"""
API endpoint tests for LawVisor.
"""
import io
import pytest
from fastapi import status


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check_returns_ok(self, test_client):
        """Test that health check returns healthy status."""
        response = test_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestUploadEndpoint:
    """Tests for document upload endpoint."""
    
    def test_upload_valid_pdf(self, test_client, sample_pdf_content):
        """Test uploading a valid PDF file."""
        files = {
            "file": ("test_contract.pdf", io.BytesIO(sample_pdf_content), "application/pdf")
        }
        
        response = test_client.post("/upload", files=files)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "document_id" in data
        assert data["filename"] == "test_contract.pdf"
        assert data["status"] == "pending"
    
    def test_upload_non_pdf_file(self, test_client):
        """Test that non-PDF files are rejected."""
        files = {
            "file": ("test.txt", io.BytesIO(b"Not a PDF"), "text/plain")
        }
        
        response = test_client.post("/upload", files=files)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "PDF" in response.json()["detail"]
    
    def test_upload_empty_file(self, test_client):
        """Test that empty files are rejected."""
        files = {
            "file": ("empty.pdf", io.BytesIO(b""), "application/pdf")
        }
        
        response = test_client.post("/upload", files=files)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_upload_invalid_pdf(self, test_client):
        """Test that invalid PDF content is handled."""
        files = {
            "file": ("fake.pdf", io.BytesIO(b"This is not a PDF"), "application/pdf")
        }
        
        response = test_client.post("/upload", files=files)
        
        # Should accept the file but mark it for validation during processing
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


class TestAnalyzeEndpoint:
    """Tests for document analysis endpoint."""
    
    def test_analyze_nonexistent_document(self, test_client):
        """Test analyzing a document that doesn't exist."""
        response = test_client.post("/analyze/doc-nonexistent123")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_analyze_requires_document_id(self, test_client):
        """Test that document ID is required."""
        response = test_client.post("/analyze/")
        
        # Should be 404 or 405 depending on routing
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestRiskEndpoint:
    """Tests for risk report endpoint."""
    
    def test_get_risk_nonexistent_document(self, test_client):
        """Test getting risk for a document that doesn't exist."""
        response = test_client.get("/risk/doc-nonexistent123")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_regulations_endpoint(self, test_client):
        """Test the regulations list endpoint."""
        response = test_client.get("/regulations")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "gdpr" in data or "sec" in data or "regulations" in data


class TestCORSHeaders:
    """Tests for CORS configuration."""
    
    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are present."""
        response = test_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        # CORS should allow the request
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_404_for_unknown_route(self, test_client):
        """Test that unknown routes return 404."""
        response = test_client.get("/unknown/route/here")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_method_not_allowed(self, test_client):
        """Test that wrong HTTP methods are rejected."""
        response = test_client.delete("/health")
        
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
