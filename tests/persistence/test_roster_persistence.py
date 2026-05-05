"""
Tests for roster persistence and RosterManager.update_athlete.
"""
import pytest
import shutil
import tempfile

from entity.runner import Runner
from persistence.roster_persistence import (
    create_roster,
    save_roster,
    load_roster,
    find_athlete_by_id,
)
from api.roster_manager import RosterManager


def _make_runner(name, lname, lap_id, start_id="", email=None):
    r = Runner()
    r.name = name
    r.lname = lname
    r.lap_id = lap_id
    r.start_id = start_id
    r.email = email
    return r


class TestUpdateAthlete:

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, monkeypatch):
        """Redirect all persistence to a temporary directory."""
        import persistence.roster_persistence as rp
        monkeypatch.setattr(rp, "get_user_data_dir", lambda: tmp_path)
        self.tmp_path = tmp_path
        self.roster = create_roster("Test Roster")
        runner = _make_runner("John", "Doe", "A1B2C3D4", "AABBCCDD", "john@test.com")
        save_roster(self.roster["id"], self.roster["name"], [runner])
        self.mgr = RosterManager()

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_update_name(self):
        result = self.mgr.update_athlete(
            "A1B2C3D4",
            {"first_name": "Jane", "last_name": "Smith", "nfc_tag": "AABBCCDD", "email": "john@test.com"},
        )
        assert result["ok"] is True
        athletes = load_roster(self.roster["id"], include_archived=True)
        assert athletes[0].name == "Jane"
        assert athletes[0].lname == "Smith"

    def test_update_nfc_tag(self):
        result = self.mgr.update_athlete(
            "A1B2C3D4",
            {"first_name": "John", "last_name": "Doe", "nfc_tag": "NEW00NFC", "email": "john@test.com"},
        )
        assert result["ok"] is True
        athletes = load_roster(self.roster["id"], include_archived=True)
        assert athletes[0].start_id == "NEW00NFC"

    def test_update_email(self):
        result = self.mgr.update_athlete(
            "A1B2C3D4",
            {"first_name": "John", "last_name": "Doe", "nfc_tag": "AABBCCDD", "email": "new@example.com"},
        )
        assert result["ok"] is True
        athletes = load_roster(self.roster["id"], include_archived=True)
        assert athletes[0].email == "new@example.com"

    def test_clear_email(self):
        result = self.mgr.update_athlete(
            "A1B2C3D4",
            {"first_name": "John", "last_name": "Doe", "nfc_tag": "AABBCCDD", "email": ""},
        )
        assert result["ok"] is True
        athletes = load_roster(self.roster["id"], include_archived=True)
        assert athletes[0].email is None

    def test_rfid_not_changed(self):
        """RFID tag (lap_id) must remain unchanged after an edit."""
        self.mgr.update_athlete(
            "A1B2C3D4",
            {"first_name": "Jane", "last_name": "Smith", "nfc_tag": "XX", "email": ""},
        )
        athletes = load_roster(self.roster["id"], include_archived=True)
        assert athletes[0].lap_id == "A1B2C3D4"

    def test_changes_persist_on_reload(self):
        """Changes must be visible when the roster is loaded fresh from disk."""
        self.mgr.update_athlete(
            "A1B2C3D4",
            {"first_name": "Persisted", "last_name": "Name", "nfc_tag": "N1", "email": "p@test.com"},
        )
        reloaded = load_roster(self.roster["id"], include_archived=True)
        assert reloaded[0].name == "Persisted"
        assert reloaded[0].lname == "Name"
        assert reloaded[0].start_id == "N1"
        assert reloaded[0].email == "p@test.com"

    # ------------------------------------------------------------------
    # In-memory sync
    # ------------------------------------------------------------------

    def test_updates_in_memory_athletes_when_roster_active(self):
        """When the edited athlete is in the active roster, self.athletes must reflect the change."""
        runner = _make_runner("John", "Doe", "A1B2C3D4", "AABBCCDD", "john@test.com")
        self.mgr.athletes = [runner]
        self.mgr.current_roster = {"id": self.roster["id"], "name": self.roster["name"]}

        self.mgr.update_athlete(
            "A1B2C3D4",
            {"first_name": "Jane", "last_name": "Smith", "nfc_tag": "NEW", "email": "j@test.com"},
        )

        assert self.mgr.athletes[0].name == "Jane"
        assert self.mgr.athletes[0].lname == "Smith"
        assert self.mgr.athletes[0].start_id == "NEW"
        assert self.mgr.athletes[0].email == "j@test.com"

    def test_does_not_touch_in_memory_athletes_for_different_roster(self):
        """Athletes in a different active roster must not be modified."""
        runner = _make_runner("John", "Doe", "A1B2C3D4", "AABBCCDD", "john@test.com")
        self.mgr.athletes = [runner]
        self.mgr.current_roster = {"id": "otherroster", "name": "Other"}

        self.mgr.update_athlete(
            "A1B2C3D4",
            {"first_name": "Jane", "last_name": "Smith", "nfc_tag": "NEW", "email": "j@test.com"},
        )

        # In-memory runner should still have original values
        assert self.mgr.athletes[0].name == "John"

    # ------------------------------------------------------------------
    # Error paths
    # ------------------------------------------------------------------

    def test_returns_error_for_unknown_athlete(self):
        result = self.mgr.update_athlete(
            "UNKNOWN000",
            {"first_name": "Jane", "last_name": "Smith", "nfc_tag": "", "email": ""},
        )
        assert result["ok"] is False
        assert "not found" in result["msg"].lower()

    def test_successful_update_returns_ok_with_message(self):
        result = self.mgr.update_athlete(
            "A1B2C3D4",
            {"first_name": "Alice", "last_name": "W", "nfc_tag": "", "email": ""},
        )
        assert result["ok"] is True
        assert "msg" in result
