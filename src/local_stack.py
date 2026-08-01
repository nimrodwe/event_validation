"""Local receiver + dashboard that can outlive pytest."""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

from src.config import OUT, ROOT
from src.receiver import connect as connect_receiver
from src.report import Report


class LocalHost:
    """Handle tests use to POST events — points at the detached stack."""

    RECEIVER_PORT = 8765
    DASHBOARD_PORT = 8080
    DASHBOARD_URL = "http://127.0.0.1:" + str(DASHBOARD_PORT)
    RECEIVER_URL = "http://127.0.0.1:" + str(RECEIVER_PORT) + "/v1/events"

    def __init__(self):
        self.port = self.RECEIVER_PORT
        self.url = self.RECEIVER_URL
        self.out = OUT / "received"


class LocalStack:
    """Starts and checks the detached receiver + dashboard process."""

    def dashboard_up(self):
        try:
            urllib.request.urlopen(LocalHost.DASHBOARD_URL + "/api/received", timeout=0.5)
            return True
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def browser_tab_active(self):
        """True if an open dashboard tab has checked in recently."""
        try:
            with urllib.request.urlopen(
                LocalHost.DASHBOARD_URL + "/api/presence", timeout=0.5
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return bool(data.get("active"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
            return False

    def stop_existing(self):
        """Stop leftover dashboard on 8080 so git pull + relaunch loads new code."""
        if not self.dashboard_up():
            return
        print("Stopping previous dashboard on " + LocalHost.DASHBOARD_URL + " …")
        try:
            req = urllib.request.Request(
                LocalHost.DASHBOARD_URL + "/api/shutdown",
                data=b"",
                method="POST",
            )
            urllib.request.urlopen(req, timeout=3)
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        for _ in range(50):
            if not self.dashboard_up():
                print("Previous dashboard stopped.")
                return
            time.sleep(0.1)
        print(
            "Warning: old dashboard may still own port 8080. "
            "Click Shut down, or: lsof -ti tcp:8080 | xargs kill -9"
        )

    def run(self, open_browser=True):
        """Run receiver + dashboard in this process until Shut down is clicked."""
        self.stop_existing()
        receiver = connect_receiver(OUT / "received", port=LocalHost.RECEIVER_PORT)
        report = Report()
        report.add_shutdown_hook(receiver.disconnect)
        try:
            report.serve(
                port=LocalHost.DASHBOARD_PORT,
                open_browser=open_browser,
                blocking=True,
            )
        finally:
            receiver.disconnect()

    def ensure_running(self, open_browser=True):
        """
        Make sure the local stack is up in a detached process with current code.

        Always restarts an existing dashboard so git pull changes are picked up.
        """
        self.stop_existing()

        OUT.mkdir(parents=True, exist_ok=True)
        log_path = OUT / "stack.log"
        log_file = open(log_path, "w", encoding="utf-8")
        popen_kwargs = {
            "args": [sys.executable, str(ROOT / "run.py"), "stack", "--no-open"],
            "cwd": str(ROOT),
            "stdin": subprocess.DEVNULL,
            "stdout": log_file,
            "stderr": subprocess.STDOUT,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            popen_kwargs["start_new_session"] = True

        print("Starting local stack (receiver + dashboard)…")
        subprocess.Popen(**popen_kwargs)
        log_file.close()

        for _ in range(50):
            if self.dashboard_up():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("Local stack did not start on " + LocalHost.DASHBOARD_URL)

        if open_browser:
            print("Opening dashboard " + LocalHost.DASHBOARD_URL)
            webbrowser.open(LocalHost.DASHBOARD_URL)
        return LocalHost()
