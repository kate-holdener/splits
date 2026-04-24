import os
import webview

HTML_DIR = os.path.join(os.path.dirname(__file__), "html")


class PocApi:
    """Minimal shared js_api passed to both windows."""

    def __init__(self):
        self._counter = 0
        self.second_window = None
    def ping(self, source: str):
        """Called from either window; returns which window called it."""
        print(f"[PocApi] ping from: {source}")
        self.second_window.show()
        return {"ok": True, "msg": f"pong from Python (caller: {source})"}

    def increment(self):
        """Increment a shared counter so both windows can observe shared state."""
        self._counter += 1
        print(f"[PocApi] counter = {self._counter}")
        return {"ok": True, "counter": self._counter}

    def get_counter(self):
        return {"ok": True, "counter": self._counter}


def main():
    api = PocApi()

    webview.create_window(
        title="Screen 1",
        url=os.path.join(HTML_DIR, "poc1.html"),
        js_api=api,
        width=800,
        height=600,
    )

    api.second_window = webview.create_window(
        title="Screen 2",
        url=os.path.join(HTML_DIR, "poc2.html"),
        js_api=api,
        width=600,
        height=400,
        x=850,
        y=0,
        hidden=True
    )

    webview.start(debug=False)
    
if __name__ == "__main__":
    main()
