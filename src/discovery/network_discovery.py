"""
Advanced network discovery methods for RFID scanners.

Implements mDNS/Bonjour discovery and enhanced network scanning
with proper error handling.
"""

import socket
import time
import threading
from typing import List, Dict, Any, Optional, Callable
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
    
    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout
        
    def scan_subnet(self, subnet_base: str, max_hosts: int = 254) -> List[Dict[str, Any]]:
        """
        Scan a subnet for RFID scanners.
        
        Args:
            subnet_base: Base IP like '192.168.1' or '169.254.1'
            max_hosts: Maximum number of hosts to scan
            
        Returns:
            List of discovered scanner info dicts
        """
        discovered = []
        threads = []
        lock = threading.Lock()
        
        def scan_host(host_num: int):
            address = f"{subnet_base}.{host_num}"
            results = self._test_address_comprehensive(address)
            if results:
                with lock:
                    discovered.extend(results)
                    
        # Limit concurrent threads for performance
        max_threads = min(50, max_hosts)
        for i in range(1, min(max_hosts + 1, 255)):
            if len(threads) >= max_threads:
                # Wait for some threads to complete
                for t in threads[:10]:
                    t.join()
                threads = [t for t in threads if t.is_alive()]
                
            thread = threading.Thread(target=scan_host, args=(i,))
            thread.start()
            threads.append(thread)
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        return discovered
        
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
