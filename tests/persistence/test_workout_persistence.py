"""
Tests for workout persistence functionality.
"""
import pytest
import os
import json
import tempfile
import shutil

from persistence.workout_persistence import (
    get_workouts_dir,
    get_workouts_index_path,
    load_workouts_index,
    save_workouts_index,
    list_workouts,
    save_workout,
    get_workout_by_id,
    _make_workout_id,
    _make_workout_name,
)


class TestWorkoutPersistence:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.temp_dir = tempfile.mkdtemp()
        yield
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def test_make_workout_id(self):
        assert _make_workout_id(400, 4, 60) == "400m_4laps_60s"
        assert _make_workout_id(200, 1, 0) == "200m_1laps_0s"

    def test_make_workout_name(self):
        name = _make_workout_name(400, 4, 60)
        assert "400m" in name
        assert "4" in name
        assert "60" in name

    # ------------------------------------------------------------------
    # Directory / path helpers
    # ------------------------------------------------------------------

    def test_get_workouts_dir_creates_directory(self):
        d = get_workouts_dir(self.temp_dir)
        assert d.exists()
        assert d.is_dir()

    def test_get_workouts_index_path(self):
        path = get_workouts_index_path(self.temp_dir)
        assert path.endswith("index.json")
        assert "workouts" in path

    # ------------------------------------------------------------------
    # Index load / save
    # ------------------------------------------------------------------

    def test_load_workouts_index_missing_file(self):
        index = load_workouts_index(self.temp_dir)
        assert index == {"workouts": []}

    def test_save_and_load_workouts_index(self):
        data = {"workouts": [{"id": "x", "name": "X"}]}
        save_workouts_index(data, self.temp_dir)
        loaded = load_workouts_index(self.temp_dir)
        assert loaded == data

    def test_save_workouts_index_atomic(self):
        """The .tmp file should not persist after a successful write."""
        data = {"workouts": []}
        save_workouts_index(data, self.temp_dir)
        tmp = get_workouts_index_path(self.temp_dir) + ".tmp"
        assert not os.path.exists(tmp)

    # ------------------------------------------------------------------
    # save_workout
    # ------------------------------------------------------------------

    def test_save_workout_creates_entry(self):
        w = save_workout(400, 4, 60, self.temp_dir)
        assert w["distance"] == 400
        assert w["laps"] == 4
        assert w["rest"] == 60
        assert w["id"] == _make_workout_id(400, 4, 60)
        assert "created_at" in w

    def test_save_workout_no_duplicate(self):
        """Saving the same params twice should not create a second entry."""
        save_workout(400, 4, 60, self.temp_dir)
        save_workout(400, 4, 60, self.temp_dir)
        workouts = list_workouts(self.temp_dir)
        assert len(workouts) == 1

    def test_save_workout_returns_existing_on_duplicate(self):
        first = save_workout(400, 4, 60, self.temp_dir)
        second = save_workout(400, 4, 60, self.temp_dir)
        assert first["id"] == second["id"]
        assert first["created_at"] == second["created_at"]

    def test_save_workout_different_params_creates_separate_entries(self):
        save_workout(400, 4, 60, self.temp_dir)
        save_workout(800, 2, 90, self.temp_dir)
        workouts = list_workouts(self.temp_dir)
        assert len(workouts) == 2

    def test_save_workout_persists_to_file(self):
        save_workout(400, 4, 60, self.temp_dir)
        index = load_workouts_index(self.temp_dir)
        assert len(index["workouts"]) == 1
        assert index["workouts"][0]["distance"] == 400

    # ------------------------------------------------------------------
    # list_workouts
    # ------------------------------------------------------------------

    def test_list_workouts_empty(self):
        workouts = list_workouts(self.temp_dir)
        assert workouts == []

    def test_list_workouts_most_recent_first(self):
        save_workout(400, 4, 60, self.temp_dir)
        save_workout(800, 2, 90, self.temp_dir)
        workouts = list_workouts(self.temp_dir)
        assert len(workouts) == 2
        # Most recently added should be first
        assert workouts[0]["distance"] == 800
        assert workouts[1]["distance"] == 400

    # ------------------------------------------------------------------
    # get_workout_by_id
    # ------------------------------------------------------------------

    def test_get_workout_by_id_found(self):
        save_workout(400, 4, 60, self.temp_dir)
        workout_id = _make_workout_id(400, 4, 60)
        w = get_workout_by_id(workout_id, self.temp_dir)
        assert w is not None
        assert w["id"] == workout_id

    def test_get_workout_by_id_not_found(self):
        w = get_workout_by_id("nonexistent_id", self.temp_dir)
        assert w is None

    def test_get_workout_by_id_returns_correct_entry(self):
        save_workout(400, 4, 60, self.temp_dir)
        save_workout(800, 2, 90, self.temp_dir)
        w = get_workout_by_id(_make_workout_id(800, 2, 90), self.temp_dir)
        assert w["distance"] == 800
        assert w["laps"] == 2
        assert w["rest"] == 90
