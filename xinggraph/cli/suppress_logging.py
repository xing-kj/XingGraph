"""
Module to suppress verbose logging before any xinggraph imports.
This must be imported before any other xinggraph modules.
"""

import os

# Set CLI mode to suppress verbose logging
os.environ["XINGGRAPH_CLI_MODE"] = "true"

# Also set log level to ERROR for extra safety
os.environ["LOG_LEVEL"] = "ERROR"
