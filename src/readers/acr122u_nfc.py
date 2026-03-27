"""
acr122u_nfc.py
--------------
A Python module for detecting and reading NFC tags using the ACR122U reader.

Dependencies:
    pip install pyscard

On Linux you may also need:
    sudo apt install pcscd pcsc-tools libpcsclite-dev
    sudo systemctl start pcscd
"""

import time
from queue import Queue
from reader import Reader
from typing import Optional, Callable
from smartcard.System import readers
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.util import toHexString
from smartcard.Exceptions import CardConnectionException, NoCardException
from entity.event import Event
from utils.normalized_timestamp import get_timestamp_now
# ---------------------------------------------------------------------------
# APDU Commands for ACR122U
# ---------------------------------------------------------------------------
GET_UID_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
GET_ATS_APDU = [0xFF, 0xCA, 0x01, 0x00, 0x00]

# NFC tag type identifiers (based on SAK / ATQ bytes)
TAG_TYPES = {
    "ISO14443A": "ISO 14443-A (NFC-A)",
    "ISO14443B": "ISO 14443-B (NFC-B)",
    "MIFARE_CLASSIC_1K": "MIFARE Classic 1K",
    "MIFARE_CLASSIC_4K": "MIFARE Classic 4K",
    "MIFARE_ULTRALIGHT": "MIFARE Ultralight / NTAG",
    "MIFARE_DESFIRE": "MIFARE DESFire",
    "FELICA": "FeliCa",
    "UNKNOWN": "Unknown",
}


# ---------------------------------------------------------------------------
# NFCTag dataclass
# ---------------------------------------------------------------------------
class NFCTag:
    """Represents a detected NFC tag."""

    def __init__(self, uid: str, tag_type: str, atr: list[int]):
        self.uid = uid                  # Hex string, e.g. "04 AB CD 12"
        self.tag_type = tag_type        # Human-readable tag type
        self.atr = toHexString(atr)     # Answer To Reset bytes

    def __repr__(self):
        return (
            f"NFCTag(uid='{self.uid}', "
            f"type='{self.tag_type}', "
            f"atr='{self.atr}')"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _identify_tag_type(atr: list[int]) -> str:
    """
    Heuristically identify NFC tag type from the ATR bytes
    returned by the ACR122U.

    ATR format for ACR122U (contactless):
      3B 8F 80 01 80 4F 0C A0 00 00 03 06 [RID] [SS] [BB] [CC] [DD] [checksum]
    Bytes of interest:
      index 12 → T0 / standard indicator
      index 13 → SS = tag type byte
      index 14 → BB = bit-rate / protocol
    """
    atr_hex = toHexString(atr)

    # FeliCa — ATR contains "03 F0" or "03 F1"
    if len(atr) >= 15 and atr[13] in (0xF0, 0xF1):
        return TAG_TYPES["FELICA"]

    # MIFARE DESFire — SS = 0x20
    if len(atr) >= 14 and atr[13] == 0x20:
        return TAG_TYPES["MIFARE_DESFIRE"]

    # MIFARE Classic 1K — SS = 0x08 or 0x88
    if len(atr) >= 14 and atr[13] in (0x08, 0x88):
        return TAG_TYPES["MIFARE_CLASSIC_1K"]

    # MIFARE Classic 4K — SS = 0x18
    if len(atr) >= 14 and atr[13] == 0x18:
        return TAG_TYPES["MIFARE_CLASSIC_4K"]

    # MIFARE Ultralight / NTAG — SS = 0x00
    if len(atr) >= 14 and atr[13] == 0x00:
        return TAG_TYPES["MIFARE_ULTRALIGHT"]

    # ISO 14443-B
    if len(atr) >= 14 and atr[12] == 0x00:
        return TAG_TYPES["ISO14443B"]

    # Generic ISO 14443-A fallback
    if len(atr) >= 2:
        return TAG_TYPES["ISO14443A"]

    return TAG_TYPES["UNKNOWN"]


def _get_uid(connection) -> Optional[str]:
    """Send GET UID APDU and return hex UID string, or None on failure."""
    try:
        response, sw1, sw2 = connection.transmit(GET_UID_APDU)
        if sw1 == 0x90 and sw2 == 0x00:
            return toHexString(response)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# One-shot detection
# ---------------------------------------------------------------------------

def detect_tag(reader_index: int = 0, timeout: float = 10.0) -> Optional[NFCTag]:
    """
    Block until an NFC tag is detected (or timeout expires).

    Args:
        reader_index: Index of the reader in the system reader list (default 0).
        timeout:      Seconds to wait before giving up (default 10 s).

    Returns:
        NFCTag instance if a tag was found, None otherwise.
    """
    available = readers()
    if not available:
        raise RuntimeError("No PC/SC readers found. Is pcscd running?")

    reader = available[reader_index]
    print(f"[acr122u_nfc] Using reader: {reader}")

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            connection = reader.createConnection()
            connection.connect()
            atr = connection.getATR()
            uid = _get_uid(connection)
            tag_type = _identify_tag_type(atr)
            connection.disconnect()
            return NFCTag(uid=uid or "N/A", tag_type=tag_type, atr=atr)
        except NoCardException:
            time.sleep(0.2)
        except CardConnectionException:
            time.sleep(0.2)
        except Exception as exc:
            print(f"[acr122u_nfc] Warning: {exc}")
            time.sleep(0.5)

    return None  # timed out


# ---------------------------------------------------------------------------
# Continuous monitoring with callback
# ---------------------------------------------------------------------------

class _TagObserver(CardObserver):
    """Internal CardObserver that fires a user-supplied callback."""

    def __init__(self, on_tag: Callable[[NFCTag], None], on_removed: Optional[Callable] = None):
        self._on_tag = on_tag
        self._on_removed = on_removed

    def update(self, observable, actions):
        added, removed = actions

        for card in added:
            try:
                connection = card.createConnection()
                connection.connect()
                atr = connection.getATR()
                uid = _get_uid(connection)
                tag_type = _identify_tag_type(atr)
                connection.disconnect()
                tag = NFCTag(uid=uid or "N/A", tag_type=tag_type, atr=atr)
                self._on_tag(tag)
            except Exception as exc:
                print(f"[acr122u_nfc] Error reading tag: {exc}")

        if self._on_removed:
            for _ in removed:
                self._on_removed()


class NFCReader(Reader):
    """
    Continuously monitor for NFC tag insertions and removals.

    Usage:
        def handle(tag):
            print("Tag detected:", tag)

        monitor = NFCMonitor(on_tag=handle)
        monitor.start()
        # ... do other work or sleep ...
        monitor.stop()
    """

    def __init__(
        self,
        event_q: Queue
    ):
        super().__init__(event_q)
        self._observer = _TagObserver(self.tag_detected, None)
        self._monitor = CardMonitor()
        available = readers()
        print(available)
        if not available:
            raise ConnectionError("Connection to NFC Scanner failed")

    def tag_detected(self, tag: NFCTag):
        timestamp =  get_timestamp_now()
        event = Event(tag.uid, timestamp)
        with open("nfc.txt", "a") as f:
            f.write(f"NFC, {tag.uid}, {timestamp}\n")
        print(event)
        self.queue.put(event)

    def _run(self):
        """Begin monitoring. Non-blocking — runs in a background thread."""
        
        print(self._monitor.addObserver(self._observer))
        print("[acr122u_nfc] Monitoring started.")
        print(self._observer)
        # Keep running while callback handles tags
        while self.running:
            time.sleep(0.1)
        self._stop()  

    def _stop(self):
        """Stop monitoring."""
        if self._monitor:
            self._monitor.deleteObserver(self._observer)
            self._monitor = None
        print("[acr122u_nfc] Monitoring stopped.")



