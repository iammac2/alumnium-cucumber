"""Local HTTP server launcher for Alumnium reports."""

from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

_PID_FILE = ".http_server.pid"


def launch(output_dir: Path, html_filename: str) -> str:
    """Start a local HTTP server, open the report in the browser, and return the URL.

    The server is launched as a detached background process so behave exits
    cleanly without blocking. A PID file is written so the previous server is
    killed on the next run, preventing orphaned processes from accumulating.
    All errors are caught — report files are always written before this is called.
    Returns the URL at which the report is served, or "" on failure.
    """
    try:
        _kill_previous_server(output_dir)

        port = _find_free_port()
        url = f"http://localhost:{port}/{html_filename}"

        proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port), "--directory", str(output_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        _write_pid(output_dir, proc.pid)

        time.sleep(1.2)

        print(f"\n\u2705  Report ready \u00b7 {url}\n")

        opened = False
        try:
            opened = webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass

        if not opened:
            print(f"   \u26a0  Could not open browser automatically.")
            print(f"   Open manually: {url}\n")

        return url

    except Exception:  # noqa: BLE001
        print(
            "\n\u26a0  Could not start server automatically.\n"
            "   To view the report with chat support, double-click:\n"
            "     open_report.sh       (Linux)\n"
            "     open_report.command  (Mac)\n"
            "     open_report.bat      (Windows)"
        )
        return ""


def _find_free_port() -> int:
    """Ask the OS for a free port."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _write_pid(output_dir: Path, pid: int) -> None:
    try:
        (output_dir / _PID_FILE).write_text(str(pid), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def _kill_previous_server(output_dir: Path) -> None:
    import signal  # noqa: PLC0415

    pid_file = output_dir / _PID_FILE
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        os.kill(pid, signal.SIGTERM)
    except Exception:  # noqa: BLE001
        pass  # process already gone, file missing, or unreadable


def _write_launcher_files(output_dir: Path, html_filename: str) -> None:
    """Write double-clickable launcher files for Linux, Windows and macOS."""
    sh = output_dir / "open_report.sh"
    sh.write_text(
        f"#!/bin/bash\n"
        f"cd \"$(dirname \"$0\")\"\n"
        f"python3 -m http.server 8000 --directory . &\n"
        f"sleep 1.2\n"
        f"xdg-open http://localhost:8000/{html_filename} 2>/dev/null"
        f" || sensible-browser http://localhost:8000/{html_filename} 2>/dev/null"
        f" || echo 'Open: http://localhost:8000/{html_filename}'\n"
        f"wait\n",
        encoding="utf-8",
    )
    sh.chmod(0o755)

    bat = output_dir / "open_report.bat"
    bat.write_text(
        f"@echo off\n"
        f"cd /d \"%~dp0\"\n"
        f"start http://localhost:8000/{html_filename}\n"
        f"python -m http.server 8000 --directory .\n"
        f"pause\n",
        encoding="utf-8",
    )

    cmd = output_dir / "open_report.command"
    cmd.write_text(
        f"#!/bin/bash\n"
        f"cd \"$(dirname \"$0\")\"\n"
        f"python3 -m http.server 8000 --directory . &\n"
        f"sleep 1.2\n"
        f"open http://localhost:8000/{html_filename}\n"
        f"wait\n",
        encoding="utf-8",
    )
    cmd.chmod(0o755)
