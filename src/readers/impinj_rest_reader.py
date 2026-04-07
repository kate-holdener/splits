import requests
from urllib.parse import urljoin
from reader import Reader
from entity.event import Event
import json
import base64
from datetime import datetime
from utils.normalized_timestamp import get_timestamp_now
from discovery.exceptions import ConnectionTimeoutError, ProtocolError, AuthenticationError

class ImpinjRestReader(Reader):
    def __init__(self, scanner_address_and_port):
        super().__init__()
        self.scanner = scanner_address_and_port
        self.hostname = 'http://{0}'.format(scanner_address_and_port)
        self.runner_ids = None
        
        # Test connectivity during initialization
        try:
            self._test_connection()
        except requests.exceptions.ConnectTimeout:
            raise ConnectionTimeoutError(scanner_address_and_port, 3.0)
        except requests.exceptions.ConnectionError as e:
            if "Connection refused" in str(e):
                raise ConnectionTimeoutError(scanner_address_and_port, 3.0)
            else:
                raise ProtocolError(scanner_address_and_port, "HTTP/REST", str(e))
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError(scanner_address_and_port, "HTTP 401 Unauthorized")
            elif e.response.status_code == 403:
                raise AuthenticationError(scanner_address_and_port, "HTTP 403 Forbidden")
            else:
                raise ProtocolError(scanner_address_and_port, "HTTP/REST", f"HTTP {e.response.status_code}")
        except Exception as e:
            raise ProtocolError(scanner_address_and_port, "HTTP/REST", str(e))
            
    def _test_connection(self):
        """Test basic connectivity to the scanner."""
        try:
            response = requests.get(
                urljoin(self.hostname, 'api/v1/status'),
                timeout=3.0,
                verify=False)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise requests.exceptions.ConnectTimeout()
        except requests.exceptions.RequestException:
            raise

    def connect(self):
        # Stop any active preset
        stop_response = requests.post(
            urljoin(self.hostname, 'api/v1/profiles/stop'), 
            verify=False, 
            timeout=5.0
        )
        
        # Start the default preset
        start_response = requests.post(
            urljoin(self.hostname, 'api/v1/profiles/inventory/presets/default/start'), 
            verify=False,
            timeout=5.0
        )
        start_response.raise_for_status()
    
    def get_protocol(self):
        return "REST"
    
    def get_address(self):
        return self.hostname
    
    def filter_by_id(self, runner_ids):
        self.runner_ids = runner_ids
        print(self.runner_ids)

    def normalize_epc(epc):
        """Remove leading zeros from EPC, but keep it as a string"""
        return epc.lstrip('0') or '0'  # The 'or 0' handles the case where epc is all zeros



    def base64_to_hex(base64_string):
        """Convert base64 encoded EPC to hexadecimal"""
        try:
            # Decode base64 to bytes
            epc_bytes = base64.b64decode(base64_string)
            # Convert bytes to hex string (uppercase, no separators)
            hex_string = epc_bytes.hex().upper()
            return hex_string
        except Exception as e:
            #print(f"Error converting base64 to hex: {e}")
            return base64_string  # Return original if conversion fails


    def iso_to_seconds(iso_timestamp):
        """Convert ISO 8601 timestamp to seconds since epoch"""
        # Remove the 'Z' and parse
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        # Convert to seconds since epoch
        return int(dt.timestamp())
        
    def extract_rfid_data(self, raw_data):
        if raw_data is None:
            return None
        # Decode bytes to string and strip whitespace
        json_string = raw_data.decode('utf-8').strip()
        if not json_string:
            return None
        data = json.loads(json_string)
        if 'tagInventoryEvent' in data and 'epc' in data['tagInventoryEvent']:
            id = ImpinjRestReader.base64_to_hex(data['tagInventoryEvent']['epc'])
            id = ImpinjRestReader.normalize_epc(id)
            #print(f"Got EPC: {repr(id)}, runner_ids: {self.runner_ids}, match: {id in self.runner_ids}")  # <-- add this

            if not self.runner_ids or id in self.runner_ids:
                event = Event(id, get_timestamp_now())
                return event
        return None
        
    def _run(self):
        try:
            # Connect to the event stream
            stream_response = requests.get(
                urljoin(self.hostname, 'api/v1/data/stream'),
                verify=False, 
                stream=True,
                timeout=10.0
            )
            stream_response.raise_for_status()
            
            while self.running:
                try:
                    for event_data in stream_response.iter_lines():
                        if not self.running:
                            break
                        event = self.extract_rfid_data(event_data)
                        if event:
                            self.queue.put(event)
                            
                except requests.exceptions.ChunkedEncodingError:
                    print("Warning: Connection interrupted, attempting to reconnect...")
                    # Try to reconnect
                    try:
                        stream_response = requests.get(
                            urljoin(self.hostname, 'api/v1/data/stream'),
                            verify=False, 
                            stream=True,
                            timeout=10.0
                        )
                        stream_response.raise_for_status()
                    except Exception as e:
                        print(f"Failed to reconnect: {e}")
                        break
                        
        except requests.exceptions.ConnectTimeout:
            print(f"Timeout connecting to REST reader at {self.hostname}")
            raise ConnectionTimeoutError(self.scanner, 5.0)
        except requests.exceptions.ConnectionError as e:
            if "Connection refused" in str(e):
                print(f"Connection refused by REST reader at {self.hostname}")
                raise ConnectionTimeoutError(self.scanner, 5.0)
            else:
                print(f"Connection error with REST reader: {e}")
                raise ProtocolError(self.scanner, "HTTP/REST", str(e))
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError(self.scanner, "HTTP 401 Unauthorized")
            elif e.response.status_code == 403:
                raise AuthenticationError(self.scanner, "HTTP 403 Forbidden")
            else:
                raise ProtocolError(self.scanner, "HTTP/REST", f"HTTP {e.response.status_code}")
        except Exception as e:
            print(f"Error in REST reader: {e}")
            raise ProtocolError(self.scanner, "HTTP/REST", str(e))
