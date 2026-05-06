import json

from persistence.session_persistence import (
    delete_completed_session,
    list_completed_sessions,
    load_completed_session,
)


def test_delete_completed_session_removes_archived_file(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    session_path = sessions_dir / "session-123.json"
    session_path.write_text(json.dumps({
        "session_id": "session-123",
        "started_at": "2026-04-22T10:00:00",
        "saved_at": "2026-04-22T10:30:00",
        "runners": [],
    }), encoding="utf-8")

    assert load_completed_session("session-123", data_dir=tmp_path) is not None
    assert len(list_completed_sessions(data_dir=tmp_path)) == 1

    assert delete_completed_session("session-123", data_dir=tmp_path) is True
    assert load_completed_session("session-123", data_dir=tmp_path) is None
    assert list_completed_sessions(data_dir=tmp_path) == []


def test_delete_completed_session_returns_false_when_missing(tmp_path):
    assert delete_completed_session("missing-session", data_dir=tmp_path) is False
