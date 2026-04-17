"""
Tests for the cross-platform user data directory helper.
"""
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from persistence.user_data_dir import get_user_data_dir


class TestUserDataDir:
    """Tests for cross-platform user data directory detection."""

    def test_get_user_data_dir_returns_path(self):
        """get_user_data_dir() should return a Path object."""
        result = get_user_data_dir()
        assert isinstance(result, Path)

    def test_get_user_data_dir_ends_with_splits(self):
        """User data directory name should be Splits."""
        result = get_user_data_dir()
        assert result.name == 'Splits'

    def test_get_user_data_dir_creates_directory(self):
        """get_user_data_dir() should create the directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "fake_home"
            fake_home.mkdir()

            if os.name == 'nt':
                with patch.dict(os.environ, {'APPDATA': tmp}):
                    result = get_user_data_dir()
            elif sys.platform == 'darwin':
                with patch('pathlib.Path.home', return_value=fake_home):
                    result = get_user_data_dir()
            else:
                with patch.dict(os.environ, {'XDG_DATA_HOME': tmp}):
                    result = get_user_data_dir()

            assert result.exists()
            assert result.is_dir()
            assert result.name == 'Splits'
