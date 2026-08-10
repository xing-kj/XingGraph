from xinggraph.exceptions import XingGraphSystemError
from fastapi import status


class PipelineRunFailedError(XingGraphSystemError):
    def __init__(
        self,
        message: str = "Pipeline run failed.",
        name: str = "PipelineRunFailedError",
        status_code: int = status.HTTP_422_UNPROCESSABLE_CONTENT,
    ):
        super().__init__(message, name, status_code)
