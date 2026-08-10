"""
Custom exceptions for the XingGraph API.

This module defines a set of exceptions for handling various application errors,
such as System, Validation, Configuration or TransientErrors
"""

from .exceptions import (
    XingGraphApiError,
    XingGraphSystemError,
    XingGraphValidationError,
    XingGraphConfigurationError,
    XingGraphTransientError,
)
