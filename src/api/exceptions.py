from typing import Any, Dict, Optional


class AppException(Exception):
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        detail: str,
        headers: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail
        self.headers = headers
        super().__init__(detail)


class NotFoundError(AppException):
    
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            status_code=404,
            error_code="not_found",
            detail=f"{resource} with ID '{resource_id}' not found",
        )


class ValidationError(AppException):
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=400,
            error_code="validation_error",
            detail=detail,
        )


class ConflictError(AppException):
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=409,
            error_code="conflict",
            detail=detail,
        )


class ServiceUnavailableError(AppException):
    
    def __init__(self, service: str):
        super().__init__(
            status_code=503,
            error_code="service_unavailable",
            detail=f"{service} is currently unavailable",
        )
