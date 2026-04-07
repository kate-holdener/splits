"""
Configuration management for interval timer RFID discovery.

This module provides utilities for loading and managing configuration
from various sources: environment variables, config files, and defaults.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List


class ConfigManager:
    """Manages configuration for RFID discovery system."""
    
    DEFAULT_CONFIG = {
        'scanner_addresses': [],
        'discovery': {
            'timeout': 3.0,
            'use_cache': True,
            'methods': [
                'environment_variable',
                'config_file',
                'default_addresses',
                'mdns_discovery',
                'upnp_discovery',
                'network_scan'
            ]
        },
        'network_scan': {
            'subnets': ['169.254.1', '169.254.45', '192.168.1', '192.168.0', '10.0.0', '127.0.0.1'],
            'max_hosts': 254
        },
        'cache': {
            'directory': '~/.cache/interval_timer',
            'expiry_hours': 24
        },
        'logging': {
            'level': 'INFO',
            'discovery_debug': False
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to config file, or None to search default locations
        """
        self.config_file = config_file
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file and environment variables."""
        config = self.DEFAULT_CONFIG.copy()
        
        # Load from config file
        config_path = self._find_config_file()
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    file_config = yaml.safe_load(f) or {}
                config = self._merge_config(config, file_config)
            except Exception as e:
                print(f"Warning: Could not load config file {config_path}: {e}")
                
        # Override with environment variables
        self._apply_env_overrides(config)
        
        return config
        
    def _find_config_file(self) -> Optional[str]:
        """Find configuration file in default locations."""
        if self.config_file:
            return self.config_file if os.path.exists(self.config_file) else None
            
        # Search default locations
        search_paths = [
            'config.yaml',
            'config.yml',
            os.path.expanduser('~/.interval_timer/config.yaml'),
            os.path.expanduser('~/.config/interval_timer/config.yaml'),
            '/etc/interval_timer/config.yaml'
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                return path
                
        return None
        
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def _apply_env_overrides(self, config: Dict[str, Any]):
        """Apply environment variable overrides to configuration."""
        # RFID_SCANNER_ADDRESS - override scanner addresses
        env_address = os.getenv('RFID_SCANNER_ADDRESS')
        if env_address:
            config['scanner_addresses'] = [env_address]
            
        # RFID_DISCOVERY_TIMEOUT - override discovery timeout
        env_timeout = os.getenv('RFID_DISCOVERY_TIMEOUT')
        if env_timeout:
            try:
                config['discovery']['timeout'] = float(env_timeout)
            except ValueError:
                pass
                
        # RFID_CACHE_DIR - override cache directory
        env_cache_dir = os.getenv('RFID_CACHE_DIR')
        if env_cache_dir:
            config['cache']['directory'] = env_cache_dir
            
        # RFID_DEBUG - enable debug logging
        if os.getenv('RFID_DEBUG', '').lower() in ('1', 'true', 'yes'):
            config['logging']['level'] = 'DEBUG'
            config['logging']['discovery_debug'] = True
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key."""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def get_scanner_addresses(self) -> List[str]:
        """Get list of scanner addresses to try."""
        return self.get('scanner_addresses', self.DEFAULT_CONFIG['scanner_addresses'])
        
    def get_discovery_timeout(self) -> float:
        """Get discovery connection timeout."""
        return self.get('discovery.timeout', self.DEFAULT_CONFIG['discovery']['timeout'])
        
    def get_cache_directory(self) -> str:
        """Get cache directory path."""
        cache_dir = self.get('cache.directory', self.DEFAULT_CONFIG['cache']['directory'])
        return os.path.expanduser(cache_dir)
        
    def get_network_scan_subnets(self) -> List[str]:
        """Get subnets for network scanning."""
        return self.get('network_scan.subnets', self.DEFAULT_CONFIG['network_scan']['subnets'])
        
    def get_max_hosts_per_subnet(self) -> int:
        """Get maximum hosts to scan per subnet."""
        return self.get('network_scan.max_hosts', self.DEFAULT_CONFIG['network_scan']['max_hosts'])
        
    def is_discovery_debug_enabled(self) -> bool:
        """Check if discovery debug logging is enabled."""
        return self.get('logging.discovery_debug', self.DEFAULT_CONFIG['logging']['discovery_debug'])


def load_config(config_file: Optional[str] = None) -> ConfigManager:
    """
    Load configuration from file and environment.
    
    Args:
        config_file: Optional path to config file
        
    Returns:
        ConfigManager instance
    """
    return ConfigManager(config_file)
