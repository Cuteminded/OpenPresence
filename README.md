# OpenPresence

OpenPresence turns media player events into Discord Rich Presence. It accepts a generic JSON format and includes an adapter for [Web Scrobbler](https://webscrobbler.com).

It runs a small local webhook server. When Web Scrobbler reports a track, OpenPresence sends its title, artist, album art, playback time, and player name to Discord. Pausing or stopping playback can clear the activity.

## Requirements

- Python 3.10 or newer
- Discord running on the same computer as OpenPresence
- A [Discord application](https://discord.com/developers/applications)
- The [Web Scrobbler browser extension](https://webscrobbler.com)

## Install

Clone the repository, open its directory, and create a virtual environment.

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Copy the example configuration:

```powershell
# Windows PowerShell
Copy-Item config.example.json config.json
```

```bash
# macOS or Linux
cp config.example.json config.json
```

Open `config.json` and replace `YOUR_DISCORD_APPLICATION_ID` with the application ID from the Discord Developer Portal.

## Configure

The example configuration contains these settings:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "webhook_file": "webhook.json",
    "log_file": "server.log",
    "notifications": true
  },
  "discord": {
    "enabled": true,
    "client_id": "YOUR_DISCORD_APPLICATION_ID",
    "clear_on_pause": true
  },
  "players": {}
}
```

### Server settings

`host` controls which network interfaces accept webhook requests. Change it to `127.0.0.1` when Web Scrobbler and OpenPresence run on the same computer. Keep `0.0.0.0` only when another device needs to reach the server on a trusted network.

`port` is the HTTP port used by the webhook server. The default is `8000`.

`webhook_file` is where requests to `/file` are stored. `log_file` receives output when OpenPresence runs in the background.

`notifications` controls desktop notifications for startup errors. It defaults to `true` when the setting is missing. Set it to `false` to disable OS notifications.

### Discord settings

`enabled` turns Discord Rich Presence updates on or off.

`client_id` is the default Discord application ID. You can override it with the `DISCORD_CLIENT_ID` environment variable.

`clear_on_pause` clears the current Discord activity when Web Scrobbler reports a pause or stop event.

### Player-specific Discord applications

OpenPresence can use a different Discord application for each player. When it sees a new player name, it adds an entry to `players` in `config.json`:

```json
"players": {
  "YouTube Music": {
    "client_id": "",
    "activity_type": 2
  }
}
```

An empty `client_id` uses the default Discord application. Add another application ID to use it for that player:

```json
"players": {
  "YouTube Music": {
    "client_id": "PLAYER_SPECIFIC_APPLICATION_ID",
    "activity_type": 2
  }
}
```

The supported activity types are:

| Value | Discord activity |
| ---: | --- |
| `0` | Playing |
| `2` | Listening |
| `3` | Watching |
| `5` | Competing |

Invalid values fall back to `0`. OpenPresence omits the small player favicon when it uses a player-specific application.

## Connect Web Scrobbler

Start OpenPresence in the current terminal:

```bash
python server.py
```

If your system uses `python3` for Python 3, run `python3 server.py` instead.

In Web Scrobbler, add a webhook account and set its API URL to:

```text
http://127.0.0.1:8000/scrobbler
```

Change the host or port in this URL if Web Scrobbler connects from another device or you changed the server configuration.

Playing and resumed events update Discord Rich Presence. Pause and stop events clear it when `clear_on_pause` is enabled. OpenPresence saves unrecognized events as `<event_name>.json` in the project directory so you can inspect them.

The "View media" button opens the supplied media URL. If the event has no media URL, it opens a YouTube search for the current title and artist.

## Connect another media player

Any program that can send an HTTP request can use `POST /media`. Send a JSON object with a playback `state` and any available metadata:

```json
{
  "state": "playing",
  "title": "A track",
  "artist": "An artist",
  "album": "An album",
  "artwork_url": "https://example.com/cover.jpg",
  "source_name": "Desktop player",
  "source_url": "https://player.example",
  "media_label": "View track",
  "media_url": "https://player.example/tracks/123",
  "duration": 240,
  "position": 30,
  "timestamp": 1787148000
}
```

`state` must be `playing`, `paused`, or `stopped`. OpenPresence updates Discord for `playing`. It clears the activity for `paused` and `stopped` when `clear_on_pause` is enabled.

All other fields are optional. `duration` and `position` use seconds. `timestamp` is the Unix time when the player produced the event.

Example request:

```bash
curl -X POST http://127.0.0.1:8000/media \
  -H "Content-Type: application/json" \
  -d '{"state":"playing","title":"A track","artist":"An artist","source_name":"My player"}'
```

## Run in the background

Start a detached process:

```bash
python server.py --background
```

The command prints the process ID. OpenPresence writes output to the configured log file.
If OpenPresence cannot connect to Discord during startup, it sends a desktop notification and then exits. This also applies when it runs in the foreground. Notifications use the native notification system on Windows, macOS, and Linux.

Stop the process on Windows PowerShell:

```powershell
Stop-Process -Id PROCESS_ID
```

Stop it on macOS or Linux:

```bash
kill PROCESS_ID
```

## HTTP routes

### `POST /media`

Accepts generic media events.

### `POST /scrobbler`

Specifically made for [Web Scrobbler](https://webscrobbler.com) events.


### `POST /file`

Writes the raw request body to the configured `webhook_file`. Each request replaces the existing file. (Useful for debugging or implementing a custom adapter.)

## What's next

OpenPresence currently only supports direct mapping of [Web Scrobbler](https://webscrobbler.com) to Discord. Support for other scrobblers and media players may be added in future releases. 

To request support for a specific player, open an issue or add your own adapter and submit a pull request.
