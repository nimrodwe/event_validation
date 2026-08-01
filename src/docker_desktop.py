"""Start Docker Desktop when the engine is not running yet."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _docker_info_ok() -> bool:
    docker = shutil.which("docker")
    if docker is None:
        return False
    try:
        proc = subprocess.run(
            [docker, "info"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _windows_desktop_exe() -> Path | None:
    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Docker"
        / "Docker"
        / "Docker Desktop.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Docker"
        / "Docker"
        / "Docker Desktop.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Docker" / "Docker Desktop.exe",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _launch_desktop() -> None:
    if sys.platform == "win32":
        exe = _windows_desktop_exe()
        if exe is None:
            raise RuntimeError(
                "Docker Desktop is not installed (Docker Desktop.exe not found). "
                "Install it from https://www.docker.com/products/docker-desktop/"
            )
        subprocess.Popen(
            [str(exe)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        return

    if sys.platform == "darwin":
        app = Path("/Applications/Docker.app")
        if not app.exists():
            raise RuntimeError(
                "Docker Desktop is not installed at /Applications/Docker.app. "
                "Install it from https://www.docker.com/products/docker-desktop/"
            )
        subprocess.run(["open", "-a", "Docker"], check=False)
        return

    # Linux: try the docker service; may need sudo / rootless already running.
    if shutil.which("systemctl"):
        subprocess.run(
            ["systemctl", "start", "docker"],
            capture_output=True,
            check=False,
        )
        return

    raise RuntimeError(
        "Docker engine is not running and no Docker Desktop launcher was found."
    )


def ensure_running(timeout_sec: float = 120.0) -> None:
    """
    If `docker info` fails, start Docker Desktop (or the docker service) and wait.

    Raises RuntimeError when Docker CLI is missing or the engine never becomes ready.
    """
    if shutil.which("docker") is None:
        raise RuntimeError(
            "docker CLI not found on PATH. Install Docker Desktop and open a new terminal."
        )

    if _docker_info_ok():
        return

    print("Docker is not running — starting Docker Desktop…")
    _launch_desktop()

    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if _docker_info_ok():
            print("Docker is ready.")
            return
        time.sleep(2)

    raise RuntimeError(
        "Timed out waiting for Docker. Open Docker Desktop manually, wait until it is "
        "fully started, then retry."
    )
