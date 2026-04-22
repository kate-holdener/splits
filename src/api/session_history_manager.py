from typing import Optional

from persistence.session_persistence import (
    delete_completed_session as _delete_completed_session,
    load_completed_session,
    list_completed_sessions as _list_completed_sessions,
)


class SessionHistoryManager:
    """Read-only access to completed sessions and email reporting. No live workout state."""

    def __init__(self):
        self._last_session_id: Optional[str] = None

    def list_completed_sessions(self):
        """Return metadata list of all archived workout sessions."""
        try:
            sessions = _list_completed_sessions()
            return {"ok": True, "sessions": sessions}
        except Exception as e:
            return {"ok": False, "msg": str(e), "sessions": []}

    def get_session_details(self, session_id: str):
        """Return full session details with per-athlete performance data (raw ms values)."""
        session_data = load_completed_session(session_id)
        if not session_data:
            return {"ok": False, "msg": "Session not found."}

        runners = session_data.get("runners", [])
        workout = next((r.get("workout") for r in runners if r.get("workout")), None)

        athletes = []
        max_intervals = 0

        for r in runners:
            completed = [
                iv for iv in r.get("session_intervals", [])
                if not iv.get("incomplete", True)
            ]
            if not completed:
                continue

            intervals_ms = [iv["end_time"] - iv["start_time"] for iv in completed]
            rests_ms = [
                completed[i + 1]["start_time"] - completed[i]["end_time"]
                for i in range(len(completed) - 1)
            ]
            total_ms = sum(intervals_ms)
            total_distance = sum(iv.get("distance", 0) for iv in completed)
            avg_pace_ms = int(total_ms / total_distance * 1600) if total_distance > 0 else 0

            max_intervals = max(max_intervals, len(intervals_ms))
            athletes.append({
                "name":            r.get("name", ""),
                "lname":           r.get("lname", ""),
                "lap_id":          r.get("lap_id", ""),
                "intervals_ms":    intervals_ms,
                "rests_ms":        rests_ms,
                "avg_pace_ms":     avg_pace_ms,
                "completed_count": len(completed),
            })

        from persistence.roster_persistence import find_athlete_by_id
        for athlete in athletes:
            result = find_athlete_by_id(athlete["lap_id"])
            if result:
                _, runner = result
                athlete["email"] = getattr(runner, "email", None) or ""
            else:
                athlete["email"] = ""

        return {
            "ok":            True,
            "session_id":    session_id,
            "started_at":    session_data.get("started_at"),
            "workout":       workout,
            "athletes":      athletes,
            "max_intervals": max_intervals,
        }

    def delete_completed_session(self, session_id: str):
        """Delete an archived workout session."""
        if not session_id or not session_id.strip():
            return {"ok": False, "msg": "Session ID is required."}
        success = _delete_completed_session(session_id.strip())
        if success:
            if self._last_session_id == session_id:
                self._last_session_id = None
            return {"ok": True, "msg": "Workout session deleted."}
        return {"ok": False, "msg": "Session not found or could not be deleted."}

    def send_reports(self, reports: list):
        """Send HTML performance reports via email. reports is [{name, email, html, lap_id}]."""
        import importlib.util, os
        email_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "email", "email_sender.py")
        )
        spec = importlib.util.spec_from_file_location("_email_sender", email_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        EmailSender     = mod.EmailSender
        SMTPConfigError = mod.SMTPConfigError

        try:
            sender = EmailSender()
        except SMTPConfigError as e:
            return {"ok": False, "msg": str(e)}
        except Exception as e:
            return {"ok": False, "msg": f"Email configuration error: {e}"}

        try:
            import playwright  # noqa: F401
        except ImportError:
            return {"ok": False, "msg": "Playwright is not installed. Run: pip install playwright && playwright install chromium"}

        sent, failed = [], []
        for report in reports:
            try:
                ok = sender.send_report(
                    to_email=report["email"],
                    runner_name=report["name"],
                    report_html_string=report["html"],
                )
                (sent if ok else failed).append(report["name"])
            except Exception as e:
                failed.append(f"{report['name']} ({e})")

        if failed:
            msg = f"Failed: {'; '.join(failed)}."
            if sent:
                msg += f" Sent: {', '.join(sent)}."
            return {"ok": False, "msg": msg}
        return {"ok": True, "msg": f"Sent {len(sent)} email{'s' if len(sent) != 1 else ''}."}
