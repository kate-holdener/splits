import time
import logging
from sllurp import llrp
from sllurp.llrp import LLRPReaderConfig, LLRPReaderClient, LLRP_DEFAULT_PORT

from reader import Reader
from entity.event import Event

class LLRPReader(Reader):
    def __init__(self, queue, scanner_address, runner_ids, port=LLRP_DEFAULT_PORT):
        super().__init__(queue)
        self.host = scanner_address
        self.port = port
        self.runner_ids = runner_ids
        self.reader = None

    @staticmethod
    def normalize_epc(epc):
        return epc.lstrip('0') or '0'

    def _on_tag_report(self, reader, tag_reports):
        for tag in tag_reports:
            try:
                print(tag)
                # sllurp tag info typically contains .epc
                epc = tag.get('EPC').decode('utf-8') if isinstance(tag.get('EPC'), bytes) else str(tag.get('EPC'))
                epc = epc.upper()
                
                normalized = self.normalize_epc(epc)
                if normalized in self.runner_ids:
                    event = Event()
                    event.id = normalized
                    # sllurp tags have timestamp in tag.LastSeenTimestampUTC(nanoseconds)
                    event.timestamp = int(tag.get('LastSeenTimestampUTC')) / 1_000_000
                    self.queue.put(event)

            except Exception as e:
                print(f"Error in tag callback: {e}")

    def _run(self):
        # Optional: enable sllurp debug logs
        logging.getLogger('sllurp').setLevel(logging.INFO)

        try:
            config = LLRPReaderConfig()
            config.tag_content_selector={
                    'EnableAntennaID': True,
                    'EnablePeakRSSI': True,
                    'EnableLastSeenTimestamp': True,
                    'EnableTagSeenCount': True,
            }
            #config.antennas[1] = {'enabled': True, 'tx_power': 30.0}  # dBm
            self.reader = LLRPReaderClient(self.host, self.port, config)

            # Register the callback handler
            self.reader.add_tag_report_callback(self._on_tag_report)

            # Connect and begin inventory
            print(f"Connecting to reader at {self.host}:{self.port}...")
            self.reader.connect()
            print("Connected — inventory started")

            # This will block until disconnect() is called
            self.reader.join(None)

        except Exception as e:
            print(f"Error in sllurp reader: {e}")

        finally:
            if self.reader:
                try:
                    self.reader.disconnect()
                except:
                    pass
            print("Sllurp reader stopped")
