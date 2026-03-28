"""
Tests for JSON serialization functionality.
"""
import pytest
from unittest.mock import Mock

from serializer.json_serializer import runner_to_json, runners_from_json


class TestJSONSerializer:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # Create mock runner for testing
        self.mock_runner = Mock()
        self.mock_runner.name = "Alice"
        self.mock_runner.lname = "Smith"
        self.mock_runner.start_id = "1"
        self.mock_runner.lap_id = "10"
        self.mock_runner.intervals = []
    
    def test_runner_to_json_complete(self):
        """Test serializing runner with all fields."""
        # Add mock interval
        mock_interval = Mock()
        mock_interval.start_time = 1000
        mock_interval.end_time = 2000
        mock_interval.distance = 400
        self.mock_runner.intervals = [mock_interval]
        
        result = runner_to_json(self.mock_runner)
        
        assert result["name"] == "Alice"
        assert result["lname"] == "Smith"
        assert result["start_id"] == "1"
        assert result["lap_id"] == "10"
        assert len(result["intervals"]) == 1
        assert result["intervals"][0]["start_time"] == 1000
        assert result["intervals"][0]["end_time"] == 2000
        assert result["intervals"][0]["distance"] == 400
    
    def test_runner_to_json_no_lname(self):
        """Test serializing runner without last name."""
        # Remove lname attribute to test getattr default
        delattr(self.mock_runner, 'lname')
        
        result = runner_to_json(self.mock_runner)
        
        assert result["name"] == "Alice"
        assert result["lname"] == ""  # Should default to empty string
        assert result["start_id"] == "1"
        assert result["lap_id"] == "10"
        assert result["intervals"] == []