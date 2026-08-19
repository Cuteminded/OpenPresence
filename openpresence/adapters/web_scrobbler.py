import time
from typing import Any

from openpresence.media import MediaEvent, PlaybackState

PLAYING_EVENTS = {"scrobble", "nowplaying", "playing", "startedplaying", "resumed", "resumedplaying"}
PAUSED_EVENTS = {"paused"}
STOPPED_EVENTS = {"stopped", "stoppedplaying"}


def parse_web_scrobbler(payload: dict[str, Any]) -> MediaEvent | None:
    state = _get_state(str(payload.get("eventName", "")).lower())
    if state is None:
        return None
    song = payload.get("data", {}).get("song", {})
    parsed = song.get("parsed", {})
    metadata = song.get("metadata", {})
    connector = song.get("connector", {})
    return MediaEvent(
        state=state,
        title=parsed.get("track") or "Unknown track",
        artist=parsed.get("artist") or "Unknown artist",
        album=parsed.get("album"),
        artwork_url=parsed.get("trackArt") or metadata.get("trackArtUrl"),
        source_name=metadata.get("label") or connector.get("label") or "Web Scrobbler",
        source_url=parsed.get("originUrl"),
        media_label="View media",
        duration=_optional_number(parsed.get("duration")),
        position=_number(parsed.get("currentTime"), 0),
        timestamp=_number(payload.get("time"), time.time() * 1000) / 1000,
    )


def _get_state(name: str) -> PlaybackState | None:
    if name in PLAYING_EVENTS:
        return PlaybackState.PLAYING
    if name in PAUSED_EVENTS:
        return PlaybackState.PAUSED
    if name in STOPPED_EVENTS:
        return PlaybackState.STOPPED
    return None


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_number(value: Any) -> float | None:
    return None if value is None else _number(value, 0)
