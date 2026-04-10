"""
Tests for athlete persistence functionality.
"""
import pytest
import os
import json
import tempfile
from unittest.mock import Mock, patch

# Import the modules to test
from persistence.athlete_persistence import (
    save_athletes_to_session,
    load_athletes_from_session,
    get_session_file_path,
    get_user_data_dir,
    session_exists,
    clear_session,
    migrate_legacy_session,
    SessionPersistenceError
)


class TestAthletePersistence:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # Create temp directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_file_path = os.path.join(self.temp_dir, "test_session.json")
        
        # Mock Runner objects for testing
        self.mock_runners = []
        for i in range(3):
            runner = Mock()
            runner.name = f"Runner{i}"
            runner.lname = f"Last{i}"
            runner.start_id = f"{i+1}"
            runner.lap_id = f"{i+10}"
            runner.intervals = []
            self.mock_runners.append(runner)
    
    def teardown_method(self):
        # Clean up temp files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_athletes_success(self):
        """Test successful saving of athletes."""
        with patch('serializer.json_serializer.runner_to_json') as mock_runner_to_json:
            # Mock the serialization function
            mock_runner_to_json.side_effect = lambda r: {
                "name": r.name,
                "lname": r.lname,
                "start_id": r.start_id,
                "lap_id": r.lap_id,
                "intervals": []
            }
            
            result = save_athletes_to_session(self.mock_runners, self.test_file_path)
            
            assert result is True
            assert os.path.exists(self.test_file_path)
            
            # Verify file content
            with open(self.test_file_path, 'r') as f:
                data = json.load(f)
            
            assert "session_metadata" in data
            assert "athletes" in data
            assert data["session_metadata"]["athlete_count"] == 3
            assert len(data["athletes"]) == 3
            
            # Check first athlete data
            athlete = data["athletes"][0]
            assert athlete["name"] == "Runner0"
            assert athlete["lname"] == "Last0"
            assert athlete["start_id"] == "1"
            assert athlete["lap_id"] == "10"
    
    def test_save_athletes_empty_list(self):
        """Test saving empty athlete list."""
        result = save_athletes_to_session([], self.test_file_path)
        
        assert result is True
        assert os.path.exists(self.test_file_path)
        
        with open(self.test_file_path, 'r') as f:
            data = json.load(f)
        
        assert data["session_metadata"]["athlete_count"] == 0
        assert len(data["athletes"]) == 0
    
    def test_save_athletes_file_permission_error(self):
        """Test handling of file permission errors."""
        # Use an invalid path that should cause permission error
        invalid_path = "/root/invalid_session.json"
        
        result = save_athletes_to_session(self.mock_runners, invalid_path)
        
        assert result is False
    
    def test_load_athletes_success(self):
        """Test successful loading of athletes."""
        # Create test session file
        session_data = {
            "session_metadata": {
                "saved_at": "2026-03-27T20:00:00",
                "athlete_count": 2
            },
            "athletes": [
                {
                    "name": "Alice",
                    "lname": "Smith",
                    "start_id": "1",
                    "lap_id": "10",
                    "intervals": []
                },
                {
                    "name": "Bob", 
                    "lname": "Jones",
                    "start_id": "2",
                    "lap_id": "20",
                    "intervals": []
                }
            ]
        }
        
        with open(self.test_file_path, 'w') as f:
            json.dump(session_data, f)
        
        with patch('serializer.json_serializer.runners_from_json') as mock_runners_from_json:
            # Mock athletes returned from JSON deserializer
            mock_athletes = [Mock(), Mock()]
            mock_athletes[0].name = "Alice"
            mock_athletes[1].name = "Bob"
            mock_runners_from_json.return_value = mock_athletes
            
            result = load_athletes_from_session(self.test_file_path)
            
            assert result is not None
            assert len(result) == 2
            assert result[0].name == "Alice"
            assert result[1].name == "Bob"
    
    def test_load_athletes_file_not_found(self):
        """Test loading when session file doesn't exist."""
        result = load_athletes_from_session("/nonexistent/path.json")
        
        assert result is None
    
    def test_load_athletes_invalid_json(self):
        """Test loading with corrupted JSON file."""
        # Write invalid JSON
        with open(self.test_file_path, 'w') as f:
            f.write("{ invalid json }")
        
        result = load_athletes_from_session(self.test_file_path)
        
        assert result is None
        # File should be backed up with .corrupt extension
        corrupt_files = [f for f in os.listdir(self.temp_dir) if 'corrupt' in f]
        assert len(corrupt_files) > 0
    
    def test_load_athletes_invalid_structure(self):
        """Test loading with invalid session structure."""
        # Write JSON with wrong structure
        invalid_data = {"wrong": "structure"}
        with open(self.test_file_path, 'w') as f:
            json.dump(invalid_data, f)
        
        result = load_athletes_from_session(self.test_file_path)
        
        assert result is None
    
    def test_get_session_file_path(self):
        """Test session file path generation."""
        path = get_session_file_path("../test_data")
        expected = os.path.join("../test_data", "athletes_session.json")
        
        assert path == expected
    
    def test_session_exists(self):
        """Test session existence check."""
        # Test with non-existent file
        assert session_exists(self.temp_dir) is False
        
        # Create session file
        session_file = os.path.join(self.temp_dir, "athletes_session.json")
        with open(session_file, 'w') as f:
            json.dump({"test": "data"}, f)
        
        assert session_exists(self.temp_dir) is True
    
    def test_clear_session(self):
        """Test session clearing."""
        # Create session file
        session_file = os.path.join(self.temp_dir, "athletes_session.json")
        with open(session_file, 'w') as f:
            json.dump({"test": "data"}, f)
        
        assert os.path.exists(session_file)
        
        result = clear_session(self.temp_dir)
        
        assert result is True
        assert not os.path.exists(session_file)
    
    def test_clear_session_no_file(self):
        """Test clearing session when no file exists."""
        result = clear_session(self.temp_dir)
        
        assert result is True  # Should succeed even if no file exists


class TestUserDataDir:
    """Tests for cross-platform user data directory detection."""

    def test_get_user_data_dir_returns_path(self):
        """get_user_data_dir() should return a Path object."""
        from pathlib import Path
        result = get_user_data_dir()
        assert isinstance(result, Path)

    def test_get_user_data_dir_ends_with_interval_timer(self):
        """User data directory name should be IntervalTimer."""
        result = get_user_data_dir()
        assert result.name == 'IntervalTimer'

    def test_get_user_data_dir_creates_directory(self):
        """get_user_data_dir() should create the directory if it doesn't exist."""
        import sys
        import tempfile
        from pathlib import Path
        from unittest.mock import patch as _patch

        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "fake_home"
            fake_home.mkdir()

            # Patch Path.home() and any env vars so the function always uses tmp
            if os.name == 'nt':
                with patch.dict(os.environ, {'APPDATA': tmp}):
                    result = get_user_data_dir()
            elif sys.platform == 'darwin':
                with _patch('pathlib.Path.home', return_value=fake_home):
                    result = get_user_data_dir()
            else:
                with patch.dict(os.environ, {'XDG_DATA_HOME': tmp}):
                    result = get_user_data_dir()

            assert result.exists()
            assert result.is_dir()
            assert result.name == 'IntervalTimer'

    def test_get_session_file_path_default_uses_user_data_dir(self):
        """Default get_session_file_path() should be inside the user data dir."""
        from pathlib import Path
        user_dir = get_user_data_dir()
        session_path = get_session_file_path()
        assert session_path == str(user_dir / "athletes_session.json")

    def test_get_session_file_path_explicit_dir(self):
        """Explicit data_dir should override user data dir."""
        path = get_session_file_path("../test_data")
        expected = os.path.join("../test_data", "athletes_session.json")
        assert path == expected

    def test_session_exists_no_args_uses_user_data_dir(self):
        """session_exists() with no args should check inside user data dir."""
        user_path = get_session_file_path()
        if os.path.exists(user_path):
            os.remove(user_path)
        assert session_exists() is False


class TestMigrateSession:
    """Tests for migrate_legacy_session()."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.legacy_dir = tempfile.mkdtemp()
        self.new_dir = tempfile.mkdtemp()
        yield
        import shutil
        shutil.rmtree(self.legacy_dir, ignore_errors=True)
        shutil.rmtree(self.new_dir, ignore_errors=True)

    def test_migrate_copies_file(self):
        """Migration should copy the session file to the new location."""
        legacy_file = os.path.join(self.legacy_dir, "athletes_session.json")
        new_file = os.path.join(self.new_dir, "athletes_session.json")

        with open(legacy_file, 'w') as f:
            json.dump({"athletes": []}, f)

        with patch('persistence.athlete_persistence.get_session_file_path', return_value=new_file):
            result = migrate_legacy_session(self.legacy_dir)

        assert result is True
        assert os.path.exists(new_file)
        # Original file should still exist
        assert os.path.exists(legacy_file)

    def test_migrate_skips_when_new_file_exists(self):
        """Migration should not overwrite an existing session at the new location."""
        legacy_file = os.path.join(self.legacy_dir, "athletes_session.json")
        new_file = os.path.join(self.new_dir, "athletes_session.json")

        with open(legacy_file, 'w') as f:
            json.dump({"athletes": [{"name": "old"}]}, f)
        with open(new_file, 'w') as f:
            json.dump({"athletes": [{"name": "new"}]}, f)

        with patch('persistence.athlete_persistence.get_session_file_path', return_value=new_file):
            result = migrate_legacy_session(self.legacy_dir)

        assert result is False
        # New file should still have its own content
        with open(new_file) as f:
            data = json.load(f)
        assert data["athletes"][0]["name"] == "new"

    def test_migrate_returns_false_when_no_legacy_file(self):
        """Migration returns False when there is nothing to migrate."""
        new_file = os.path.join(self.new_dir, "athletes_session.json")

        with patch('persistence.athlete_persistence.get_session_file_path', return_value=new_file):
            result = migrate_legacy_session(self.legacy_dir)

        assert result is False