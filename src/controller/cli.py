from parser.runner_parser import parse_runner_data
from entity.workout import Workout
from datetime import datetime, timezone
# CLI supports the following operations:
#   Load athletes from CSV.
#   Configure workout parameters: distance, rest time, lap count.
#   Add an athlete to a group (by NFC tag).
#   Trigger a group start (all athletes that have been added to the latest group start their run)
#   Send an 'RFID tag detected' event for a specific RIFD tag
#   Send an 'NFC tag scanned' for a specific NFC tag
#   Get (print) a list of currently resting athletes
#   Get (print) a list of currently running athletes
#   Terminate the workout

def cli():
    print("1. Load athletes from CSV.")
    print("2. Configure workout parameters: distance, rest time, lap count.")
    print("3. Add an athlete to a group (by NFC tag).")
    print("4. Trigger a group start (all athletes that have been added to the latest group start their run)")
    print("5. Send an 'RFID tag detected' event for a specific RIFD tag")
    print("6. Send an 'NFC tag scanned' for a specific NFC tag")
    print("7. Get (print) a list of currently resting athletes")
    print("8. Get (print) a list of currently running athletes")
    print("9. Terminate the workout")

    runners = []
    workout = None
    while True:
        try:
            command = input("> ").split()
            if not command:
                continue
            
            option = command[0]
            
            if option == "1":
                if len(command) > 1:
                    print(f"Loading athletes from {command[1]}")
                    runners = parse_runner_data(command[1])
            elif option == "2":
                if len(command) > 3:
                    print(f"Configuring workout: distance={command[1]}, rest time={command[2]}, lap count={command[3]}")
                    workout = Workout(int(datetime.now(timezone.utc).timestamp()))
                    workout.laps_per_interval = int(command[3])
                    workout.interval_distance = int(command[2])
            elif option == "3":
                if len(command) > 1:
                    print(f"Adding athlete to group: {command[1]}")
                    
            elif option == "4":
                print("Triggering group start")
            elif option == "5":
                if len(command) > 1:
                    print(f"RFID tag detected: {command[1]}")
            elif option == "6":
                 if len(command) > 1:
                    print(f"NFC tag scanned: {command[1]}")
            elif option == "7":
                print("Resting athletes")
            elif option == "8":
                print("Running athletes")
            elif option == "9":
                print("Terminating workout")
                break
        except EOFError:
            break
    
if __name__ == '__main__':
    cli()
