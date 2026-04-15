from readers.sllurp_reader import LLRPReader
from readers.impinj_rest_reader import ImpinjRestReader
from discovery.rfid_discovery import RFIDDiscovery
from discovery.exceptions import ConnectionTimeoutError, ProtocolError, NoScannersFoundError
from reader import Reader

def auto_connect_to_rfid_scanner() -> Reader:
    # Try auto-discovery for both LLRP and REST protocols
    try:
        discovery = RFIDDiscovery(timeout=3.0)
        scanners = discovery.discover(protocol='both', use_cache=True)
    except Exception:
        return None
    
    for scanner in scanners:
        try:
            connection, reader = connect_rfid_with_scanner_info(scanner)
            if connection['ok']:
                return reader
        except Exception as e:
            pass
    raise NoScannersFoundError()

def connect_rfid_with_scanner_info(scanner_info: dict):        
    address = scanner_info['address']
    protocol = scanner_info['protocol']
    port = scanner_info.get('port', 5084)
    rfid_scanner = None
    try:
        # Instantiate the appropriate reader based on discovered protocol
        if protocol == 'llrp':
            rfid_scanner = LLRPReader(address, port)
        elif protocol == 'rest':
            rfid_scanner = ImpinjRestReader(address, port)
        else:
            return ({"ok": False,
                    "msg": f"Unknown protocol '{protocol}' for scanner at {address}"}, None)
        
        # Try to connect - both readers now return boolean
        if rfid_scanner.connect():
            return ({"ok": True,
                     "msg": f"Connected to {rfid_scanner.get_protocol()}"}, rfid_scanner) 
        else:
            return ({"ok": False, 
                     "msg": f"Failed to connect to {protocol.upper()} scanner at {address}:{port}"}, None)
            
    except ConnectionTimeoutError as e:
        return ({"ok": False, "msg": f"Connection timeout: {e}"}, None)
    except ProtocolError as e:
        return ({"ok": False, "msg": f"Protocol error: {e}"}, None)
    except Exception as e:
        return ({"ok": False, "msg": f"RFID failed: {e}"}, None)
    