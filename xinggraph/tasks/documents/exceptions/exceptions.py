from xinggraph.exceptions import (
    XingGraphValidationError,
    XingGraphConfigurationError,
)
from fastapi import status


class WrongDataDocumentInputError(XingGraphValidationError):
    """Raised when a wrong data document is provided."""

    def __init__(
        self,
        field: str,
        name: str = "WrongDataDocumentInputError",
        status_code: int = status.HTTP_422_UNPROCESSABLE_CONTENT,
    ):
        message = f"Missing of invalid parameter: '{field}'."
        super().__init__(message, name, status_code)


class InvalidChunkSizeError(XingGraphValidationError):
    def __init__(self, value):
        super().__init__(
            message=f"max_chunk_size must be a positive integer (got {value}).",
            name="InvalidChunkSizeError",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class InvalidChunkerError(XingGraphValidationError):
    def __init__(self):
        super().__init__(
            message="chunker must be a valid Chunker class.",
            name="InvalidChunkerError",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
