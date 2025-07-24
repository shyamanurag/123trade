from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from typing import Union
import logging
import traceback
from datetime import datetime

from ..models.responses import ErrorResponse

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Global error handler for the application"""
    
    @staticmethod
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle request validation errors"""
        error_details = []
        for error in exc.errors():
            error_details.append({
                "loc": error["loc"],
                "msg": error["msg"],
                "type": error["type"]
            })
        
        response = ErrorResponse(
            success=False,
            message="Validation error",
            error_code="VALIDATION_ERROR",
            error_details={"errors": error_details},
            timestamp=datetime.utcnow()
        )
        
        logger.warning(f"Validation error: {error_details}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response.dict()
        )

    @staticmethod
    async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Handle database errors"""
        response = ErrorResponse(
            success=False,
            message="Database error occurred",
            error_code="DATABASE_ERROR",
            error_details={"error": str(exc)},
            timestamp=datetime.utcnow()
        )
        
        logger.error(f"Database error: {str(exc)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.dict()
        )

    @staticmethod
    async def handle_http_error(request: Request, exc: Union[Exception, HTTPException]) -> JSONResponse:
        """Handle HTTP exceptions"""
        status_code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
        error_code = getattr(exc, "error_code", "INTERNAL_SERVER_ERROR")
        
        response = ErrorResponse(
            success=False,
            message=str(exc),
            error_code=error_code,
            timestamp=datetime.utcnow()
        )
        
        logger.error(f"HTTP error {status_code}: {str(exc)}")
        return JSONResponse(
            status_code=status_code,
            content=response.dict()
        )

    @staticmethod
    async def handle_generic_error(request: Request, exc: Exception) -> JSONResponse:
        """Handle any unhandled exceptions"""
        response = ErrorResponse(
            success=False,
            message="An unexpected error occurred",
            error_code="INTERNAL_SERVER_ERROR",
            error_details={"error": str(exc)},
            timestamp=datetime.utcnow()
        )
        
        logger.error(f"Unexpected error: {str(exc)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.dict()
        )

# Error handler instance
error_handler = ErrorHandler() 