from pyllrp import *
from pyllrp.LLRPConnector import LLRPConnector
import time

class RFIDReader:
    def __init__(self, host='169.254.1.1'):
        self.host = host
        self.connector = None
        
    def tag_callback(self, tag_data):
        """
        Callback function called when a tag is detected.
        Override this method or pass your own callback.
        
        Args:
            tag_data: Dictionary containing tag information
        """
        print(f"Tag detected: EPC={tag_data.get('epc')}, "
              f"Antenna={tag_data.get('antenna')}, "
              f"RSSI={tag_data.get('rssi')}")
    
    def handle_ro_access_report(self, connector, ro_access_report):
        """
        Handler for RO_ACCESS_REPORT messages (tag reads).
        This is called automatically by the connector when tags are detected.
        """
        # Extract tag data from the report
        for tag_report_data in ro_access_report.TagReportData:
            tag_data = {}
            
            # Get EPC (Electronic Product Code - the tag ID)
            if hasattr(tag_report_data, 'EPCData') and tag_report_data.EPCData:
                epc_data = tag_report_data.EPCData[0]
                if hasattr(epc_data, 'EPC'):
                    tag_data['epc'] = epc_data.EPC.hex()
            
            # Get antenna number
            if hasattr(tag_report_data, 'AntennaID') and tag_report_data.AntennaID:
                tag_data['antenna'] = tag_report_data.AntennaID[0].AntennaID
            
            # Get RSSI (signal strength)
            if hasattr(tag_report_data, 'PeakRSSI') and tag_report_data.PeakRSSI:
                tag_data['rssi'] = tag_report_data.PeakRSSI[0].PeakRSSI
            
            # Get timestamp
            if hasattr(tag_report_data, 'FirstSeenTimestampUTC') and tag_report_data.FirstSeenTimestampUTC:
                tag_data['timestamp'] = tag_report_data.FirstSeenTimestampUTC[0].Microseconds
            
            # Call the user's callback
            self.tag_callback(tag_data)
    
    def connect(self):
        """Connect to the RFID reader and configure it."""
        try:
            # Create connector
            self.connector = LLRPConnector()
            
            # Register the handler for tag reports
            self.connector.addHandler(
                'RO_ACCESS_REPORT',
                self.handle_ro_access_report
            )
            
            # Connect to reader
            print(f"Connecting to reader at {self.host}...")
            response = self.connector.connect(self.host)
            
            if not response:
                print("Failed to connect to reader")
                return False
            
            print("Connected successfully!")
            
            # Reset reader to default state
            #self.reset_reader()
            
            # Configure reader for tag detection
            #self.configure_reader()
            
            # Start inventory (tag reading)
            self.start_inventory()
        
            
            return True
            
        except Exception as e:
            print(f"Error connecting: {e}")
            return False
    
    def reset_reader(self):
        """Reset the reader to default configuration."""
        print("Resetting reader configuration...")
        
        # Delete all ROSpecs (Reader Operation Specifications)
        delete_msg = DELETE_ROSPEC(
            ROSpecID=0  # 0 means delete all
        )
        response = self.connector.transact(delete_msg)
        
        # Delete all AccessSpecs
        delete_access = DELETE_ACCESSSPEC(
            AccessSpecID=0  # 0 means delete all
        )
        response = self.connector.transact(delete_access)
    
    def configure_reader(self):
        """Configure the reader for continuous tag inventory."""
        print("Configuring reader for tag detection...")
        
        # Create ROSpec (Reader Operation Spec) for continuous reading
        rospec = ADD_ROSPEC(
            ROSpec=ROSpec(
                ROSpecID=1,
                Priority=0,
                CurrentState=ROSpecState.Disabled,
                ROBoundarySpec=ROBoundarySpec(
                    ROSpecStartTrigger=ROSpecStartTrigger(
                        ROSpecStartTriggerType=ROSpecStartTriggerType.Immediate
                    ),
                    ROSpecStopTrigger=ROSpecStopTrigger(
                        ROSpecStopTriggerType=ROSpecStopTriggerType.Null,
                        DurationTriggerValue=0
                    )
                ),
                AISpec=[
                    AISpec(
                        AntennaIDs=[0],  # 0 means all antennas
                        AISpecStopTrigger=AISpecStopTrigger(
                            AISpecStopTriggerType=AISpecStopTriggerType.Null,
                            DurationTrigger=0
                        ),
                        InventoryParameterSpec=[
                            InventoryParameterSpec(
                                InventoryParameterSpecID=1,
                                ProtocolID=AirProtocols.EPCGlobalClass1Gen2
                            )
                        ]
                    )
                ],
                ROReportSpec=ROReportSpec(
                    ROReportTrigger=ROReportTriggerType.Upon_N_Tags_Or_End_Of_AISpec,
                    N=1,  # Report after every tag
                    TagReportContentSelector=TagReportContentSelector(
                        EnableROSpecID=False,
                        EnableSpecIndex=False,
                        EnableInventoryParameterSpecID=False,
                        EnableAntennaID=True,
                        EnableChannelIndex=False,
                        EnablePeakRSSI=True,
                        EnableFirstSeenTimestamp=True,
                        EnableLastSeenTimestamp=False,
                        EnableTagSeenCount=False,
                        EnableAccessSpecID=False
                    )
                )
            )
        )
        
        response = self.connector.transact(rospec)
        print("ROSpec configured")
        
        # Enable the ROSpec
        enable_msg = ENABLE_ROSPEC(ROSpecID=1)
        response = self.connector.transact(enable_msg)
        print("ROSpec enabled")
    
    def start_inventory(self):
        """Start the tag inventory process."""
        print("Starting tag inventory...")
        start_msg = START_ROSPEC(ROSpecID=1)
        response = self.connector.transact(start_msg)
        print("Tag inventory started - waiting for tags...")
    
    def stop_inventory(self):
        """Stop the tag inventory process."""
        if self.connector:
            print("Stopping tag inventory...")
            stop_msg = STOP_ROSPEC(ROSpecID=1)
            self.connector.transact(stop_msg)
    
    def disconnect(self):
        """Disconnect from the reader."""
        if self.connector:
            self.stop_inventory()
            print("Disconnecting...")
            self.connector.disconnect()
            print("Disconnected")


# Example usage
if __name__ == "__main__":
    # Create reader instance
    reader = RFIDReader()  # Change to your reader's IP
    
    # Optional: Define a custom callback
    def my_tag_callback(tag_data):
        print(f">>> Custom callback - Tag found!")
        print(f"    EPC: {tag_data.get('epc', 'N/A')}")
        print(f"    Antenna: {tag_data.get('antenna', 'N/A')}")
        print(f"    RSSI: {tag_data.get('rssi', 'N/A')} dBm")
        print(f"    Timestamp: {tag_data.get('timestamp', 'N/A')}")
        print()
    
    # Assign custom callback (optional)
    reader.tag_callback = my_tag_callback
    
    # Connect to reader
    if reader.connect():
        try:
            # Keep running and detecting tags
            print("\nReading tags... Press Ctrl+C to stop\n")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            reader.disconnect()
    else:
        print("Failed to connect to reader")