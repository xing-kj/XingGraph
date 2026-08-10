from xinggraph.exceptions import (
    XingGraphValidationError,
    XingGraphConfigurationError,
)
from fastapi import status


class InvalidDataChunksError(XingGraphValidationError):
    def __init__(self, detail: str):
        super().__init__(
            message=f"Invalid data_chunks: {detail}",
            name="InvalidDataChunksError",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class InvalidGraphModelError(XingGraphValidationError):
    def __init__(self, got):
        super().__init__(
            message=f"graph_model must be a subclass of BaseModel (got {got}).",
            name="InvalidGraphModelError",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class InvalidOntologyAdapterError(XingGraphConfigurationError):
    def __init__(self, got):
        super().__init__(
            message=f"ontology_adapter lacks required interface (got {got}).",
            name="InvalidOntologyAdapterError",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class InvalidChunkGraphInputError(XingGraphValidationError):
    def __init__(self, detail: str):
        super().__init__(
            message=f"Invalid chunk inputs or LLM Chunkgraphs: {detail}",
            name="InvalidChunkGraphInputError",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
