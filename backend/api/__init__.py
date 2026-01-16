"""
LawVisor API Module
===================
FastAPI routers for the LawVisor API.
"""

from api.analyze import router as analyze_router
from api.risk import router as risk_router
from api.upload import router as upload_router

__all__ = ["upload_router", "analyze_router", "risk_router"]
