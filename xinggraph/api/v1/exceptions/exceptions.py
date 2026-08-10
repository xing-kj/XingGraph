from xinggraph.exceptions import XingGraphConfigurationError, XingGraphValidationError
from fastapi import status


class InvalidConfigAttributeError(XingGraphConfigurationError):
    def __init__(
        self,
        attribute: str,
        name: str = "InvalidConfigAttributeError",
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        message = f"'{attribute}' is not a valid attribute of the configuration."
        super().__init__(message, name, status_code)


class DocumentNotFoundError(XingGraphValidationError):
    def __init__(
        self,
        message: str = "Document not found in database.",
        name: str = "DocumentNotFoundError",
        status_code: int = status.HTTP_404_NOT_FOUND,
    ):
        super().__init__(message, name, status_code)


class DatasetNotFoundError(XingGraphValidationError):
    def __init__(
        self,
        message: str = "Dataset not found.",
        name: str = "DatasetNotFoundError",
        status_code: int = status.HTTP_404_NOT_FOUND,
    ):
        super().__init__(message, name, status_code)


class DataNotFoundError(XingGraphValidationError):
    def __init__(
        self,
        message: str = "Data not found.",
        name: str = "DataNotFoundError",
        status_code: int = status.HTTP_404_NOT_FOUND,
    ):
        super().__init__(message, name, status_code)


class DocumentSubgraphNotFoundError(XingGraphValidationError):
    def __init__(
        self,
        message: str = "Document subgraph not found in graph database.",
        name: str = "DocumentSubgraphNotFoundError",
        status_code: int = status.HTTP_404_NOT_FOUND,
    ):
        super().__init__(message, name, status_code)
