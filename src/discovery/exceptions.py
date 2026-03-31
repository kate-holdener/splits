"""
Discovery-specific exception classes for clearer error handling and user messaging.
"""


class DiscoveryError(Exception):
    """Base exception for all discovery-related errors."""
    pass


class ConnectionTimeoutError(DiscoveryError):
    """Scanner is unreachable or not responding within timeout period."""
    
    def __init__(self, address: str, timeout: float = None):
        self.address = address
        self.timeout = timeout
        msg = f"Could not connect to scanner at {address}"
        if timeout:
            msg += f" within {timeout}s"
        super().__init__(msg)


class ProtocolError(DiscoveryError):
    """Scanner protocol mismatch (e.g., LLRP vs HTTP)."""
    
    def __init__(self, address: str, expected_protocol: str, details: str = None):
        self.address = address
        self.expected_protocol = expected_protocol
        msg = f"Scanner at {address} does not support {expected_protocol} protocol"
        if details:
            msg += f": {details}"
        super().__init__(msg)


class AuthenticationError(DiscoveryError):
    """Scanner requires credentials that were not provided."""
    
    def __init__(self, address: str, details: str = None):
        self.address = address
        msg = f"Scanner at {address} requires authentication"
        if details:
            msg += f": {details}"
        super().__init__(msg)


class MultipleScannersFoundError(DiscoveryError):
    """Multiple scanners found when only one expected."""
    
    def __init__(self, scanners: list[str]):
        self.scanners = scanners
        scanner_list = ", ".join(scanners)
        super().__init__(f"Multiple scanners found: {scanner_list}. Please specify which one to use.")


class NoScannersFoundError(DiscoveryError):
    """No scanners found after trying all discovery methods."""
    
    def __init__(self, attempted_methods: list[str] = None):
        self.attempted_methods = attempted_methods or []
        msg = "No RFID scanners found on the network"
        if attempted_methods:
            methods = ", ".join(attempted_methods)
            msg += f" using methods: {methods}"
        super().__init__(msg)