import json
import os
import threading
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_DIR / "config.json"
CONFIG_LOCK = threading.Lock()


def load_config() -> dict[str, Any]:
    with CONFIG_FILE.open(encoding="utf-8") as file:
        return json.load(file)


CONFIG = load_config()
WEBHOOK_FILE = PROJECT_DIR / CONFIG["server"]["webhook_file"]
LOG_FILE = PROJECT_DIR / CONFIG["server"].get("log_file", "server.log")


def get_player_settings(player_name: str) -> tuple[str, bool, int]:
    with CONFIG_LOCK:
        players = CONFIG.setdefault("players", {})
        legacy_players = CONFIG.get("web_scrobbler", {}).get("custom_client_ids", {})
        for name, settings in legacy_players.items():
            players.setdefault(name, settings)

        changed = False
        if player_name not in players:
            players[player_name] = {"client_id": "", "activity_type": 2}
            changed = True

        settings = players[player_name]
        if not isinstance(settings, dict):
            settings = {"client_id": str(settings or "").strip(), "activity_type": 0}
            players[player_name] = settings
            changed = True
        if changed:
            CONFIG_FILE.write_text(json.dumps(CONFIG, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        custom_client_id = str(settings.get("client_id") or "").strip()
        activity_type = _parse_activity_type(settings.get("activity_type", 0))
        fallback = os.getenv("DISCORD_CLIENT_ID") or CONFIG["discord"]["client_id"]
        return custom_client_id or fallback, bool(custom_client_id), activity_type


def _parse_activity_type(value: Any) -> int:
    try:
        activity_type = int(value)
    except (TypeError, ValueError):
        return 0
    return activity_type if activity_type in {0, 2, 3, 5} else 0
