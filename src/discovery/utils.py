"""
Utility functions for easy RFID scanner discovery integration.
"""

from typing import Optional, List, Dict, Any
from .rfid_discovery import RFIDDiscovery
from .exceptions import NoScannersFoundError, MultipleScannersFoundError


def discover_scanner(protocol: str = 'both', 
                    timeout: float = 3.0,
                    interactive: bool = True,
                    return_full_info: bool = False) -> Optional[str]:
    """
    Simple function to discover and return a scanner address.
    
    Args:
        protocol: 'llrp', 'rest', or 'both'
        timeout: Discovery timeout in seconds
        interactive: Whether to prompt user for selection/input
        return_full_info: If True, return full scanner dict instead of just address
        
    Returns:
        Scanner IP address string, full scanner info dict, or None if none found
    """
    try:
        discovery = RFIDDiscovery(timeout=timeout)
        scanner = discovery.get_best_scanner(protocol)
        
        if return_full_info:
            return scanner
        else:
            return scanner['address']
        
    except NoScannersFoundError:
        if interactive:
            print("No RFID scanners found automatically.")
            address = input("Please enter scanner IP address manually: ").strip()
            if address:
                if return_full_info:
                    # Return minimal info for manual address
                    return {
                        'address': address,
                        'protocol': 'llrp',  # Default assumption
                        'port': 5084,
                        'discovery_method': 'manual'
                    }
                else:
                    return address
            return None
        return None
        
    except MultipleScannersFoundError as e:
        if interactive:
            print("Multiple RFID scanners found:")
            scanners = discovery.discover(protocol)
            for i, scanner in enumerate(scanners, 1):
                protocol_info = f"{scanner['protocol']} (port {scanner['port']})"
                print(f"  {i}. {scanner['address']} - {protocol_info}")
            try:
                choice = int(input("Select scanner (number): ")) - 1
                if 0 <= choice < len(scanners):
                    selected = scanners[choice]
                    if return_full_info:
                        return selected
                    else:
                        return selected['address']
            except (ValueError, IndexError):
                pass
        # Return first scanner if not interactive or invalid choice
        if e.scanners:
            if return_full_info:
                # Need to get full info for first scanner
                try:
                    scanners = discovery.discover(protocol)
                    return scanners[0] if scanners else None
                except:
                    return {
                        'address': e.scanners[0],
                        'protocol': 'llrp',
                        'port': 5084,
                        'discovery_method': 'fallback'
                    }
            else:
                return e.scanners[0]
        return None
        
    except Exception as e:
        print(f"Scanner discovery error: {e}")
        if interactive:
            address = input("Please enter scanner IP address manually: ").strip()
            if address:
                if return_full_info:
                    return {
                        'address': address,
                        'protocol': 'llrp',
                        'port': 5084,
                        'discovery_method': 'manual_fallback'
                    }
                else:
                    return address
            return None
        return None


def discover_all_scanners(protocol: str = 'both',
                         timeout: float = 3.0) -> List[Dict[str, Any]]:
    """
    Discover all available RFID scanners.
    
    Args:
        protocol: 'llrp', 'rest', or 'both'
        timeout: Discovery timeout in seconds
        
    Returns:
        List of scanner info dictionaries
    """
    try:
        discovery = RFIDDiscovery(timeout=timeout)
        return discovery.discover(protocol)
    except NoScannersFoundError:
        return []
    except Exception as e:
        print(f"Scanner discovery error: {e}")
        return []


def get_scanner_from_config() -> Optional[str]:
    """
    Get scanner address from environment variable or return None.
    
    Returns:
        Scanner address from RFID_SCANNER_ADDRESS env var, or None
    """
    import os
    return os.getenv('RFID_SCANNER_ADDRESS')