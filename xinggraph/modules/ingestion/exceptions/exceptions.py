from xinggraph.exceptions import XingGraphValidationError
from fastapi import status


class IngestionError(XingGraphValidationError):
    def __init__(
        self,
        message: str = "Type of data sent to classify not supported.",
        name: str = "IngestionError",
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    ):
        super().__init__(message, name, status_code)
