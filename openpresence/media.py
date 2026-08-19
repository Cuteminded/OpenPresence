from dataclasses import dataclass
from enum import Enum
from typing import Any


class PlaybackState(str, Enum):
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass(frozen=True)
class MediaEvent:
    state: PlaybackState
    title: str = "Unknown track"
    artist: str = "Unknown artist"
    album: str | None = None
    artwork_url: str | None = None
    source_name: str = "Unknown player"
    source_url: str | None = None
    media_url: str | None = None
    media_label: str = "View"
    duration: float | None = None
    position: float = 0
    timestamp: float | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MediaEvent":
        try:
            state = PlaybackState(str(payload.get("state", "")).lower())
        except ValueError as error:
            raise ValueError("state must be playing, paused, or stopped") from error
        return cls(
            state=state,
            title=str(payload.get("title") or "Unknown track"),
            artist=str(payload.get("artist") or "Unknown artist"),
            album=_text(payload.get("album")),
            artwork_url=_text(payload.get("artwork_url")),
            source_name=str(payload.get("source_name") or "Unknown player"),
            source_url=_text(payload.get("source_url")),
            media_url=_text(payload.get("media_url")),
            media_label=str(payload.get("media_label") or "View"),
            duration=_number(payload.get("duration")),
            position=_number(payload.get("position")) or 0,
            timestamp=_number(payload.get("timestamp")),
        )


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Expected a number, got {value!r}") from error
