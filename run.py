"""
One-click launcher for VibeSplit.
Starts FastAPI backend server, serves the modern Gen-Z SPA, and launches browser.
"""
import sys
import os
import subprocess
import time
import webbrowser

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    print("=" * 60)
    print("⚡ Launching VibeSplit - AI-Powered Gen-Z Expense & Debt Settler")
    print("=" * 60)

    # Set working directory to project root
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_dir)
    os.chdir(project_dir)

    print("🚀 Starting FastAPI backend on http://127.0.0.1:8000 ...")

    # Launch browser after a brief delay
    def open_browser():
        time.sleep(1.5)
        print("🌐 Opening http://127.0.0.1:8000 in your browser...")
        webbrowser.open("http://127.0.0.1:8000")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    main()
