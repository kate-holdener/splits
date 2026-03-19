import time
import logging
from sllurp import llrp
from sllurp.llrp import LLRPReaderConfig, LLRPReaderClient, LLRP_DEFAULT_PORT
from utils.normalized_timestamp import get_timestamp_now
from reader import Reader
from entity.event import Event
from datetime import datetime, timezone

class LLRPReader(Reader):
    def __init__(self, queue, scanner_address, runner_ids, port=LLRP_DEFAULT_PORT):
        super().__init__(queue)
        self.host = scanner_address
        self.port = port
        self.runner_ids = runner_ids
        self.reader = None
        try: 
            self.reader = LLRPReader._init_reader(self.host, self.port)
        except Exception as e:
            raise ConnectionError(f"could not connect to {self.host}:{self.port}")

    @staticmethod
    def normalize_epc(epc):
        return epc.lstrip('0') or '0'

    @staticmethod
    def _init_reader(host, port)->LLRPReaderClient:
        # Optional: enable sllurp debug logs
        logging.getLogger('sllurp').setLevel(logging.INFO)
        factory_args = dict(
            report_every_n_tags=1,
            antennas=[0],
            tx_power=30,
            start_inventory=True,
            tag_content_selector={
                'EnableROSpecID': True,
                'EnableSpecIndex': True,
                'EnableInventoryParameterSpecID': True,
                'EnableAntennaID': True,
                'EnableChannelIndex': True,
                'EnablePeakRSSI': True,
                'EnableFirstSeenTimestamp': True,
                'EnableLastSeenTimestamp': True,
                'EnableTagSeenCount': True,
                'EnableAccessSpecID': True,
                'C1G2EPCMemorySelector': {
                    'EnableCRC': True,
                    'EnablePCBits': True,
                }
            },
            impinj_search_mode=2,
            impinj_tag_content_selector=None,
        )

        config = LLRPReaderConfig(factory_args)
        reader = LLRPReaderClient(host, port, config)
        return reader

    def _on_tag_report(self, reader, tag_reports):
        for tag in tag_reports:
            try:
                # sllurp tag info typically contains .epc
                epc = tag.get('EPC').decode('utf-8') if isinstance(tag.get('EPC'), bytes) else str(tag.get('EPC'))
                epc = epc.upper()
                
                normalized = self.normalize_epc(epc)
                if normalized in self.runner_ids:
                    # sllurp tags have timestamp in tag.LastSeenTimestampUTC(nanoseconds)
                    #event.timestamp = int(tag.get('LastSeenTimestampUTC')) / 1_000_000
                    timestamp = get_timestamp_now() #int(datetime.now(timezone.utc).timestamp())
                    event = Event(normalized, timestamp)
                    self.queue.put(event)

            except Exception as e:
                print(f"Error in tag callback: {e}")

    def _run(self):
        if not self.reader:
            return
        
        try:
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
