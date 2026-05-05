"""
Advanced network discovery methods for RFID scanners.

Implements mDNS/Bonjour discovery and enhanced network scanning
with proper error handling.
"""

import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf, ServiceInfo

from .exceptions import DiscoveryError

class MDNSDiscovery:
    """mDNS/Bonjour discovery for RFID scanners."""
    
    LLRP_SERVICE_TYPE = "_llrp._tcp.local."
    HTTP_SERVICE_TYPE = "_http._tcp.local."
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.discovered_services: List[Dict[str, Any]] = []
        
    def discover(self) -> List[Dict[str, Any]]:
        """
        Discover RFID scanners via mDNS/Bonjour.
        
        Returns:
            List of discovered scanner info dicts
        """
           
        self.discovered_services = []
        
        class RFIDServiceListener(ServiceListener):
            def __init__(self, parent):
                self.parent = parent
                
            def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                info = zc.get_service_info(type_, name)
                if info:
                    self.parent._add_service_info(info, type_)
                    
            def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                pass
                
            def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                pass
        
        try:
            zeroconf = Zeroconf()
            listener = RFIDServiceListener(self)
            
            # Browse for LLRP and HTTP services
            browser_llrp = ServiceBrowser(zeroconf, self.LLRP_SERVICE_TYPE, listener)
            browser_http = ServiceBrowser(zeroconf, self.HTTP_SERVICE_TYPE, listener)
            
            # Wait for discoveries
            time.sleep(self.timeout)
            
            # Cleanup
            browser_llrp.cancel()
            browser_http.cancel()
            zeroconf.close()
            
        except Exception as e:
            print(f"mDNS discovery error: {e}")
            
        return self.discovered_services
        
    def _add_service_info(self, info: ServiceInfo, service_type: str):
        """Process discovered service info."""
        try:
            if info.addresses:
                address = socket.inet_ntoa(info.addresses[0])
                port = info.port
                
                # Determine protocol from service type and port
                protocol = 'llrp' if service_type == self.LLRP_SERVICE_TYPE or port == 5084 else 'rest'
                
                service_info = {
                    'address': address,
                    'protocol': protocol,
                    'port': port,
                    'name': info.name,
                    'timestamp': time.time(),
                    'discovery_method': 'mdns'
                }
                
                # Avoid duplicates
                if not any(s['address'] == address and s['port'] == port 
                          for s in self.discovered_services):
                    self.discovered_services.append(service_info)
                    
        except Exception as e:
            print(f"Error processing service info: {e}")


class NetworkScanner:
    """Enhanced network scanning for RFID scanners."""

    PRIORITY_HOST_SUFFIXES = (
        1, 2, 3, 4, 5,
        10, 11, 12, 20, 21, 22,
        100, 101, 102, 110, 111, 112,
        200, 201, 210, 211, 254
    )
    
    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout
        
    def scan_hosts(self, addresses: List[str]) -> List[Dict[str, Any]]:
        """
        Scan a list of addresses for RFID scanners in parallel.

        Args:
            addresses: List of IP addresses to test

        Returns:
            List of discovered scanner info dicts
        """
        discovered = []
        with ThreadPoolExecutor(max_workers=min(50, len(addresses))) as executor:
            futures = {executor.submit(self._test_address_comprehensive, addr): addr
                       for addr in addresses}
            for future in as_completed(futures):
                results = future.result()
                if results:
                    discovered.extend(results)
        return discovered

    def scan_subnet(self, subnet_base: str, max_hosts: int = 254) -> List[Dict[str, Any]]:
        """
        Scan a subnet for RFID scanners.

        Args:
            subnet_base: Base IP like '192.168.1' or '169.254.1'
            max_hosts: Maximum number of hosts to scan

        Returns:
            List of discovered scanner info dicts
        """
        limit = min(max_hosts, 254)
        priority_addresses = [
            f"{subnet_base}.{suffix}"
            for suffix in self.PRIORITY_HOST_SUFFIXES
            if 1 <= suffix <= limit
        ]

        if priority_addresses:
            prioritized_results = self.scan_hosts(priority_addresses)
            if prioritized_results:
                return prioritized_results

        seen = set(priority_addresses)
        remaining_addresses = [
            f"{subnet_base}.{host}"
            for host in range(1, limit + 1)
            if f"{subnet_base}.{host}" not in seen
        ]
        return self.scan_hosts(remaining_addresses)

    def _test_address_comprehensive(self, address: str) -> List[Dict[str, Any]]:
        """Comprehensive test of an address for RFID scanner protocols."""
        results = []
        
        # Test LLRP port
        if self._test_port(address, 5084):
            results.append({
                'address': address,
                'protocol': 'llrp',
                'port': 5084,
                'timestamp': time.time(),
                'discovery_method': 'network_scan'
            })
            
        # Test common HTTP ports
        for port in [80, 443, 8080, 8443]:
            if self._test_port(address, port):
                # Quick HTTP check to see if it's a web service
                if self._test_http_service(address, port):
                    results.append({
                        'address': address,
                        'protocol': 'rest',
                        'port': port,
                        'timestamp': time.time(),
                        'discovery_method': 'network_scan'
                    })
                    break  # Only add one HTTP service per address
                    
        return results
        
    def _test_port(self, address: str, port: int) -> bool:
        """Test TCP connectivity to address:port."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((address, port))
            sock.close()
            return result == 0
        except:
            return False
            
    def _test_http_service(self, address: str, port: int) -> bool:
        """Test if the service responds to HTTP requests."""
        try:
            import requests
            url = f"http://{address}:{port}" if port != 80 else f"http://{address}"
            response = requests.get(url, timeout=self.timeout, verify=False)
            return response.status_code < 500
        except:
            return False
