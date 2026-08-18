import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from flask import Flask, jsonify, request
from pypresence import Presence
from pypresence.types import ActivityType
from waitress import serve


PROJECT_DIR = Path(__file__).parent
CONFIG_FILE = PROJECT_DIR / "config.json"


def load_config() -> dict[str, Any]:
    with CONFIG_FILE.open(encoding="utf-8") as file:
        return json.load(file)


CONFIG = load_config()
WEBHOOK_FILE = PROJECT_DIR / CONFIG["server"]["webhook_file"]
LOG_FILE = PROJECT_DIR / CONFIG["server"].get("log_file", "server.log")
CONFIG_LOCK = threading.Lock()
PLAYING_EVENTS = {"scrobble","nowplaying","playing","startedplaying","resumed","resumedplaying"}
PAUSED_EVENTS = {"paused", "stopped", "stoppedplaying"}


def get_player_settings(player_name: str) -> tuple[str, bool, int]:
    with CONFIG_LOCK:
        custom_client_ids = CONFIG.setdefault("web_scrobbler", {}).setdefault("custom_client_ids", {})
        if player_name not in custom_client_ids:
            custom_client_ids[player_name] = {"client_id": "","activity_type": 2}
            CONFIG_FILE.write_text(json.dumps(CONFIG, indent=2, ensure_ascii=False) + "\n",encoding="utf-8")

        player_config = custom_client_ids[player_name]
        if not isinstance(player_config, dict):
            player_config = {"client_id": str(player_config or "").strip(),"activity_type": 0}
            custom_client_ids[player_name] = player_config
            CONFIG_FILE.write_text(json.dumps(CONFIG, indent=2, ensure_ascii=False) + "\n",encoding="utf-8")

        custom_client_id = str(player_config.get("client_id") or "").strip()
        try:
            activity_type = int(player_config.get("activity_type", 0))
        except (TypeError, ValueError):
            activity_type = 0

        if activity_type not in {0, 2, 3, 5}:
            activity_type = 0

        fallback = os.getenv("DISCORD_CLIENT_ID") or CONFIG["discord"]["client_id"]
        return (custom_client_id or fallback, bool(custom_client_id), activity_type)


class DiscordPresence:
    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        self.client = Presence(client_id)
        self.lock = threading.Lock()
        self.connected = False

    def connect(self) -> None:
        with self.lock:
            self._ensure_connected()

    def update(self, payload: dict[str, Any], event: str = "missing_eventName") -> None:
        song = payload["data"]["song"]
        parsed = song["parsed"]
        metadata = song.get("metadata", {})
        connector = song.get("connector", {})

        track = parsed.get("track") or "Unknown track"
        artist = parsed.get("artist") or "Unknown artist"
        album = parsed.get("album")
        player_name = metadata.get("label") or connector.get("label") or "Web Scrobbler"
        client_id, uses_custom_client_id, activity_type = get_player_settings(player_name)
        duration = parsed.get("duration")
        current_time = parsed.get("currentTime") or 0
        started_at = metadata.get("startTimestamp")
        event_time = payload.get("time", int(time.time() * 1000)) / 1000
        started_at = int(event_time - current_time)
        if event.lower() in {"nowplaying", "resumedplaying"}:
            print(f"[{event}] for {player_name}: {track} by {artist}")

        presence: dict[str, Any] = {
            "activity_type": ActivityType(activity_type),
            "details": track,
            "state": f"by {artist}",
            "large_text": album or track,
            "start": int(started_at),
        }

        if duration:
            presence["end"] = int(started_at + duration)

        artwork = parsed.get("trackArt") or metadata.get("trackArtUrl")
        if artwork:
            presence["large_image"] = artwork

        origin_url = parsed.get("originUrl")
        if origin_url and not uses_custom_client_id:
            domain = urlparse(origin_url).hostname
            if domain:
                presence["small_image"] = ("https://www.google.com/s2/favicons"f"?sz=64&domain={quote(domain)}")
                presence["small_text"] = player_name

        track_url = "https://www.youtube.com/results?search_query={0}".format(f"{track}+-+{artist}".replace(" ", "+"))
        if track_url:
            presence["buttons"] = [{"label": "View track", "url": track_url}]

        with self.lock:
            self._use_client_id(client_id)
            self._ensure_connected()
            self.client.update(**presence)

    def clear(self) -> None:
        with self.lock:
            self._ensure_connected()
            self.client.clear()

    def _ensure_connected(self) -> None:
        if not self.connected:
            self.client.connect()
            self.connected = True

    def _use_client_id(self, client_id: str) -> None:
        if client_id == self.client_id:
            return

        if self.connected:
            self.client.clear()
            self.client.close()

        self.client_id = client_id
        self.client = Presence(client_id)
        self.connected = False

def create_discord_presence() -> DiscordPresence | None:
    discord_config = CONFIG["discord"]
    if not discord_config["enabled"]:
        return None

    client_id = os.getenv("DISCORD_CLIENT_ID") or discord_config["client_id"]
    if not client_id:
        print("Discord client ID is not configured, Rich Presence is disabled")
        return None

    discord = DiscordPresence(client_id)
    try:
        discord.connect()
        print("Connected to Discord")
    except Exception as error:
        print(f"Could not connect to Discord: {error}")
    return discord


def create_app() -> Flask:
    app = Flask(__name__)
    discord = create_discord_presence()

    @app.post("/file")
    def receive_file():
        WEBHOOK_FILE.write_bytes(request.get_data(cache=False))
        return jsonify(success=True)

    @app.post("/scrobbler")
    def receive_scrobbler():
        body = request.get_data(cache=False)
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            print(f"Invalid Web Scrobbler JSON: {error}")
            return jsonify(success=False, error="Invalid JSON"), 400

        if not isinstance(payload, dict):
            return jsonify(success=False, error="Expected a JSON object"), 400

        event_name = str(payload.get("eventName", "")).lower()
        try:
            if event_name in PLAYING_EVENTS:
                if discord:
                    discord.update(payload,event_name)
            elif event_name in PAUSED_EVENTS:
                if discord and CONFIG["discord"]["clear_on_pause"]:
                    discord.clear()
            else:
                safe_event_name = re.sub(
                    r"[^a-zA-Z0-9_-]", "_", event_name or "missing_eventName"
                )
                event_file = PROJECT_DIR / f"{safe_event_name}.json"
                event_file.write_bytes(body)
                print(f"Ignoring Web Scrobbler event: {event_name or 'missing eventName'}")
        except Exception as error:
            print(f"Discord Rich Presence update failed: {error}")
            if discord:
                try:
                    discord.clear()
                    print("Cleared Discord Rich Presence after failed update")
                except Exception as clear_error:
                    print(f"Could not clear Discord Rich Presence: {clear_error}")
        return jsonify(success=True, eventName=event_name)
    return app

def run_server() -> None:
    host = CONFIG["server"]["host"]
    port = CONFIG["server"]["port"]
    serve(create_app(), host=host, port=port, threads=4)


def start_background() -> None:
    command = [sys.executable, "-u", str(Path(__file__).resolve()), "--serve"]
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    flags = 0
    if os.name == "nt":
        flags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NO_WINDOW
        )

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

    parser = argparse.ArgumentParser(description="Web Scrobbler Discord Rich Presence")
    parser.add_argument("--background", action="store_true", help="run detached")
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.background:
        start_background()
    else:
        run_server()

if __name__ == "__main__":
    main()
