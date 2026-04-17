"""
Interval Training CLI

Workflow:
- Options 1 (load athletes) and 2 (configure workout) can be done in any order
- Both 1 and 2 must be completed before options 3 and 4 become available
- Options 3 (RFID) and 4 (NFC) must both succeed for remaining options
- Option 11 (generate reports) is always available
"""

import argparse
from enum import Enum, auto
from typing import Optional, List, Set
from datetime import datetime
from queue import Queue
from parser.runner_parser import parse_runner_data
from entity.workout import Workout
from entity.runner import Runner
from entity.RunnerState import RunnerState
from controller.start_controller import ManualStartController
from interactors.interval_timer import SplitsTimer
from interactors.stats_calculator import calculate_performance
from readers.acr122u_nfc import NFCReader
from readers.sllurp_reader import LLRPReader
from reader import Reader
from discovery.utils import discover_scanner
from discovery.exceptions import ConnectionTimeoutError, ProtocolError, NoScannersFoundError


class AppState(Enum):
    """Application state machine states."""
    INITIAL = auto()
    ATHLETES_LOADED = auto()
    WORKOUT_CONFIGURED = auto()
    SETUP_COMPLETE = auto()  # Both 1 and 2 done
    SCANNERS_CONNECTED = auto()  # 3 and 4 done successfully
    SCANNER_FAILED = auto()  # 3 or 4 failed

class RunnerObserver:
    def __init__(self):
        self.running: list[Runner]=[]
        self.resting: list[Runner]=[]

    def update(self, runner: Runner):
        print(f"update: runner is {runner.get_status()}")
        if runner.get_status() == RunnerState.RUNNING:
            if not runner in self.running:
                print("adding to running list")
                self.running.append(runner)
            if runner in self.resting:
                self.resting.remove(runner)
        elif runner.get_status() == RunnerState.RESTING:
            if runner in self.running:
                self.running.remove(runner)
            if not runner in self.resting:
                self.resting.append(runner)
        else:
            if runner in self.running:
                self.running.remove(runner)
            if runner in self.resting:
                self.resting.remove(runner)

class IntervalTrainingCLI:
    def __init__(self):
        self.athletes: List[Runner] = []
        self.csv_file: Optional[str] = None
        self.workout: Optional[Workout] = None
        self.rfid_connected: bool = False
        self.nfc_connected: bool = False
        self.group_start_athletes: Set[Runner] = set()
        self.running_athletes: Set[Runner] = set()
        self.resting_athletes: Set[Runner] = set()
        self.runner_state_obersver = RunnerObserver()
        self.workout_active: bool = False
        self.start_event_q = Queue()
        self.lap_event_q = Queue()
        self.manual_start_controller = ManualStartController(self.start_event_q)
        self.nfc_scanner: Optional[Reader] = None
        self.rfid_scanner: Optional[Reader] = None
        self.timer = None
        
        # State tracking
        self.athletes_loaded: bool = False
        self.workout_configured: bool = False
        self.scanners_connected: bool = False
        self.rfid_scanner_failed: bool = False
        self.nfc_scanner_failed: bool = False

    def display_menu(self) -> None:
        """Display the menu with available options based on current state."""
        print("\n" + "=" * 50)
        print("       INTERVAL TRAINING CLI")
        print("=" * 50)
        
        # Options 1 and 2 - available until both complete
        if not self.athletes_loaded:
            print("  1. Load athletes from CSV")
        else:
            print("  1. Load athletes from CSV [DONE]")
            
        if not self.workout_configured:
            print("  2. Configure workout")
        else:
            print("  2. Configure workout [DONE]")
        
        # Options 3 and 4 - available after 1 and 2 complete
        setup_complete = self.athletes_loaded and self.workout_configured
        
        if setup_complete:
            if not self.rfid_connected and not self.rfid_scanner_failed:
                print("  3. Connect to RFID scanner")
            elif self.rfid_scanner_failed:
                print("  3. Connect to RFID scanner [FAILED]")
            else:
                print("  3. Connect to RFID scanner [CONNECTED]")
                
            if not self.nfc_connected and not self.nfc_scanner_failed:
                print("  4. Connect to NFC scanner")
            elif self.nfc_scanner_failed:
                print("  4. Connect to NFC scanner [FAILED]")
            else:
                print("  4. Connect to NFC scanner [CONNECTED]")
        elif not setup_complete:
            print("  3. Connect to RFID scanner [Requires: 1, 2]")
            print("  4. Connect to NFC scanner [Requires: 1, 2]")
        else:
            if not self.rfid_connected:
                print("  3. Connect to RFID scanner [FAILED]")
            if not self.nfc_connected:
                print("  4. Connect to NFC scanner [FAILED]")
        
        # Options 5-11 - available after all scanners connected
        all_ready = setup_complete and self.rfid_connected and self.nfc_connected
        
        # Option 5 - always available
        print("  5. List all athletes")
        
        if all_ready:
            print("  6. Add an athlete to group start")
            print("  7. Start all athletes in group start")
            print("  8. List running athletes")
            print("  9. List resting athletes")
            print(" 10. View performance of all athletes")
            print(" 11. Finish workout")
        else:
            status = "[Requires: 1, 2, 3, 4]"
            if self.nfc_scanner_failed or self.rfid_scanner_failed:
                status = "[BLOCKED: Scanner connection failed]"
            print(f"  6. Add an athlete to group start {status}")
            print(f"  7. Start all athletes in group start {status}")
            print(f"  8. List running athletes {status}")
            print(f"  9. List resting athletes {status}")
            print(f" 10. View performance of all athletes {status}")
            print(f" 11. Finish workout {status}")
        
        # Option 12 - always available
        print(" 12. Generate workout reports")
        
        print("  0. Exit")
        print("=" * 50)

    def option_1_load_athletes(self) -> None:
        """Load athletes from CSV file."""
        csv_path = input("Enter CSV file path: ").strip()
        if not csv_path:
            print("[ERROR] CSV file path is required.")
            return
        
        # Dummy implementation
        print(f"[DUMMY] Loading athletes from: {csv_path}")
        self.csv_file = csv_path
        try:
            self.athletes = parse_runner_data(self.csv_file)
            self.athletes_loaded = True
            print(f"[SUCCESS] Loaded {len(self.athletes)} athletes.")

            # get notifications about runner state changes via RunnerObserver
            for a in self.athletes:
                a.add_observer(self.runner_state_obersver)
            self.timer = SplitsTimer(self.start_event_q, self.lap_event_q, self.athletes)
            self.timer.start()

            if self.workout:
                for a in self.athletes:
                    a.add_workout(self.workout)

        except Exception:
            print(f"could not load athletes from {self.csv_file}")

    def option_2_configure_workout(self) -> None:
        """Configure workout parameters."""
        try:
            distance = input("Enter interval distance (meters): ").strip()
            laps = input("Enter number of laps per interval: ").strip()
            self.workout = Workout(datetime.now())
            self.workout.configure(int(distance), int(laps))
            
            # Dummy implementation
            print(f"Configuring workout:")
            print(f"  - Interval distance: {self.workout.interval_distance} meters")
            print(f"  - Laps per interval: {self.workout.laps_per_interval}")
            self.workout_configured = True
            if self.athletes:
                for a in self.athletes:
                    a.add_workout(self.workout)

            print("[SUCCESS] Workout configured.")
        except ValueError:
            print("[ERROR] Invalid input. Please enter numeric values.")

    def option_3_connect_rfid(self) -> None:
        """Connect to RFID scanner with auto-discovery."""
        if not (self.athletes_loaded and self.workout_configured):
            print("[ERROR] Must complete options 1 and 2 first.")
            return
        
        print("[] Discovering RFID scanners...")
        
        try:
            # Try to discover RFID scanner (both LLRP and REST protocols)
            scanner_info = discover_scanner(protocol='both', interactive=True, return_full_info=True)
            
            if not scanner_info:
                print("[FAILED] No RFID scanner address provided.")
                self.rfid_scanner_failed = True
                return
                
            address = scanner_info['address']
            protocol = scanner_info['protocol']
            port = scanner_info.get('port', 5084)
            
            print(f"[] Attempting to connect to {protocol.upper()} RFID scanner at {address}...")
            
            # Filter by runner lap IDs
            runner_ids = [r.lap_id for r in self.athletes]
            
            # Create appropriate reader based on detected protocol
            if protocol == 'llrp':
                self.rfid_scanner = LLRPReader(self.lap_event_q, address)
                protocol_name = f"LLRP (port {port})"
            elif protocol == 'rest':
                from readers.impinj_rest_reader import ImpinjRestReader
                self.rfid_scanner = ImpinjRestReader(self.lap_event_q, address)
                protocol_name = f"REST API (port {port})"
            else:
                print(f"[FAILED] Unknown protocol '{protocol}' for scanner at {address}")
                self.rfid_scanner_failed = True
                return
                
            self.rfid_scanner.filter_by_id(runner_ids)
            self.rfid_scanner.start()
            
            self.rfid_connected = True
            self.rfid_scanner_failed = False
            print(f"[SUCCESS] RFID scanner connected at {address} using {protocol_name}.")
            
        except ConnectionTimeoutError as e:
            print(f"[FAILED] Connection timeout: {e}")
            self.rfid_scanner_failed = True
            print("[WARNING] Further options are now blocked.")
            
        except ProtocolError as e:
            print(f"[FAILED] Protocol error: {e}")
            self.rfid_scanner_failed = True
            print("[WARNING] Further options are now blocked.")
            
        except NoScannersFoundError:
            print("[FAILED] No RFID scanners found on network.")
            self.rfid_scanner_failed = True
            print("[WARNING] Further options are now blocked.")
            
        except Exception as e:
            print(f"[FAILED] Unexpected error: {e}")
            self.rfid_scanner_failed = True
            print("[WARNING] Further options are now blocked.")

    def option_4_connect_nfc(self) -> None:
        """Connect to NFC scanner."""
        if not (self.athletes_loaded and self.workout_configured):
            print("[ERROR] Must complete options 1 and 2 first.")
            return
        success = False
        try:
            self.nfc_scanner = NFCReader(self.start_event_q)
            self.nfc_scanner.start()
            success = True
        except Exception as e:
            print(f"failed to start NFC scanner {e}")
            success = False
        # Dummy implementation
        print("[] Attempting to connect to NFC scanner...")
        
        if success:
            self.nfc_connected = True
            self.nfc_scanner_failed = False
            print("[SUCCESS] NFC scanner connected.")
        else:
            self.nfc_scanner_failed = True
            print("[FAILED] Could not connect to NFC scanner.")
            print("[WARNING] Further options are now blocked.")

    def _check_full_setup(self) -> bool:
        """Check if full setup is complete (1, 2, 3, 4 all successful)."""
        if self.rfid_scanner_failed or self.nfc_scanner_failed:
            print("[ERROR] Cannot proceed: Scanner connection failed.")
            return False
        if not (self.athletes_loaded and self.workout_configured 
                and self.rfid_connected and self.nfc_connected):
            print("[ERROR] Must complete options 1, 2, 3, and 4 first.")
            return False
        return True

    def option_5_list_all_athletes(self) -> None:
        """List all athletes (available anytime)."""
        # Dummy implementation
        print("[DUMMY] All athletes:")
        if self.athletes:
            for athlete in self.athletes:
                print(f"  - {athlete.to_dict()}")
        else:
            print("  (none - load athletes first)")

    def option_6_add_to_group_start(self) -> None:
        """Add an athlete to group start."""
        if not self._check_full_setup():
            return
        
        tag_id = input("Enter athlete tag ID: ").strip()
        if not tag_id:
            print("[ERROR] Tag ID is required.")
            return
        
        # Dummy implementation
        print(f"[DUMMY] Adding athlete with tag ID: {tag_id}")
        if  self.add_to_group(tag_id):
            print(f"[SUCCESS] Athlete {tag_id} added to group start.")
            print(f"  Current group: {self.group_start_athletes}")
        else:
            print(f"Failed to add athlete with tag {tag_id} to group start")

    def option_7_start_group(self) -> None:
        """Start all athletes in group start."""
        if not self._check_full_setup():
            return
        
        # Dummy implementation
        if not self.group_start_athletes:
            print("[WARNING] No athletes in group start.")
            return
        ids = [r.start_id for r in self.group_start_athletes]
        self.manual_start_controller.start(ids)

        print(f"Starting all athletes in group start...{ids}")
        self.group_start_athletes.clear()
        self.workout_active = True
        print(f"[SUCCESS] Started athletes: {ids}")

    def option_8_list_running(self) -> None:
        """List running athletes."""
        if not self._check_full_setup():
            return
        
        # Dummy implementation
        print("[] Running athletes:")
        for runner in self.runner_state_obersver.running:
            print(f"  - {runner.to_dict()}")

    def option_9_list_resting(self) -> None:
        """List resting athletes."""
        if not self._check_full_setup():
            return
        
        # Dummy implementation
        print("[] Resting athletes:")
        for runner in self.runner_state_obersver.resting:
            print(f"  - {runner.to_dict()}")

    def option_10_view_performance(self) -> None:
        """View performance of all athletes."""
        if not self._check_full_setup():
            return
        stats = []
        for r in self.athletes:
            p = calculate_performance(r)
            if p:
                stats.append((r, p))
        for stat in stats:
            print(f"{stat[0].to_dict()} - {stat[1]}")

    def option_11_finish_workout(self) -> None:
        """Finish the workout."""
        if not self._check_full_setup():
            return
        
        # Dummy implementation
        print("[DUMMY] Finishing workout...")
        self.running_athletes.clear()
        self.resting_athletes.clear()
        self.workout_active = False
        print("[SUCCESS] Workout finished.")

    def option_12_generate_reports(self) -> None:
        """Generate workout reports (available anytime)."""
        directory = input("Enter directory for workout data: ").strip()
        if not directory:
            print("[ERROR] Directory path is required.")
            return
        
        # Dummy implementation
        print(f"[DUMMY] Generating workout reports from: {directory}")
        print("  - athlete_summary.pdf")
        print("  - lap_times.csv")
        print("  - workout_overview.html")
        print("[SUCCESS] Reports generated.")

    def run(self) -> None:
        """Main CLI loop."""
        print("\nWelcome to Interval Training CLI!")
        
        while True:
            self.display_menu()
            
            try:
                choice = input("\nSelect option: ").strip()
                
                if choice == "0":
                    if self.timer:
                        self.timer.stop()
                    print("Goodbye!")
                    break
                elif choice == "1":
                    self.option_1_load_athletes()
                elif choice == "2":
                    self.option_2_configure_workout()
                elif choice == "3":
                    self.option_3_connect_rfid()
                elif choice == "4":
                    self.option_4_connect_nfc()
                elif choice == "5":
                    self.option_5_list_all_athletes()
                elif choice == "6":
                    self.option_6_add_to_group_start()
                elif choice == "7":
                    self.option_7_start_group()
                elif choice == "8":
                    self.option_8_list_running()
                elif choice == "9":
                    self.option_9_list_resting()
                elif choice == "10":
                    self.option_10_view_performance()
                elif choice == "11":
                    self.option_11_finish_workout()
                elif choice == "12":
                    self.option_12_generate_reports()
                else:
                    print("[ERROR] Invalid option. Please try again.")
                    
            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except EOFError:
                print("\n\nGoodbye!")
                break
    def add_to_group(self, tag_id: str)->bool:
        for athlete in self.athletes:
            if athlete.start_id == tag_id:
                self.group_start_athletes.add(athlete)
                return True
        return False

def main():
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Interval Training CLI Application"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Interval Training CLI v1.0.0"
    )
    
    args = parser.parse_args()
    
    cli = IntervalTrainingCLI()
    cli.run()


if __name__ == "__main__":
    main()
