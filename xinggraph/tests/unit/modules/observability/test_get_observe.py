import pytest
from unittest.mock import patch

from xinggraph.modules.observability.get_observe import get_observe
from xinggraph.modules.observability.observers import Observer
from xinggraph.modules.observability.exceptions import UnsupportedObserverError


def test_get_observe_raises_for_unsupported_observer():
    """Unsupported observer (e.g. LLMLITE, LANGSMITH) raises UnsupportedObserverError."""
    with patch("xinggraph.modules.observability.get_observe.get_base_config") as get_config:
        get_config.return_value = type("Config", (), {"monitoring_tool": Observer.LLMLITE})()

        with pytest.raises(UnsupportedObserverError, match="Unsupported observer"):
            get_observe()
