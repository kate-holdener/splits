import requests
from urllib.parse import urljoin
from reader import Reader
from entity.event import Event
import json
import base64
from datetime import datetime
class ImpinjRestReader(Reader):
    def __init__(self, queue, scanner_address, runner_ids):
        super().__init__(queue)
        self.scanner = scanner_address
        self.hostname = 'https://root:impinj@{0}'.format(scanner_address)
        self.runner_ids = runner_ids

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
            if id in self.runner_ids:
                event = Event()
                event.id = id
                event.timestamp = ImpinjRestReader.iso_to_seconds(data['timestamp'])
                return event
        return None
        
    def _run(self):
        requests.post(urljoin(self.hostname, 'api/v1/profiles/stop'), verify=False) # Stop the active preset
        requests.post(urljoin(self.hostname, 'api/v1/profiles/inventory/presets/default/start'), verify=False) # Start the default preset
        while self.running:
            for event_data in requests.get(urljoin(self.hostname, 'api/v1/data/stream'),verify=False, stream=True).iter_lines(): # Connect to the event stream
                event = self.extract_rfid_data(event_data)
                if event:
                    self.queue.put(event)
