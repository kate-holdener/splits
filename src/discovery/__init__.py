"""
RFID Scanner Discovery Module

Provides automatic discovery of RFID scanners on the network using multiple
discovery methods with configurable fallback chains.
"""

from .rfid_discovery import RFIDDiscovery
from .exceptions import (
    DiscoveryError,
    ConnectionTimeoutError,
    ProtocolError,
    AuthenticationError,
    MultipleScannersFoundError,
    NoScannersFoundError
)

__all__ = [
    'RFIDDiscovery',
    'DiscoveryError',
    'ConnectionTimeoutError',
    'ProtocolError', 
    'AuthenticationError',
    'MultipleScannersFoundError',
    'NoScannersFoundError'
]