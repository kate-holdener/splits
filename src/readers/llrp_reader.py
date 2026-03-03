from reader import Reader
from entity.event import Event
import pyllrp as llrp
from pyllrp.LLRPConnector import LLRPConnector


import time

# Alternative implementation using callback pattern
class LLRPReader(Reader):
    """LLRP reader using callback pattern"""
    
    def __init__(self, queue, scanner_address, runner_ids, port=5084):
        super().__init__(queue)
        self.scanner_address = scanner_address
        self.port = port
        self.runner_ids = runner_ids
        self.client = None
    
    @staticmethod
    def normalize_epc(epc):
        """Remove leading zeros from EPC, but keep it as a string"""
        return epc.lstrip('0') or '0'
    
    def _tag_callback(self, tag_data):
        """Callback function for tag reports"""
        try:
            epc = tag_data.get('EPC', '')
            if isinstance(epc, bytes):
                epc = epc.hex().upper()
            else:
                epc = str(epc).upper()
            
            normalized_epc = self.normalize_epc(epc)
            
            if normalized_epc in self.runner_ids:
                event = Event()
                event.id = normalized_epc
                if 'LastSeenTimestampUTC' in tag_data:
                    event.timestamp = int(tag_data['LastSeenTimestampUTC'] / 1000000)
                else:
                    event.timestamp = int(time.time())
                self.queue.put(event)
        except Exception as e:
            print(f"Error in tag callback: {e}")

    def _create_rospec(self):
        rospec = llrp.ROSpec()
        rospec.ROSpecID = 1
        rospec.Priority = 0
        rospec.CurrentState = llrp.ROSpecState.Disabled

        # ROBoundarySpec
        rospec.ROBoundarySpec = llrp.ROBoundarySpec(
            llrp.ROSpecStartTrigger(
                llrp.ROSpecStartTriggerType.Immediate
            ),
            llrp.ROSpecStopTrigger(
                llrp.ROSpecStopTriggerType.Null
            )
        )

        # AISpec
        aispec = llrp.AISpec()
        aispec.AntennaIDs.Add(1)  # All antennas
        aispec.AISpecStopTrigger = llrp.AISpecStopTrigger(
            llrp.AISpecStopTriggerType.Null
        )

        # InventoryParameterSpec (Gen2)
        inv = llrp.InventoryParameterSpec()
        inv.InventoryParameterSpecID = 1
        inv.ProtocolID = llrp.AirProtocols.EPCGlobalClass1Gen2

        aispec.InventoryParameterSpecList.append(inv)
        rospec.SpecParameterList.append(aispec)

        # ROReportSpec
        rospec.SpecParameterList.append(
            llrp.ROReportSpec(
                llrp.ROReportTriggerType.Upon_N_Tags_Or_End_Of_ROSpec,
                1
            )
        )

        return rospec

    def _run(self):
        """Main reader loop with callback"""
        try:
            self.client = LLRPConnector(self.scanner_address, self.port)
            self.client.connect()
            
            # Set up callback
            self.client.add_tag_report_callback(self._tag_callback)
            
            # Initialize reader
            self.client.delete_all_rospecs()
            rospec = self._create_rospec()
            self.client.add_rospec(rospec)
            self.client.enable_rospec(1)
            self.client.start_rospec(1)
            self.client.set_antenna_config(antenna_id=1,
                transmit_power=30.0  # dBm – choose a value allowed by your region
            )

            print("Reader started with callback")
            
            # Keep running while callback handles tags
            while self.running:
                time.sleep(0.1)
        
        except Exception as e:
            print(f"Error in callback reader: {e}")
        
        finally:
            if self.client:
                try:
                    self.client.stop_rospec(1)
                    self.client.disconnect()
                except:
                    pass
            print("Callback reader stopped")