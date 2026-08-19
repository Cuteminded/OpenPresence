import unittest

from openpresence.media import MediaEvent, PlaybackState


class MediaEventTests(unittest.TestCase):
    def test_builds_event_from_generic_payload(self):
        event = MediaEvent.from_dict(
            {
                "state": "playing",
                "title": "A track",
                "artist": "An artist",
                "source_name": "Desktop player",
                "duration": 240,
                "position": 12,
            }
        )

        self.assertEqual(event.state, PlaybackState.PLAYING)
        self.assertEqual(event.source_name, "Desktop player")
        self.assertEqual(event.duration, 240)
        self.assertEqual(event.position, 12)

    def test_rejects_unknown_state(self):
        with self.assertRaisesRegex(ValueError, "state must be"):
            MediaEvent.from_dict({"state": "buffering"})


if __name__ == "__main__":
    unittest.main()
