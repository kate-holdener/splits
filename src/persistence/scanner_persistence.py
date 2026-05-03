"""
RFID scanner connection persistence.

Stores the last successful RFID scanner connection parameters to enable
automatic reconnection on application startup.

File structure:
  <user_data_dir>/
  └── scanner_config.json    (saved scanner connection parameters)
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any

from persistence.user_data_dir import get_user_data_dir


def get_scanner_config_path(data_dir=None) -> str:
    """Return path to the scanner config file."""
    if data_dir is None:
        base = get_user_data_dir()
    else:
        base = Path(data_dir)
    return str(base / "scanner_config.json")


def save_scanner_config(hostname: str, port: int, protocol: str,
                        tx_power_dbm: float = None, data_dir=None) -> None:
    """Save successful scanner connection parameters.

    Args:
        hostname: Scanner IP address/hostname
        port: Scanner port number
        protocol: 'llrp' or 'rest'
        tx_power_dbm: Transmit power in dBm (LLRP only); None uses reader default
    """
    config_path = get_scanner_config_path(data_dir)

    config = {
        "hostname": hostname.strip(),
        "port": int(port),
        "protocol": protocol.lower(),
        "tx_power_dbm": float(tx_power_dbm) if tx_power_dbm is not None else None,
    }
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save scanner config: {e}")


def load_scanner_config(data_dir=None) -> Optional[Dict[str, Any]]:
    """Load saved scanner connection parameters.
    
    Returns:
        Dict with keys 'hostname', 'port', 'protocol' or None if no config exists
    """
    config_path = get_scanner_config_path(data_dir)
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        # Validate config structure
        if not isinstance(config, dict):
            return None
            
        required_keys = {'hostname', 'port', 'protocol'}
        if not all(key in config for key in required_keys):
            return None
            
        # Validate values
        if not isinstance(config['hostname'], str) or not config['hostname'].strip():
            return None
        if not isinstance(config['port'], int) or not (1 <= config['port'] <= 65535):
            return None
        if config['protocol'] not in ('llrp', 'rest'):
            return None
            
        raw_power = config.get('tx_power_dbm')
        tx_power_dbm = float(raw_power) if raw_power is not None else None

        return {
            'hostname': config['hostname'].strip(),
            'port': int(config['port']),
            'protocol': config['protocol'].lower(),
            'tx_power_dbm': tx_power_dbm,
        }
        
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        # Malformed or corrupt config
        print(f"Warning: Corrupt scanner config file at {config_path}")
        return None


def clear_scanner_config(data_dir=None) -> None:
    """Remove saved scanner configuration."""
    config_path = get_scanner_config_path(data_dir)
    
    try:
        Path(config_path).unlink(missing_ok=True)
    except Exception as e:
        print(f"Warning: Failed to clear scanner config: {e}")