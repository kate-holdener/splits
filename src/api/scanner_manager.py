from queue import Queue
from typing import Optional

from readers.acr122u_nfc import NFCReader
from reader import Reader
from discovery.auto_connect import auto_connect_to_rfid_scanner, connect_rfid_with_scanner_info
from persistence.scanner_persistence import save_scanner_config, load_scanner_config


class ScannerManager:
    """Manages RFID and NFC scanner hardware lifecycle. No athlete or workout knowledge."""

    def __init__(self, lap_event_q: Queue, start_event_q: Queue):
        self.lap_event_q = lap_event_q
        self.start_event_q = start_event_q

        self.rfid_scanner = None
        self.nfc_scanner = None
        self.rfid_connected = False
        self.nfc_connected = False
        self.rfid_scanner_failed = False
        self.nfc_scanner_failed = False

        self.rfid_protocol: Optional[str] = None
        self.rfid_address: Optional[str] = None
        self.rfid_port: Optional[int] = None

        self.saved_scanner_config = load_scanner_config()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _activate_rfid_reader(self, reader: Reader, hostname: str) -> dict:
        """Start the reader thread and record RFID connection state."""
        reader.start(self.lap_event_q)
        self.rfid_scanner = reader
        self.rfid_connected = True
        self.rfid_scanner_failed = False

        protocol = reader.get_protocol().lower()
        port = reader.get_port()

        self.rfid_protocol = protocol
        self.rfid_address = hostname
        self.rfid_port = port

        save_scanner_config(hostname, port, protocol)

        return {
            "ok": True,
            "msg": f"Connected via {protocol.upper()} to {hostname}:{port}",
            "connection_details": {"address": hostname, "port": port, "protocol": protocol},
        }

    def _stop_reader(self, reader: Optional[Reader]) -> None:
        """Stop a reader thread, suppressing all errors."""
        if reader:
            try:
                reader.stop()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # RFID connect
    # ------------------------------------------------------------------

    def connect_rfid(self):
        """Connect to RFID scanner with auto-discovery."""
        try:
            reader = auto_connect_to_rfid_scanner()
            protocol = reader.get_protocol().lower()
            address = reader.get_address()
            if protocol == 'llrp':
                hostname = address.split(':')[0]
            else:
                hostname = address.replace('http://', '').split(':')[0]
            return self._activate_rfid_reader(reader, hostname)
        except Exception as e:
            return {"ok": False, "msg": f"Auto-connection failed: {e}"}

    def connect_rfid_with_address(self, address: str):
        """Connect to RFID scanner at a specific IP address, trying LLRP then REST."""
        if not address or not address.strip():
            return {"ok": False, "msg": "IP address is required."}
        address = address.strip()
        default_ports = {'llrp': 5084, 'rest': 80}
        for protocol in ('llrp', 'rest'):
            scanner_info = {"address": address, "protocol": protocol, "port": default_ports[protocol]}
            result, reader = connect_rfid_with_scanner_info(scanner_info)
            if result["ok"] and reader:
                return self._activate_rfid_reader(reader, address)
        self.rfid_scanner_failed = True
        return {"ok": False, "msg": f"Could not connect to RFID scanner at {address}."}

    def connect_rfid_manual(self, address: str, port: int, protocol: str):
        """Connect to RFID scanner with manual configuration (IP, port, protocol)."""
        if not address or not address.strip():
            return {"ok": False, "msg": "IP address is required."}
        if protocol not in ('llrp', 'rest'):
            return {"ok": False, "msg": "Protocol must be 'llrp' or 'rest'."}
        if not isinstance(port, int) or port < 1 or port > 65535:
            return {"ok": False, "msg": "Port must be between 1 and 65535."}

        address = address.strip()
        scanner_info = {"address": address, "protocol": protocol, "port": port}
        result, reader = connect_rfid_with_scanner_info(scanner_info)

        if result["ok"] and reader:
            return self._activate_rfid_reader(reader, address)
        self.rfid_scanner_failed = True
        return {"ok": False, "msg": f"Could not connect to RFID scanner at {address}:{port} using {protocol.upper()}."}

    # ------------------------------------------------------------------
    # RFID disconnect
    # ------------------------------------------------------------------

    def disconnect_rfid(self):
        """Disconnect the currently connected RFID scanner."""
        if not self.rfid_connected:
            return {"ok": False, "msg": "RFID scanner is not connected."}
        self._stop_reader(self.rfid_scanner)
        self.rfid_scanner = None
        self.rfid_connected = False
        self.rfid_scanner_failed = False
        self.rfid_protocol = None
        self.rfid_address = None
        self.rfid_port = None
        return {"ok": True, "msg": "RFID scanner disconnected."}

    # ------------------------------------------------------------------
    # RFID helpers
    # ------------------------------------------------------------------

    def get_rfid_connection_info(self):
        return self._get_connection_info(self.rfid_scanner)

    def get_saved_scanner_config(self):
        return self.saved_scanner_config

    def try_auto_connect_rfid(self):
        """Attempt to auto-connect using saved scanner configuration."""
        if not self.saved_scanner_config:
            return {"ok": False, "msg": "No saved scanner configuration."}
        if self.rfid_connected:
            return {"ok": False, "msg": "RFID scanner already connected."}
        config = self.saved_scanner_config
        return self.connect_rfid_manual(config['hostname'], config['port'], config['protocol'])

    # ------------------------------------------------------------------
    # NFC connect / disconnect
    # ------------------------------------------------------------------

    def connect_nfc(self):
        """Connect to the ACR122U NFC scanner."""
        if self.nfc_connected and self.nfc_scanner:
            return {"ok": True, "msg": "NFC scanner already connected."}
        self._stop_reader(self.nfc_scanner)
        try:
            self.nfc_scanner = NFCReader()
            self.nfc_scanner.start(self.start_event_q)
            self.nfc_connected = True
            self.nfc_scanner_failed = False
            return {"ok": True, "msg": "NFC scanner connected."}
        except Exception as e:
            self.nfc_scanner_failed = True
            return {"ok": False, "msg": f"NFC failed: {e}"}

    def disconnect_nfc(self):
        """Disconnect the currently connected NFC scanner."""
        if not self.nfc_connected:
            return {"ok": False, "msg": "NFC scanner is not connected."}
        self._stop_reader(self.nfc_scanner)
        self.nfc_scanner = None
        self.nfc_connected = False
        self.nfc_scanner_failed = False
        return {"ok": True, "msg": "NFC scanner disconnected."}

    # ------------------------------------------------------------------
    # Shared info helper
    # ------------------------------------------------------------------

    def get_nfc_connection_info(self):
        return self._get_connection_info(self.nfc_scanner)

    def _get_connection_info(self, reader: Optional[Reader]) -> dict:
        if reader and reader.is_connected():
            return {
                "connected": True,
                "address":   reader.get_address(),
                "port":      reader.get_port(),
                "protocol":  reader.get_protocol(),
            }
        return {"connected": False}

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self):
        """Stop all connected scanners so they stop feeding the event queues."""
        self._stop_reader(self.rfid_scanner)
        self._stop_reader(self.nfc_scanner)
