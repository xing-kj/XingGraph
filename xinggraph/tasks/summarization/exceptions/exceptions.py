from xinggraph.exceptions import (
    XingGraphValidationError,
    XingGraphConfigurationError,
)
from fastapi import status


class InvalidSummaryInputsError(XingGraphValidationError):
    def __init__(self, detail: str):
        super().__init__(
            message=f"Invalid summarize_text inputs: {detail}",
            name="InvalidSummaryInputsError",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
