"""Routes package."""
from src.routes.generate import router as generate_router
from src.routes.analyze import router as analyze_router
from src.routes.history import router as history_router

__all__ = ["generate_router", "analyze_router", "history_router"]
