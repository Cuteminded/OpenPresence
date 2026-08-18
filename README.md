# OpenPresence

A small Flask webhook server that publishes Web Scrobbler playback data as Discord Rich Presence. It supports player-specific Discord applications, album artwork, playback timestamps, track links, pause events, and detached background operation.

## Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux
- Discord Desktop running on the same computer
- A Discord application ID
- [The Web Scrobbler browser extension](https://webscrobbler.com)

## Setup

1. Clone the repository and enter its directory.
2. Create a virtual environment.

   Windows PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   macOS or Linux:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the dependencies:

   ```text
   pip install -r requirements.txt
   ```

4. Copy the example configuration:

   Windows PowerShell:

   ```powershell
   Copy-Item config.example.json config.json
   ```

   macOS or Linux:

   ```bash
   cp config.example.json config.json
   ```

5. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications) and put its application ID in `discord.client_id`.

## Configuration

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8000,
    "webhook_file": "webhook.json",
    "log_file": "server.log"
  },
  "discord": {
    "enabled": true,
    "client_id": "YOUR_DISCORD_APPLICATION_ID",
    "clear_on_pause": true
  },
  "web_scrobbler": {
    "custom_client_ids": {}
  }
}
```

Use `127.0.0.1` to accept requests only from the local computer. Use `0.0.0.0` only when another device must reach the server and the network is trusted.

The `DISCORD_CLIENT_ID` environment variable can override the default client ID.

### Player-specific Discord applications

When Web Scrobbler reports a new `metadata.label`, the server automatically adds it to `web_scrobbler.custom_client_ids` with an empty value:

```json
"custom_client_ids": {
  "YouTube Music": {
    "client_id": "",
    "activity_type": 0
  }
}
```

An empty `client_id` uses the default Discord application. Set a different application ID to use a player-specific application:

```json
"custom_client_ids": {
  "YouTube Music": {
    "client_id": "PLAYER_SPECIFIC_APPLICATION_ID",
    "activity_type": 0
  }
}
```

The small player favicon is hidden when a player-specific Discord application is active.

Supported activity types are `0` (Playing), `2` (Listening), `3` (Watching), and `5` (Competing). The default and fallback value is `0`.

## Running the server

Run in the current terminal:

```text
python server.py
```

Run as a detached background process:

```text
python server.py --background
```

On systems where Python 3 is exposed as `python3`, use that command instead of `python`.

The background command prints its process ID. Output is written to the configured `server.log` file.

Stop it on Windows PowerShell:

```powershell
Stop-Process -Id PROCESS_ID
```

Stop it on macOS or Linux:

```bash
kill PROCESS_ID
```

## Web Scrobbler setup

Add a webhook account in Web Scrobbler and use this API URL:

```text
http://127.0.0.1:8000/scrobbler
```

The server handles common playing, resumed, paused, and stopped events. Unknown events are accepted and saved as `<event_name>.json` for inspection.

## Routes

### `POST /scrobbler`

Receives Web Scrobbler events and updates or clears Discord Rich Presence.

### `POST /file`

Overwrites the configured webhook file with the raw request body.
