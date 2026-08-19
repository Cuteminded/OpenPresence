import os
import threading
import time
from urllib.parse import quote, urlencode, urlparse

from pypresence import Presence
from pypresence.types import ActivityType

from openpresence.config import CONFIG, get_player_settings
from openpresence.media import MediaEvent


class DiscordPresence:
    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        self.client = Presence(client_id)
        self.lock = threading.Lock()
        self.connected = False

    def connect(self) -> None:
        with self.lock:
            self._ensure_connected()

    def update(self, event: MediaEvent) -> None:
        client_id, custom_client, activity_type = get_player_settings(event.source_name)
        presence = build_presence(event, activity_type, custom_client)
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


def build_presence(event: MediaEvent, activity_type: int, custom_client: bool) -> dict:
    started_at = int((event.timestamp or time.time()) - event.position)
    presence = {
        "activity_type": ActivityType(activity_type),
        "details": event.title,
        "state": f"by {event.artist}",
        "large_text": event.album or event.title,
        "start": started_at,
    }
    if event.duration:
        presence["end"] = int(started_at + event.duration)
    if event.artwork_url:
        presence["large_image"] = event.artwork_url
    if event.source_url and not custom_client:
        domain = urlparse(event.source_url).hostname
        if domain:
            presence["small_image"] = f"https://www.google.com/s2/favicons?sz=64&domain={quote(domain)}"
            presence["small_text"] = event.source_name
    presence["buttons"] = [{"label": "View media", "url": _youtube_search_url(event)}]
    return presence


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


def _youtube_search_url(event: MediaEvent) -> str:
    return f"https://www.youtube.com/results?{urlencode({'search_query': f'{event.title} - {event.artist}'})}"
