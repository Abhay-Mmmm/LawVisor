"""
LawVisor OCR Module
===================
Handles document ingestion, OCR processing, and text extraction.
Supports both scanned (image-based) and native (text-based) PDFs.

Key Features:
- Automatic detection of scanned vs native PDFs
- Structure-preserving text extraction
- Table, header, and footnote handling
- Confidence scoring for OCR results
"""

import asyncio
import io
import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from PyPDF2 import PdfReader

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = settings.tesseract_path


class DocumentType(str, Enum):
    """Type of PDF document."""
    NATIVE = "native"  # Text-based PDF
    SCANNED = "scanned"  # Image-based PDF
    HYBRID = "hybrid"  # Mixed content


@dataclass
class PageContent:
    """Extracted content from a single page."""
    page_number: int
    text: str
    tables: list[dict[str, Any]]
    headers: list[str]
    footnotes: list[str]
    confidence: float
    is_scanned: bool


@dataclass
class DocumentContent:
    """Complete extracted document content."""
    document_id: str
    filename: str
    document_type: DocumentType
    total_pages: int
    pages: list[PageContent]
    overall_confidence: float
    raw_text: str
    metadata: dict[str, Any]
    
    def get_full_text(self) -> str:
        """Get concatenated text from all pages."""
        return "\n\n".join(page.text for page in self.pages)


class OCRProcessor:
    """
    Handles OCR and text extraction from PDF documents.
    
    This processor:
    1. Detects if PDF is scanned or native
    2. Applies appropriate extraction method
    3. Preserves document structure (tables, headers, footnotes)
    4. Provides confidence scores for quality assessment
    """
    
    def __init__(self):
        self.min_confidence = settings.ocr_confidence_threshold
        self._preprocess_config = {
            "denoise": True,
            "deskew": True,
            "binarize": True
        }
    
    async def process_document(
        self, 
        file_path: Path, 
        document_id: str
    ) -> DocumentContent:
        """
        Process a PDF document and extract all text content.
        
        Args:
            file_path: Path to the PDF file
            document_id: Unique identifier for the document
            
        Returns:
            DocumentContent with all extracted information
            
        Raises:
            OCRError: If OCR confidence is below threshold
        """
        logger.info(f"Processing document: {file_path}")
        
        # Detect document type
        doc_type = await self._detect_document_type(file_path)
        logger.info(f"Document type detected: {doc_type}")
        
        # Extract content based on type
        if doc_type == DocumentType.NATIVE:
            pages = await self._extract_native_pdf(file_path)
        elif doc_type == DocumentType.SCANNED:
            pages = await self._extract_scanned_pdf(file_path)
        else:
            pages = await self._extract_hybrid_pdf(file_path)
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(pages)
        
        # Validate confidence threshold
        if overall_confidence < self.min_confidence:
            raise OCRError(
                f"OCR confidence {overall_confidence:.2f} is below threshold "
                f"{self.min_confidence}. Document may require manual review."
            )
        
        # Extract metadata
        metadata = await self._extract_metadata(file_path)
        
        return DocumentContent(
            document_id=document_id,
            filename=file_path.name,
            document_type=doc_type,
            total_pages=len(pages),
            pages=pages,
            overall_confidence=overall_confidence,
            raw_text="\n\n".join(p.text for p in pages),
            metadata=metadata
        )
    
    async def _detect_document_type(self, file_path: Path) -> DocumentType:
        """
        Detect whether a PDF is native text, scanned, or hybrid.
        
        Uses text extraction ratio to determine type:
        - >80% extractable text = Native
        - <20% extractable text = Scanned
        - Between = Hybrid
        """
        try:
            reader = PdfReader(str(file_path))
            total_chars = 0
            total_pages = len(reader.pages)
            
            for page in reader.pages:
                text = page.extract_text() or ""
                total_chars += len(text.strip())
            
            # Average characters per page
            avg_chars = total_chars / total_pages if total_pages > 0 else 0
            
            # Thresholds based on typical document characteristics
            if avg_chars > 500:
                return DocumentType.NATIVE
            elif avg_chars < 50:
                return DocumentType.SCANNED
            else:
                return DocumentType.HYBRID
                
        except Exception as e:
            logger.warning(f"Error detecting document type: {e}")
            return DocumentType.SCANNED  # Default to OCR
    
    async def _extract_native_pdf(self, file_path: Path) -> list[PageContent]:
        """Extract text from a native text-based PDF using pdfplumber."""
        pages = []
        
        with pdfplumber.open(str(file_path)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract main text
                text = page.extract_text() or ""
                
                # Extract tables
                tables = self._extract_tables(page)
                
                # Extract headers and footnotes
                headers = self._extract_headers(text)
                footnotes = self._extract_footnotes(text)
                
                pages.append(PageContent(
                    page_number=page_num,
                    text=text,
                    tables=tables,
                    headers=headers,
                    footnotes=footnotes,
                    confidence=1.0,  # Native PDFs have perfect confidence
                    is_scanned=False
                ))
        
        return pages
    
    async def _extract_scanned_pdf(self, file_path: Path) -> list[PageContent]:
        """Extract text from a scanned PDF using OCR."""
        pages = []
        
        # Convert PDF pages to images
        images = await asyncio.to_thread(
            convert_from_path, 
            str(file_path), 
            dpi=300
        )
        
        for page_num, image in enumerate(images, start=1):
            # Preprocess image for better OCR
            processed_image = await self._preprocess_image(image)
            
            # Perform OCR with detailed output
            ocr_result = await asyncio.to_thread(
                pytesseract.image_to_data,
                processed_image,
                output_type=pytesseract.Output.DICT,
                config='--oem 3 --psm 6'
            )
            
            # Extract text and confidence
            text, confidence = self._parse_ocr_result(ocr_result)
            
            # Extract tables using image processing
            tables = await self._extract_tables_from_image(processed_image)
            
            # Extract structure
            headers = self._extract_headers(text)
            footnotes = self._extract_footnotes(text)
            
            pages.append(PageContent(
                page_number=page_num,
                text=text,
                tables=tables,
                headers=headers,
                footnotes=footnotes,
                confidence=confidence,
                is_scanned=True
            ))
        
        return pages
    
    async def _extract_hybrid_pdf(self, file_path: Path) -> list[PageContent]:
        """Extract from hybrid PDF, using OCR where native extraction fails."""
        pages = []
        
        # First try native extraction
        native_pages = await self._extract_native_pdf(file_path)
        
        # Check each page and apply OCR if needed
        images = None
        for i, page in enumerate(native_pages):
            if len(page.text.strip()) < 100:  # Page likely needs OCR
                if images is None:
                    images = await asyncio.to_thread(
                        convert_from_path, 
                        str(file_path), 
                        dpi=300
                    )
                
                # Apply OCR to this page
                processed_image = await self._preprocess_image(images[i])
                ocr_result = await asyncio.to_thread(
                    pytesseract.image_to_data,
                    processed_image,
                    output_type=pytesseract.Output.DICT,
                    config='--oem 3 --psm 6'
                )
                text, confidence = self._parse_ocr_result(ocr_result)
                
                pages.append(PageContent(
                    page_number=page.page_number,
                    text=text,
                    tables=page.tables,
                    headers=self._extract_headers(text),
                    footnotes=self._extract_footnotes(text),
                    confidence=confidence,
                    is_scanned=True
                ))
            else:
                pages.append(page)
        
        return pages
    
    async def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for optimal OCR results.
        
        Steps:
        1. Convert to grayscale
        2. Apply denoising
        3. Deskew if necessary
        4. Apply adaptive binarization
        """
        # Convert PIL Image to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # Denoise
        if self._preprocess_config["denoise"]:
            gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Deskew
        if self._preprocess_config["deskew"]:
            gray = self._deskew_image(gray)
        
        # Adaptive binarization
        if self._preprocess_config["binarize"]:
            gray = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
        
        # Convert back to PIL
        return Image.fromarray(gray)
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Correct image skew using Hough transform."""
        coords = np.column_stack(np.where(image > 0))
        
        if len(coords) < 100:
            return image
            
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = 90 + angle
        elif angle > 45:
            angle = angle - 90
            
        if abs(angle) > 0.5:  # Only correct if skew is significant
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            image = cv2.warpAffine(
                image, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
        
        return image
    
    def _parse_ocr_result(self, ocr_data: dict) -> tuple[str, float]:
        """Parse Tesseract OCR output and calculate confidence."""
        texts = []
        confidences = []
        
        n_boxes = len(ocr_data['text'])
        
        for i in range(n_boxes):
            conf = int(ocr_data['conf'][i])
            text = ocr_data['text'][i]
            
            if conf > 0 and text.strip():
                texts.append(text)
                confidences.append(conf)
        
        full_text = ' '.join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Normalize confidence to 0-1 scale
        normalized_confidence = avg_confidence / 100.0
        
        return full_text, normalized_confidence
    
    def _extract_tables(self, page: Any) -> list[dict[str, Any]]:
        """Extract tables from a pdfplumber page."""
        tables = []
        
        try:
            extracted_tables = page.extract_tables()
            
            for idx, table in enumerate(extracted_tables):
                if table and len(table) > 0:
                    # Convert to structured format
                    headers = table[0] if table else []
                    rows = table[1:] if len(table) > 1 else []
                    
                    tables.append({
                        "table_id": idx,
                        "headers": headers,
                        "rows": rows,
                        "row_count": len(rows)
                    })
        except Exception as e:
            logger.warning(f"Error extracting tables: {e}")
        
        return tables
    
    async def _extract_tables_from_image(
        self, 
        image: Image.Image
    ) -> list[dict[str, Any]]:
        """Extract tables from scanned image using line detection."""
        # Convert to OpenCV format
        cv_image = np.array(image)
        
        # Detect horizontal and vertical lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        
        horizontal_lines = cv2.morphologyEx(
            cv_image, cv2.MORPH_OPEN, horizontal_kernel
        )
        vertical_lines = cv2.morphologyEx(
            cv_image, cv2.MORPH_OPEN, vertical_kernel
        )
        
        # Combine lines
        table_mask = cv2.add(horizontal_lines, vertical_lines)
        
        # Find contours that might be table cells
        contours, _ = cv2.findContours(
            table_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        
        tables = []
        if len(contours) > 10:  # Likely a table structure
            tables.append({
                "table_id": 0,
                "detected": True,
                "cell_count": len(contours),
                "note": "Table detected in scanned image - manual review recommended"
            })
        
        return tables
    
    def _extract_headers(self, text: str) -> list[str]:
        """Extract section headers from text."""
        headers = []
        
        # Common header patterns in legal documents
        patterns = [
            r'^(?:ARTICLE|Article|SECTION|Section)\s+[\dIVXLCDM]+[.:]\s*(.+)$',
            r'^(?:\d+\.)\s*([A-Z][A-Z\s]+)$',
            r'^([A-Z][A-Z\s]{10,})$',  # All caps lines
        ]
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    headers.append(line)
                    break
        
        return headers
    
    def _extract_footnotes(self, text: str) -> list[str]:
        """Extract footnotes from text."""
        footnotes = []
        
        # Common footnote patterns
        patterns = [
            r'^\s*\[(\d+)\]\s*(.+)$',  # [1] Footnote text
            r'^\s*(\d+)\.\s*(.+)$',     # 1. Footnote text (at bottom)
            r'^\s*\*+\s*(.+)$',         # *** Footnote text
        ]
        
        lines = text.split('\n')
        in_footnote_section = False
        
        for line in lines:
            # Detect footnote section markers
            if re.match(r'^[-_=]{20,}$', line.strip()):
                in_footnote_section = True
                continue
            
            if in_footnote_section:
                for pattern in patterns:
                    match = re.match(pattern, line)
                    if match:
                        footnotes.append(line.strip())
                        break
        
        return footnotes
    
    async def _extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract PDF metadata."""
        try:
            reader = PdfReader(str(file_path))
            info = reader.metadata
            
            return {
                "title": info.title if info and info.title else None,
                "author": info.author if info and info.author else None,
                "creator": info.creator if info and info.creator else None,
                "creation_date": str(info.creation_date) if info and info.creation_date else None,
                "modification_date": str(info.modification_date) if info and info.modification_date else None,
                "page_count": len(reader.pages),
                "file_size_bytes": file_path.stat().st_size
            }
        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")
            return {}
    
    def _calculate_overall_confidence(self, pages: list[PageContent]) -> float:
        """Calculate weighted average confidence across all pages."""
        if not pages:
            return 0.0
        
        # Weight by text length
        total_weight = 0
        weighted_confidence = 0
        
        for page in pages:
            weight = len(page.text) + 1  # +1 to avoid zero weight
            weighted_confidence += page.confidence * weight
            total_weight += weight
        
        return weighted_confidence / total_weight if total_weight > 0 else 0.0


class OCRError(Exception):
    """Raised when OCR processing fails or confidence is too low."""
    pass
