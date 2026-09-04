import unittest
from unittest.mock import patch

from openpresence.config import CONFIG
from openpresence.runtime import run_server


class RunServerTests(unittest.TestCase):
    @patch("openpresence.runtime.send_error_notification")
    @patch("openpresence.runtime.create_app", side_effect=RuntimeError("Discord is not running"))
    def test_startup_error_sends_notification_by_default(self, create_app, send_notification):
        with patch.dict(CONFIG, {"server": {}}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Discord is not running"):
                run_server()

        create_app.assert_called_once_with()
        send_notification.assert_called_once_with("Discord is not running")

    @patch("openpresence.runtime.send_error_notification")
    @patch("openpresence.runtime.create_app", side_effect=RuntimeError("Discord is not running"))
    def test_notifications_can_be_disabled(self, create_app, send_notification):
        settings = {"server": {"notifications": False}}

        with patch.dict(CONFIG, settings, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Discord is not running"):
                run_server()

        create_app.assert_called_once_with()
        send_notification.assert_not_called()


if __name__ == "__main__":
    unittest.main()
