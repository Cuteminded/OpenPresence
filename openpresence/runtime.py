import argparse
import os
import subprocess
import sys

from waitress import serve

from openpresence.app import create_app
from openpresence.config import CONFIG, LOG_FILE, PROJECT_DIR
from openpresence.notifications import send_error_notification


def run_server() -> None:
    settings = CONFIG["server"]
    try:
        app = create_app()
    except Exception as error:
        if settings.get("notifications", True):
            _send_startup_error_notification(error)
        raise
    serve(app, host=settings["host"], port=settings["port"], threads=4)


def _send_startup_error_notification(error: Exception) -> None:
    try:
        send_error_notification(str(error))
    except Exception as notification_error:
        print(f"Could not send desktop notification: {notification_error}", file=sys.stderr)


def start_background() -> None:
    command = [sys.executable, "-u", str(PROJECT_DIR / "server.py"), "--serve"]
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
    with LOG_FILE.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command,
            cwd=PROJECT_DIR,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=log_file,
            creationflags=flags,
            env=environment,
            start_new_session=os.name != "nt",
        )
    print(f"Server started in the background with process ID {process.pid}")
    print(f"Logs: {LOG_FILE}")


def main() -> None:
    for output in (sys.stdout, sys.stderr):
        if hasattr(output, "reconfigure"):
            output.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Media player Discord Rich Presence bridge")
    parser.add_argument("--background", action="store_true", help="run detached")
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    start_background() if args.background else run_server()
