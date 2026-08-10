from xinggraph.exceptions import XingGraphSystemError
from fastapi import status


class PyPdfInternalError(XingGraphSystemError):
    """Internal pypdf error"""

    def __init__(
        self,
        message: str = "Error during PyPdf processing. Pdf is damaged or cannot be processed.",
        name: str = "PyPdfInternalError",
        status_code=status.WS_1011_INTERNAL_ERROR,
    ):
        super().__init__(message, name, status_code)
