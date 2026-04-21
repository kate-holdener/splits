import os
import webview

HTML_DIR = os.path.join(os.path.dirname(__file__), "html")


def main():
    win1 = webview.create_window(
        title="Screen 1",
        url=os.path.join(HTML_DIR, "poc1.html"),
        width=800,
        height=600,
    )

    win2 = webview.create_window(
        title="Screen 2",
        url=os.path.join(HTML_DIR, "poc2.html"),
        width=600,
        height=400,
        x=850,
        y=0,
    )

    webview.start(debug=False)


if __name__ == "__main__":
    main()
