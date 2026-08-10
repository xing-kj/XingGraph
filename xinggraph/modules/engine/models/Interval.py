from pydantic import Field
from xinggraph.infrastructure.engine import DataPoint
from xinggraph.modules.engine.models.Timestamp import Timestamp


class Interval(DataPoint):
    time_from: Timestamp = Field(...)
    time_to: Timestamp = Field(...)
