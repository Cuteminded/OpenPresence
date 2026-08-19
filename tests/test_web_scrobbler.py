import unittest

from openpresence.adapters.web_scrobbler import parse_web_scrobbler
from openpresence.media import PlaybackState


class WebScrobblerAdapterTests(unittest.TestCase):
    def test_translates_web_scrobbler_payload(self):
        event = parse_web_scrobbler(
            {
                "eventName": "nowplaying",
                "time": 2_000_000,
                "data": {
                    "song": {
                        "parsed": {
                            "track": "A track",
                            "artist": "An artist",
                            "album": "An album",
                            "currentTime": 15,
                            "duration": 180,
                            "originUrl": "https://player.example/track",
                        },
                        "metadata": {"label": "Example player"},
                    }
                },
            }
        )

        self.assertIsNotNone(event)
        self.assertEqual(event.state, PlaybackState.PLAYING)
        self.assertEqual(event.title, "A track")
        self.assertEqual(event.source_name, "Example player")
        self.assertEqual(event.timestamp, 2000)

    def test_ignores_unknown_event(self):
        self.assertIsNone(parse_web_scrobbler({"eventName": "unknown"}))


if __name__ == "__main__":
    unittest.main()
