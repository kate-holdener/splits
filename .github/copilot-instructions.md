# Copilot Instructions

## Project Overview

An interval training timer system that uses RFID and NFC readers to automatically track runners during interval training workouts. Runners carry two tags: an NFC tag (scanned at start) and an RFID tag (detected at the lap sensor). The system detects each runner's start and lap events and computes performance stats.

## Commands

All Python commands must be run with `PYTHONPATH` pointing to `src/`:

```bash
# Run all tests
PYTHONPATH=src pytest tests/

# Run a single test
PYTHONPATH=src pytest tests/entity/runner_test.py::TestRunner::test_finish_interval

# Run a single test file
PYTHONPATH=src pytest tests/parser/runner_parser_test.py

# Run the simulation (random lap times, single session)
cd src && python main.py ../data/runners.csv

# Run the file-driven simulation (roster + commands CSV)
cd src && python simulation.py <roster.csv> <commands.csv>

# Run the interactive CLI
cd src && python cli/cli.py

# Serve the MkDocs documentation
mkdocs serve
```

## Architecture

The codebase follows a clean/layered architecture. All source lives in `src/`, tests mirror that structure in `tests/`.

```
src/
  entity/        # Domain models: Runner, Workout, Interval, Performance, Event, RunnerState
  interactors/   # Business logic: SplitsTimer, stats_calculator
  controller/    # ManualStartController, CLI controller
  readers/       # Hardware drivers: ACR122U (NFC), Impinj REST, LLRP, SLLURP
  reader.py      # Base Reader Protocol (threading + queue interface)
  boundary/      # Observer Protocol definition
  view/          # Observer implementations (TimerView, PySide6 GUI views)
  parser/        # CSV runner data parser
  serializer/    # Runner serialization (dict, JSON)
  simulator/     # LapTimeController — simulates lap events for testing
  report/        # PDF report generation via reportlab
  utils/         # get_timestamp_now() — returns milliseconds since epoch UTC
  cli/           # Interactive CLI (cli.py)
  gui/           # pywebview-based GUI (HTML/CSS in gui/html/)
```

**Event flow:**
1. Hardware readers (`readers/`) detect tag scans and put `Event(id, timestamp)` objects into a `Queue`.
2. `SplitsTimer` (runs in a daemon thread) consumes from the start-event queue and lap-event queue.
3. `SplitsTimer` routes each event to the matching `Runner` via `runners_by_start_id` / `runners_by_lap_id` dicts.
4. `Runner` updates its state (`INACTIVE → RUNNING → RESTING`) and calls `notify_observers()`.
5. Observers (e.g., `TimerView`) react to state changes for display.

## Key Conventions

**Two tags per runner:** Each `Runner` has a `start_id` (NFC tag UID) and a `lap_id` (RFID EPC). The CSV file uses columns `First Name`, `Last Name`, `NFC TAG`, `RFID TAG`.

**Timestamps are milliseconds since epoch UTC.** Always use `utils.normalized_timestamp.get_timestamp_now()` — never call `time.time()` or `datetime.now()` directly in production code.

**`Runner` is the Observer pattern Subject.** Call `runner.add_observer(obj)` where `obj` implements the `Observer` Protocol (`boundary/observer.py`). Observers receive the full `Runner` instance on `update(runner)` and must inspect `runner.current_status`.

**Interval completion is lap-count driven.** `Workout.laps_per_interval` sets how many times a runner must cross the lap sensor to finish an interval. `Runner.add_lap()` includes a `TIME_DELTA = 1` (millisecond) debounce to drop duplicate detections.

**Protocols over abstract base classes.** `Reader` and `Observer` are `typing.Protocol` classes. Concrete implementations inherit from the protocol class (e.g., `class NFCReader(Reader)`) and call `super().__init__(queue)`.

**EPC normalization:** All RFID reader implementations strip leading zeros from EPCs using `normalize_epc(epc)` before matching against runner IDs.

**Test setup pattern:** Tests use `pytest.fixture(autouse=True)` named `setup` to initialize `self.*` attributes on the test class — not `setUp` (not unittest style).

**`runner_parser_test.py` uses a relative path** (`test_data/runners.csv`). Run it from `tests/parser/` or add a `conftest.py` with `rootdir` configuration to support running from the repo root.

## CSV Format

```csv
First Name, Last Name, NFC TAG, RFID TAG
Kate, Smith, 04AB1234, A1B2C3D4
```
