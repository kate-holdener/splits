"""
RFID Scanner Discovery Coordinator

Main class for discovering RFID scanners on the network using multiple methods
with configurable fallback chains, caching, and configuration support.
"""

import os
import json
import time
import socket
import threading
import requests
import subprocess
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

from .exceptions import (
    DiscoveryError,
    ConnectionTimeoutError,
    ProtocolError,
    AuthenticationError,
    MultipleScannersFoundError,
    NoScannersFoundError
)
from .network_discovery import MDNSDiscovery, NetworkScanner
from .config import ConfigManager


class RFIDDiscovery:
    """
    Discovers RFID scanners on the network using multiple methods.
    
    Supports both LLRP (sllurp) and REST API (Impinj) scanners with
    fallback chains, configuration options, and result caching.
    """
    @staticmethod
    def get_local_subnets() -> List[str]:
        """Derive subnets to scan from the machine's own network interfaces."""
        subnets = []
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            subnet_base = '.'.join(local_ip.split('.')[:3])
            subnets.append(subnet_base)
        except Exception as e:
            print(f"Could not determine local subnet: {e}")
        return subnets
    
    # Ports to scan
    LLRP_PORT = 5084
    HTTP_PORTS = [80, 443, 8080, 8443]
    
    def __init__(self, 
                 cache_file: Optional[str] = None,
                 config_file: Optional[str] = None,
                 timeout: Optional[float] = None):
        """
        Initialize RFID discovery.
        
        Args:
            cache_file: Path to cache discovered addresses (default: from config)
            config_file: Path to configuration file (optional)
            timeout: Connection timeout for discovery attempts (default: from config)
        """
        self.config = ConfigManager(config_file)
        self.timeout = timeout or self.config.get_discovery_timeout()
        self.cache_file = cache_file or self._get_cache_file_path()
        self._cached_addresses: Dict[str, Dict[str, Any]] = {}
        self._load_cache()
        
    def _get_cache_file_path(self) -> str:
        """Get cache file path from configuration."""
        cache_dir = Path(self.config.get_cache_directory())
        cache_dir.mkdir(parents=True, exist_ok=True)
        return str(cache_dir / 'rfid_scanners.json')
        
    def _load_cache(self):
        """Load cached scanner addresses."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    self._cached_addresses = json.load(f)
                # Clean up old entries based on config expiry time
                current_time = time.time()
                expiry_hours = self.config.get('cache.expiry_hours', 24)
                expiry_seconds = expiry_hours * 3600
                expired_keys = [
                    addr for addr, info in self._cached_addresses.items()
                    if current_time - info.get('timestamp', 0) > expiry_seconds
                ]
                for key in expired_keys:
                    del self._cached_addresses[key]
        except Exception as e:
            print(f"Warning: Could not load scanner cache: {e}")
            self._cached_addresses = {}
            
    def _save_cache(self):
        """Save cached scanner addresses."""
        try:
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self._cached_addresses, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save scanner cache: {e}")

    @classmethod
    def get_arp_hosts(cls) -> List[str]:
        """Get list of active hosts on the local network from the ARP cache."""
        hosts = []
        try:
            output = subprocess.check_output(['arp', '-a'], text=True)
            local_subnets = cls.get_local_subnets()
            for line in output.splitlines():
                # Skip incomplete entries — no MAC address means host is not reachable
                if 'incomplete' in line.lower():
                    continue
                ips = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                for ip in ips:
                    if (not ip.endswith('.255')
                            and not ip.endswith('.0')
                            and any(ip.startswith(subnet + '.') for subnet in local_subnets)):
                        hosts.append(ip)
        except Exception as e:
            print(f"Could not read ARP cache: {e}")
        return hosts
               
    def discover(self, 
                 protocol: str = 'both',
                 use_cache: bool = True,
                 force_discovery: bool = False) -> List[Dict[str, Any]]:
        """
        Discover RFID scanners on the network.
        
        Args:
            protocol: 'llrp', 'rest', or 'both' to specify which protocols to check
            use_cache: Whether to use cached results
            force_discovery: Skip cache and force fresh discovery
            
        Returns:
            List of discovered scanner info dicts with keys:
            - address: IP address
            - protocol: 'llrp' or 'rest'
            - port: Port number
            - timestamp: Discovery timestamp
            
        Raises:
            NoScannersFoundError: If no scanners found after all methods tried
        """
        #if use_cache and not force_discovery:
        #    cached_results = self._get_cached_results(protocol)
        #    if cached_results:
        #        return cached_results
                
        attempted_methods = []
        discovered = []
        
        # Method 1: Try environment variable
        env_address = os.getenv('RFID_SCANNER_ADDRESS')
        if env_address:
            attempted_methods.append('environment_variable')
            result = self._test_address(env_address, protocol)
            if result:
                discovered.extend(result)
                
        # Method 2: Try config file addresses
        config_addresses = self.config.get_scanner_addresses()
        if config_addresses:
            attempted_methods.append('config_file')
            for addr in config_addresses:
                result = self._test_address(addr, protocol)
                if result:
                    discovered.extend(result)
               
        # Method 4: mDNS/Bonjour discovery
        attempted_methods.append('mdns_discovery')
        discovered.extend(self._mdns_discovery(protocol))
            
        # Method 5: Network scanning
        attempted_methods.append('network_scan')
        discovered.extend(self._network_discovery(protocol))
        
        # Cache and return results
        if discovered:
            print(attempted_methods)
            self._cache_results(discovered)
            return discovered

        raise NoScannersFoundError(attempted_methods)
        
    def _get_cached_results(self, protocol: str) -> List[Dict[str, Any]]:
        """Get valid cached results for the specified protocol."""
        results = []
        for addr, info in self._cached_addresses.items():
            if protocol == 'both' or info.get('protocol') == protocol:
                # Verify cached result is still valid (quick check)
                if self._quick_connectivity_check(addr, info.get('port', self.LLRP_PORT)):
                    results.append(info)
                else:
                    # Remove invalid cached entry
                    del self._cached_addresses[addr]
        return results
        
    def _test_address(self, address: str, protocol: str) -> List[Dict[str, Any]]:
        """Test a specific address for RFID scanner availability."""
        results = []
        
        if protocol in ('llrp', 'both'):
            if self._test_llrp(address):
                results.append({
                    'address': address,
                    'protocol': 'llrp',
                    'port': self.LLRP_PORT,
                    'timestamp': time.time()
                })
                
        if protocol in ('rest', 'both'):
            rest_port = self._test_rest(address)
            if rest_port:
                results.append({
                    'address': address,
                    'protocol': 'rest',
                    'port': rest_port,
                    'timestamp': time.time()
                })
                
        return results
        
    def _test_llrp(self, address: str) -> bool:
        """Test if address responds to LLRP protocol on port 5084."""
        return self._quick_connectivity_check(address, self.LLRP_PORT)
        
    def _test_rest(self, address: str) -> Optional[int]:
        """Test if address responds to REST API on common HTTP ports."""
        for port in self.HTTP_PORTS:
            if self._quick_connectivity_check(address, port):
                # Quick HTTP check
                try:
                    url = f"http://{address}:{port}" if port != 80 else f"http://{address}"
                    response = requests.get(url, timeout=self.timeout, verify=False)
                    if response.status_code < 500:  # Any response indicates HTTP service
                        return port
                except:
                    continue
        return None
        
    def _quick_connectivity_check(self, address: str, port: int) -> bool:
        """Quick TCP connectivity check."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((address, port))
            sock.close()
            return result == 0
        except:
            return False
            
    def _mdns_discovery(self, protocol: str) -> List[Dict[str, Any]]:
        """Perform mDNS/Bonjour discovery."""
        try:
            mdns = MDNSDiscovery(timeout=self.timeout)
            results = mdns.discover()
            # Filter by protocol if specified
            if protocol != 'both':
                results = [r for r in results if r.get('protocol') == protocol]
            return results
        except Exception as e:
            print(f"mDNS discovery failed: {e}")
            return []


    def _network_discovery(self, protocol: str) -> List[Dict[str, Any]]:
        """Perform network-wide discovery scan."""
        discovered = []
        scanner = NetworkScanner(timeout=self.timeout)

        # Try ARP cache first — only tests hosts with known MAC addresses,
        # skipping the ~240 stale/incomplete entries common on large networks
        """arp_hosts = self.get_arp_hosts()
        if arp_hosts:
            print(f"Scanning {len(arp_hosts)} ARP-known hosts")
            results = scanner.scan_hosts(arp_hosts)
            if protocol != 'both':
                results = [r for r in results if r.get('protocol') == protocol]
            discovered.extend(results)"""

        # Fall back to full subnet scan if ARP found nothing
        if not discovered:
            print("ARP scan found nothing, falling back to full subnet scan")
            max_hosts = self.config.get_max_hosts_per_subnet()
            if max_hosts < 254:
                print(f"Warning: max_hosts_per_subnet is {max_hosts}, this may miss scanners.")
            subnets = self.get_local_subnets()
            if not subnets:
                subnets = self.config.get_network_scan_subnets()
            for subnet in subnets:
                results = scanner.scan_subnet(subnet, max_hosts=max_hosts)
                if protocol != 'both':
                    results = [r for r in results if r.get('protocol') == protocol]
                discovered.extend(results)
                if discovered:
                    break

        return discovered

    def _cache_results(self, results: List[Dict[str, Any]]):
        """Cache discovery results."""
        for result in results:
            addr = result['address']
            self._cached_addresses[addr] = result
        self._save_cache()
        
    def get_best_scanner(self, 
                        protocol: str = 'both',
                        prefer_cached: bool = True) -> Dict[str, Any]:
        """
        Get the best available scanner.
        
        Returns the first working scanner found, preferring cached results.
        
        Raises:
            NoScannersFoundError: If no scanners available
            MultipleScannersFoundError: If multiple found and user choice needed
        """
        scanners = self.discover(protocol, use_cache=prefer_cached)
        
        if not scanners:
            raise NoScannersFoundError()
            
        # Return first scanner (could be enhanced with scoring/preference logic)
        return scanners[0]
        
    def clear_cache(self):
        """Clear the scanner address cache."""
        self._cached_addresses = {}
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
        except Exception as e:
            print(f"Warning: Could not remove cache file: {e}")
