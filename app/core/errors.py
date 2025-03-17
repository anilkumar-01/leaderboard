# app/core/errors.py
from fastapi import HTTPException, status

class BadRequestError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class UnauthorizedError(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class ForbiddenError(HTTPException):
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

class NotFoundError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )

class ConflictError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )