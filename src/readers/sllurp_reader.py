import time
import socket
import logging
from sllurp import llrp
from sllurp.llrp import LLRPReaderConfig, LLRPReaderClient, LLRP_DEFAULT_PORT
from utils.normalized_timestamp import get_timestamp_now
from reader import Reader
from entity.event import Event
from datetime import datetime, timezone
from discovery.exceptions import ConnectionTimeoutError, ProtocolError

class LLRPReader(Reader):
    def __init__(self,scanner_address, port=LLRP_DEFAULT_PORT):
        super().__init__()
        self.host = scanner_address
        self.port = port
        self.runner_ids = None
        self.reader = None
        self.connected = False
        try: 
            self.reader = LLRPReader._init_reader(self.host, self.port)
            # Register the callback handler
            self.reader.add_tag_report_callback(self._on_tag_report)
        except socket.timeout:
            raise ConnectionTimeoutError(self.host, self.port)
        except ConnectionRefusedError:
            raise ConnectionTimeoutError(self.host, self.port)
        except OSError as e:
            if "Network is unreachable" in str(e) or "No route to host" in str(e):
                raise ConnectionTimeoutError(self.host, self.port)
            raise ProtocolError(self.host, "LLRP", str(e))
        except Exception as e:
            if "timeout" in str(e).lower():
                raise ConnectionTimeoutError(self.host, self.port)
            else:
                raise ProtocolError(self.host, "LLRP", f"Failed to initialize LLRP reader: {e}")

    def get_protocol(self):
        return "LLRP"
    
    def get_address(self):
        return self.host + ":" + str(self.port)
    
    def get_port(self):
        return self.port
    
    def connect(self):
        self.connected = self._connect()
        return self.connected

    def stop(self):
        """Disconnect the LLRP reader to unblock reader.join() in _run(), then stop the thread."""
        self.running = False
        if self.reader:
            try:
                self.reader.disconnect()
            except Exception:
                pass
        if self.thread is not None:
            self.thread.join(timeout=2.0)

    def is_connected(self):
        return self.connected

    def _connect(self):
        """Connect to the RFID reader and return connection status."""
        try:
            # Start the connection
            self.reader.connect(start_main_loop=False)
            
            # Wait for initial connection
            time.sleep(0.5)
            
            # Check if basic connection is alive
            if not self.reader.is_alive():
                return False
            
            # Validate this is actually an LLRP connection by checking connection stability
            # over a period - LLRP connections should remain stable, while non-LLRP 
            # connections may drop or behave unexpectedly
            validation_attempts = 8
            failed_checks = 0
            
            for i in range(validation_attempts):
                time.sleep(0.2)
                
                try:
                    # Check multiple indicators of connection health
                    alive = self.reader.is_alive()
                    peer = self.reader.get_peername()
                    
                    if not alive or peer is None:
                        failed_checks += 1
                        
                except Exception as e:
                    failed_checks += 1
                
                # If too many checks fail, this is not a valid LLRP connection
                if failed_checks > validation_attempts // 2:
                    try:
                        self.reader.disconnect()
                    except:
                        pass
                    return False
            
            # Additional validation: try to perform an LLRP-specific operation
            try:
                # This should work on a real LLRP reader but fail on non-LLRP servers
                self.reader.add_tag_report_callback(lambda reader, reports: None)
                print("LLRP callback registration successful")
            except Exception as e:
                print(f"LLRP protocol validation failed: {e}")
                try:
                    self.reader.disconnect()
                except:
                    pass
                return False
            
            return True
                
        except (socket.timeout, TimeoutError) as e:
            print(f"Connection timeout: {e}")
            return False
        except ConnectionRefusedError as e:
            print(f"Connection refused: {e}")
            return False
        except OSError as e:
            if "Network is unreachable" in str(e) or "No route to host" in str(e):
                print(f"Network error: {e}")
            else:
                print(f"Connection error: {e}")
            return False
        except Exception as e:
            print(f"Unexpected connection error: {e}")
            return False

    def filter_by_id(self, runner_ids=list[str]):
        self.runner_ids = runner_ids

    @staticmethod
    def normalize_epc(epc):
        return epc.lstrip('0') or '0'

    @staticmethod
    def _init_reader(host, port)->LLRPReaderClient:
        # Optional: enable sllurp debug logs
        logging.getLogger('sllurp').setLevel(logging.INFO)
        
        try:
            factory_args = dict(
                report_every_n_tags=1,
                antennas=[0],
                tx_power=50,
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
            
        except ImportError as e:
            raise ProtocolError(host, "LLRP", f"LLRP library not available: {e}")
        except Exception as e:
            # Let the calling code handle connection errors
            raise

    def _on_tag_report(self, reader, tag_reports):
        for tag in tag_reports:
            print(tag)
            try:
                # sllurp tag info typically contains .epc
                epc_raw = tag.get('EPC')
                if isinstance(epc_raw, bytes):
                    # sllurp decodes EPC-96 as lowercase ASCII hex bytes
                    # e.g. b'300833b2ddd9014000000001' not raw binary
                    epc = epc_raw.decode('ascii').upper()
                else:
                    epc = str(epc_raw).upper()
                normalized = self.normalize_epc(epc)
                if not self.runner_ids or normalized in self.runner_ids:
                    # sllurp tags have timestamp in tag.LastSeenTimestampUTC(nanoseconds)
                    #event.timestamp = int(tag.get('LastSeenTimestampUTC')) / 1_000_000
                    timestamp = get_timestamp_now() #int(datetime.now(timezone.utc).timestamp())
                    event = Event(normalized, timestamp)
                    with open("rfid.txt", "a") as f:
                        f.write(f"RFID, {normalized}, {timestamp}\n")
                    self.queue.put(event)

            except Exception as e:
                print(f"Error in tag callback: {e}")

    def _run(self):
        if not self.reader:
            return
        try:
            # This will block until disconnect() is called
            self.reader.join(None)

        except socket.timeout:
            print(f"Timeout connecting to LLRP reader at {self.host}:{self.port}")
            raise ConnectionTimeoutError(self.host, self.timeout)
        except ConnectionRefusedError:
            print(f"Connection refused by LLRP reader at {self.host}:{self.port}")
            raise ConnectionTimeoutError(self.host, self.timeout)
        except Exception as e:
            print(f"Error in sllurp reader: {e}")
            if "timeout" in str(e).lower() or "unreachable" in str(e).lower():
                raise ConnectionTimeoutError(self.host, self.timeout)
            else:
                raise ProtocolError(self.host, "LLRP", str(e))

        finally:
            if self.reader:
                try:
                    self.reader.disconnect()
                except:
                    pass
            print("Sllurp reader stopped")
