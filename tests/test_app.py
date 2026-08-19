import unittest

from openpresence.app import create_app
from openpresence.media import PlaybackState


class FakePresence:
    def __init__(self):
        self.events = []
        self.clear_count = 0

    def update(self, event):
        self.events.append(event)

    def clear(self):
        self.clear_count += 1


class MediaRouteTests(unittest.TestCase):
    def setUp(self):
        self.presence = FakePresence()
        self.client = create_app(self.presence).test_client()

    def test_playing_event_updates_presence(self):
        response = self.client.post(
            "/media",
            json={
                "state": "playing",
                "title": "A track",
                "artist": "An artist",
                "source_name": "Desktop player",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.presence.events), 1)
        self.assertEqual(self.presence.events[0].state, PlaybackState.PLAYING)

    def test_pause_clears_presence(self):
        response = self.client.post("/media", json={"state": "paused"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.presence.clear_count, 1)

    def test_invalid_event_returns_bad_request(self):
        response = self.client.post("/media", json={"state": "buffering"})

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
