"""
LawVisor Clause Extractor Module
================================
Converts raw document text into structured legal clauses.
Uses LLM to classify and segment contract content.

Each clause is:
- Identified with a unique ID
- Classified by type (data protection, liability, etc.)
- Assigned a confidence score
- Linked to its source location
"""

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from openai import AsyncOpenAI

from core.config import CLAUSE_TYPES, get_settings
from core.ocr import DocumentContent

logger = logging.getLogger(__name__)
settings = get_settings()


class ClauseType(str, Enum):
    """Legal clause type classifications."""
    DATA_PROTECTION = "data_protection"
    LIABILITY = "liability"
    TERMINATION = "termination"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    JURISDICTION = "jurisdiction"
    CONFIDENTIALITY = "confidentiality"
    INDEMNIFICATION = "indemnification"
    FORCE_MAJEURE = "force_majeure"
    PAYMENT_TERMS = "payment_terms"
    WARRANTIES = "warranties"
    DISPUTE_RESOLUTION = "dispute_resolution"
    AMENDMENT = "amendment"
    ASSIGNMENT = "assignment"
    GOVERNING_LAW = "governing_law"
    SEVERABILITY = "severability"
    NOTICES = "notices"
    ENTIRE_AGREEMENT = "entire_agreement"
    COUNTERPARTS = "counterparts"
    UNKNOWN = "unknown"


@dataclass
class ExtractedClause:
    """A single extracted and classified clause."""
    clause_id: str
    clause_type: ClauseType
    title: str
    raw_text: str
    normalized_text: str
    page_number: int
    start_position: int
    end_position: int
    confidence: float
    sub_clauses: list['ExtractedClause']
    metadata: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "clause_id": self.clause_id,
            "clause_type": self.clause_type.value,
            "title": self.title,
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "page_number": self.page_number,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "confidence": self.confidence,
            "sub_clauses": [sc.to_dict() for sc in self.sub_clauses],
            "metadata": self.metadata
        }


@dataclass
class ExtractionResult:
    """Complete clause extraction result."""
    document_id: str
    extracted_at: datetime
    clauses: list[ExtractedClause]
    total_clauses: int
    clause_type_distribution: dict[str, int]
    average_confidence: float
    warnings: list[str]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document_id,
            "extracted_at": self.extracted_at.isoformat(),
            "clauses": [c.to_dict() for c in self.clauses],
            "total_clauses": self.total_clauses,
            "clause_type_distribution": self.clause_type_distribution,
            "average_confidence": self.average_confidence,
            "warnings": self.warnings
        }


# System prompt for clause extraction
CLAUSE_EXTRACTION_PROMPT = """You are a legal document analysis expert. Your task is to extract and classify legal clauses from contract text.

For each clause you identify, provide:
1. A unique clause number (e.g., "C001", "C002")
2. The clause type from this list: {clause_types}
3. The clause title (as it appears or inferred)
4. The exact raw text of the clause
5. A normalized/cleaned version of the text
6. Your confidence score (0.0 to 1.0) based on:
   - How clearly the clause fits a type
   - Whether the text is complete
   - How standard the language is

IMPORTANT RULES:
- Extract ALL clauses, including nested sub-clauses
- Preserve the exact text - do not modify or summarize
- If a clause spans multiple types, choose the primary one
- For ambiguous clauses, use "unknown" type
- Include section/article numbers if present

Output your response as a JSON array of clauses with this structure:
{{
    "clauses": [
        {{
            "clause_number": "C001",
            "clause_type": "data_protection",
            "title": "Data Processing Agreement",
            "raw_text": "...",
            "normalized_text": "...",
            "confidence": 0.95,
            "sub_clauses": []
        }}
    ],
    "warnings": []
}}"""


class ClauseExtractor:
    """
    Extracts and classifies legal clauses from document content.
    
    Uses a combination of:
    1. Rule-based pattern matching for structure detection
    2. LLM for semantic classification and normalization
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._init_llm_client()
        
    def _init_llm_client(self):
        """Initialize the OpenAI LLM client."""
        self.llm_client = AsyncOpenAI(
            api_key=self.settings.openai_api_key,
            timeout=300.0  # 5 minutes per request
        )
        self.model = self.settings.llm_model or "gpt-4o-mini"
    
    async def extract_clauses(
        self, 
        document: DocumentContent
    ) -> ExtractionResult:
        """
        Extract all clauses from a document.
        
        Args:
            document: Processed document content from OCR
            
        Returns:
            ExtractionResult with all classified clauses
        """
        logger.info(f"Extracting clauses from document: {document.document_id}")
        
        # Step 1: Pre-segment the document using rule-based patterns
        segments = self._presegment_document(document)
        logger.info(f"Pre-segmented into {len(segments)} sections")
        
        # Step 2: Process each segment with LLM for classification
        all_clauses = []
        all_warnings = []
        
        # Process in batches concurrently
        batch_size = 5
        batches = []
        for i in range(0, len(segments), batch_size):
            batch_segments = segments[i:i + batch_size]
            batch_text = "\n\n---\n\n".join(
                f"[Page {s['page']}]\n{s['text']}" for s in batch_segments
            )
            batches.append((batch_text, i))

        logger.info(f"Processing {len(batches)} batches concurrently (limit: 5)...")
        
        semaphore = asyncio.Semaphore(5)  # Limit concurrent requests to avoid rate limits
        
        async def process_batch(batch_text: str, index: int, batch_num: int, total: int):
            async with semaphore:
                logger.info(f"Processing batch {batch_num}/{total} with LLM...")
                clauses, warnings = await self._extract_clauses_with_llm(
                    batch_text, 
                    document.document_id,
                    start_index=index
                )
                logger.info(f"Batch {batch_num}/{total} complete. Found {len(clauses)} clauses.")
                return clauses, warnings

        tasks = [
            process_batch(b[0], b[1], idx + 1, len(batches)) 
            for idx, b in enumerate(batches)
        ]
        
        results = await asyncio.gather(*tasks)
        
        for clauses, warnings in results:
            all_clauses.extend(clauses)
            all_warnings.extend(warnings)
        
        # Step 3: Post-process and validate
        validated_clauses = self._validate_clauses(all_clauses)
        
        # Step 4: Calculate statistics
        type_distribution = self._calculate_type_distribution(validated_clauses)
        avg_confidence = self._calculate_average_confidence(validated_clauses)
        
        return ExtractionResult(
            document_id=document.document_id,
            extracted_at=datetime.utcnow(),
            clauses=validated_clauses,
            total_clauses=len(validated_clauses),
            clause_type_distribution=type_distribution,
            average_confidence=avg_confidence,
            warnings=all_warnings
        )
    
    def _presegment_document(
        self, 
        document: DocumentContent
    ) -> list[dict[str, Any]]:
        """
        Pre-segment document into logical sections using patterns.
        
        Identifies:
        - Article/Section headers
        - Numbered clauses
        - Paragraph breaks
        """
        segments = []
        
        # Patterns for clause/section detection
        patterns = [
            r'^(?:ARTICLE|Article)\s+[\dIVXLCDM]+[.:]\s*',
            r'^(?:SECTION|Section)\s+[\d.]+[.:]\s*',
            r'^\d+\.\d*\s+[A-Z]',
            r'^[A-Z][A-Z\s]{5,}$',  # All caps headers
            r'^\([a-z]\)\s+',  # Sub-clause markers
        ]
        
        combined_pattern = '|'.join(f'({p})' for p in patterns)
        
        for page in document.pages:
            text = page.text
            lines = text.split('\n')
            
            current_segment = []
            segment_start = 0
            
            for i, line in enumerate(lines):
                # Check if line matches a section start pattern
                if re.match(combined_pattern, line.strip()):
                    # Save previous segment if exists
                    if current_segment:
                        segments.append({
                            "page": page.page_number,
                            "text": '\n'.join(current_segment),
                            "start_line": segment_start,
                            "end_line": i - 1
                        })
                    
                    current_segment = [line]
                    segment_start = i
                else:
                    current_segment.append(line)
            
            # Add final segment
            if current_segment:
                segments.append({
                    "page": page.page_number,
                    "text": '\n'.join(current_segment),
                    "start_line": segment_start,
                    "end_line": len(lines) - 1
                })
        
        return segments
    
    async def _extract_clauses_with_llm(
        self,
        text: str,
        document_id: str,
        start_index: int = 0
    ) -> tuple[list[ExtractedClause], list[str]]:
        """
        Use LLM to extract and classify clauses from text.
        
        Returns:
            Tuple of (extracted clauses, warnings)
        """
        # Prepare the prompt
        system_prompt = CLAUSE_EXTRACTION_PROMPT.format(
            clause_types=", ".join(CLAUSE_TYPES)
        )
        
        user_prompt = f"""Analyze the following legal document text and extract all clauses:

{text}

Provide your response as valid JSON only, no additional text."""

        try:
            logger.info(f"Using OpenAI LLM ({self.model}) to extract clauses from batch...")
            # Use OpenAI for clause extraction
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=4000
            )
            result_text = response.choices[0].message.content
            
            # Parse JSON response
            result = json.loads(result_text)
            
            clauses = []
            for i, clause_data in enumerate(result.get("clauses", [])):
                clause = self._parse_clause_data(
                    clause_data, 
                    document_id, 
                    start_index + i
                )
                if clause:
                    clauses.append(clause)
            
            warnings = result.get("warnings", [])
            
            return clauses, warnings
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return [], [f"JSON parsing error: {str(e)}"]
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return [], [f"Extraction error: {str(e)}"]
    
    def _parse_clause_data(
        self,
        data: dict[str, Any],
        document_id: str,
        index: int
    ) -> ExtractedClause | None:
        """Parse raw clause data into ExtractedClause object."""
        try:
            # Generate unique clause ID
            clause_id = self._generate_clause_id(
                document_id, 
                data.get("raw_text", ""),
                index
            )
            
            # Map clause type
            clause_type_str = data.get("clause_type", "unknown").lower()
            try:
                clause_type = ClauseType(clause_type_str)
            except ValueError:
                clause_type = ClauseType.UNKNOWN
            
            # Parse sub-clauses recursively
            sub_clauses = []
            for j, sub_data in enumerate(data.get("sub_clauses", [])):
                sub_clause = self._parse_clause_data(
                    sub_data, 
                    document_id, 
                    index * 100 + j
                )
                if sub_clause:
                    sub_clauses.append(sub_clause)
            
            return ExtractedClause(
                clause_id=clause_id,
                clause_type=clause_type,
                title=data.get("title", "Untitled Clause"),
                raw_text=data.get("raw_text", ""),
                normalized_text=data.get("normalized_text", data.get("raw_text", "")),
                page_number=data.get("page_number", 1),
                start_position=data.get("start_position", 0),
                end_position=data.get("end_position", 0),
                confidence=float(data.get("confidence", 0.5)),
                sub_clauses=sub_clauses,
                metadata={
                    "clause_number": data.get("clause_number", f"C{index:03d}"),
                    "extracted_at": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to parse clause data: {e}")
            return None
    
    def _generate_clause_id(
        self, 
        document_id: str, 
        text: str, 
        index: int
    ) -> str:
        """Generate a unique, deterministic clause ID."""
        content = f"{document_id}:{index}:{text[:100]}"
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:12]
        return f"CL-{hash_value}"
    
    def _validate_clauses(
        self, 
        clauses: list[ExtractedClause]
    ) -> list[ExtractedClause]:
        """Validate and clean up extracted clauses."""
        validated = []
        
        for clause in clauses:
            # Check minimum text length
            if len(clause.raw_text.strip()) < 10:
                continue
            
            # Check for duplicate text
            is_duplicate = any(
                c.raw_text.strip() == clause.raw_text.strip()
                for c in validated
            )
            if is_duplicate:
                continue
            
            validated.append(clause)
        
        return validated
    
    def _calculate_type_distribution(
        self, 
        clauses: list[ExtractedClause]
    ) -> dict[str, int]:
        """Calculate distribution of clause types."""
        distribution = {}
        for clause in clauses:
            type_key = clause.clause_type.value
            distribution[type_key] = distribution.get(type_key, 0) + 1
        return distribution
    
    def _calculate_average_confidence(
        self, 
        clauses: list[ExtractedClause]
    ) -> float:
        """Calculate average confidence score across all clauses."""
        if not clauses:
            return 0.0
        return sum(c.confidence for c in clauses) / len(clauses)
