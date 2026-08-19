import json
import re

from flask import Flask, jsonify, request

from openpresence.adapters.web_scrobbler import parse_web_scrobbler
from openpresence.config import CONFIG, PROJECT_DIR, WEBHOOK_FILE
from openpresence.discord import DiscordPresence, create_discord_presence
from openpresence.media import MediaEvent, PlaybackState


def create_app(presence: DiscordPresence | None = None) -> Flask:
    app = Flask(__name__)
    discord = presence if presence is not None else create_discord_presence()

    @app.post("/file")
    def receive_file():
        WEBHOOK_FILE.write_bytes(request.get_data(cache=False))
        return jsonify(success=True)

    @app.post("/media")
    def receive_media():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(success=False, error="Expected a JSON object"), 400
        try:
            event = MediaEvent.from_dict(payload)
        except ValueError as error:
            return jsonify(success=False, error=str(error)), 400
        _handle_event(discord, event)
        return jsonify(success=True, state=event.state.value)

    @app.post("/scrobbler")
    def receive_scrobbler():
        body = request.get_data(cache=False)
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            return jsonify(success=False, error=f"Invalid JSON: {error}"), 400
        if not isinstance(payload, dict):
            return jsonify(success=False, error="Expected a JSON object"), 400
        event_name = str(payload.get("eventName", "")).lower()
        event = parse_web_scrobbler(payload)
        if event:
            _handle_event(discord, event)
        else:
            _save_unknown_event(event_name, body)
        return jsonify(success=True, eventName=event_name)

    return app


def _handle_event(discord: DiscordPresence | None, event: MediaEvent) -> None:
    if not discord:
        return
    print(f"[{event.state.value}] for {event.source_name}: {event.title} by {event.artist}")
    try:
        if event.state == PlaybackState.PLAYING:
            discord.update(event)
        elif CONFIG["discord"]["clear_on_pause"]:
            discord.clear()
    except Exception as error:
        print(f"Discord Rich Presence update failed: {error}")
        try:
            discord.clear()
        except Exception as clear_error:
            print(f"Could not clear Discord Rich Presence: {clear_error}")


def _save_unknown_event(event_name: str, body: bytes) -> None:
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", event_name or "missing_eventName")
    (PROJECT_DIR / f"{safe_name}.json").write_bytes(body)
    print(f"Ignoring Web Scrobbler event: {event_name or 'missing eventName'}")
