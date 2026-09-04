import asyncio

from desktop_notifier import DesktopNotifier


def send_error_notification(message: str) -> None:
    notifier = DesktopNotifier(app_name="OpenPresence")
    asyncio.run(
        notifier.send(
            title="OpenPresence could not start",
            message=message,
        )
    )
