"""Windows desktop notification support for wx-cli.

This module provides toast notifications for severe weather alerts on Windows 10/11.
Requires win10toast or plyer package (optional dependencies).
"""

from __future__ import annotations

import os
import sys
from typing import Any

# Check if we're on Windows
IS_WINDOWS = sys.platform == "win32"


def is_notifications_enabled() -> bool:
    """Check if Windows notifications are enabled via environment variable."""
    return os.getenv("WX_NOTIFICATIONS", "0").strip().lower() in {"1", "true", "yes", "on"}


def send_notification(
    title: str,
    message: str,
    *,
    duration: int = 10,
    icon_path: str | None = None,
    urgency: str = "normal",
) -> bool:
    """Send a Windows toast notification.

    Args:
        title: Notification title
        message: Notification body text
        duration: How long to show notification (seconds)
        icon_path: Path to icon file (optional)
        urgency: "normal" or "critical" (affects behavior)

    Returns:
        True if notification was sent successfully, False otherwise
    """
    if not IS_WINDOWS:
        return False

    if not is_notifications_enabled():
        return False

    # Try win10toast first (simpler, Windows-specific)
    try:
        from win10toast import ToastNotifier

        toaster = ToastNotifier()
        toaster.show_toast(
            title,
            message,
            icon_path=icon_path,
            duration=duration,
            threaded=True,
        )
        return True
    except ImportError:
        pass
    except Exception:  # noqa: BLE001
        pass

    # Fallback to plyer (cross-platform)
    try:
        from plyer import notification

        notification.notify(
            title=title,
            message=message,
            app_name="wx Weather Bot",
            timeout=duration,
        )
        return True
    except ImportError:
        pass
    except Exception:  # noqa: BLE001
        pass

    return False


def notify_severe_weather(alerts: list[dict[str, Any]]) -> bool:
    """Send notifications for severe weather alerts.

    Args:
        alerts: List of alert dictionaries from wx fetchers

    Returns:
        True if any notification was sent successfully
    """
    if not alerts:
        return False

    # Filter for severe weather only
    severe_keywords = {
        "tornado",
        "severe thunderstorm",
        "flash flood",
        "flood warning",
        "extreme",
        "emergency",
    }

    severe_alerts = []
    for alert in alerts:
        event = alert.get("event", "").lower()
        severity = alert.get("severity", "").lower()

        is_severe = any(keyword in event for keyword in severe_keywords)
        is_high_severity = severity in {"extreme", "severe"}

        if is_severe or is_high_severity:
            severe_alerts.append(alert)

    if not severe_alerts:
        return False

    # Send notification for the most severe alert
    alert = severe_alerts[0]
    event = alert.get("event", "Weather Alert")
    headline = alert.get("headline", "Check weather conditions")

    # Truncate message if too long (Windows toast limit)
    if len(headline) > 200:
        headline = headline[:197] + "..."

    title = f"⚠️ {event}"
    message = headline

    # Use critical urgency for tornado/extreme events
    urgency = "critical" if "tornado" in event.lower() or "extreme" in str(alert.get("severity", "")).lower() else "normal"

    return send_notification(title, message, duration=15, urgency=urgency)


def notify_weather_summary(summary: str, location: str) -> bool:
    """Send a notification with weather summary.

    Args:
        summary: Weather summary text
        location: Location name

    Returns:
        True if notification was sent successfully
    """
    title = f"🌤️ Weather for {location}"

    # Truncate summary if too long
    if len(summary) > 200:
        summary = summary[:197] + "..."

    return send_notification(title, summary, duration=10)


def test_notification() -> bool:
    """Send a test notification to verify setup.

    Returns:
        True if test notification was sent successfully
    """
    title = "wx Weather Bot"
    message = "Notifications are working! You'll receive alerts for severe weather."

    success = send_notification(title, message, duration=5)

    if not success:
        print("❌ Notifications not available.")
        print("\nTo enable Windows notifications:")
        print("  1. Install notification library:")
        print("     pip install win10toast")
        print("  2. Enable in your .env file:")
        print("     WX_NOTIFICATIONS=1")
        print("  3. Check Windows notification settings:")
        print("     Settings → System → Notifications → Python")

    return success


def get_notification_status() -> dict[str, Any]:
    """Get current notification configuration status.

    Returns:
        Dictionary with status information
    """
    status = {
        "platform": sys.platform,
        "is_windows": IS_WINDOWS,
        "enabled_in_config": is_notifications_enabled(),
        "win10toast_available": False,
        "plyer_available": False,
    }

    try:
        import win10toast  # noqa: F401

        status["win10toast_available"] = True
    except ImportError:
        pass

    try:
        import plyer  # noqa: F401

        status["plyer_available"] = True
    except ImportError:
        pass

    status["notification_library"] = (
        "win10toast"
        if status["win10toast_available"]
        else "plyer" if status["plyer_available"] else "none"
    )

    status["ready"] = (
        IS_WINDOWS
        and is_notifications_enabled()
        and (status["win10toast_available"] or status["plyer_available"])
    )

    return status


def install_notification_support() -> bool:
    """Attempt to install notification library via pip.

    Returns:
        True if installation was successful
    """
    if not IS_WINDOWS:
        print("Notifications are only supported on Windows.")
        return False

    print("Installing win10toast for Windows notifications...")

    try:
        import subprocess

        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "win10toast"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            print("✓ win10toast installed successfully!")
            print("\nTo enable notifications, add to your .env file:")
            print("  WX_NOTIFICATIONS=1")
            return True
        else:
            print(f"❌ Installation failed: {result.stderr}")
            return False
    except Exception as e:  # noqa: BLE001
        print(f"❌ Installation error: {e}")
        return False


# CLI integration helper
def notify_from_cli(result: Any) -> None:
    """Send notification based on CLI command result.

    Args:
        result: OrchestrationResult from wx CLI commands
    """
    if not is_notifications_enabled():
        return

    try:
        command = getattr(result, "command", None)

        if command == "alerts":
            # Check for severe weather alerts
            feature_pack = getattr(result, "feature_pack", {})
            alerts = feature_pack.get("alerts_quick", [])
            if alerts:
                notify_severe_weather(alerts)

        elif command in {"forecast", "question"}:
            # Send summary notification for regular queries
            response = getattr(result, "response", None)
            if response:
                summary = getattr(response, "bottom_line", None)
                if summary:
                    location = result.query if hasattr(result, "query") else "your location"
                    notify_weather_summary(summary, location)

    except Exception:  # noqa: BLE001
        # Don't crash the CLI if notifications fail
        pass


if __name__ == "__main__":
    # Test notifications when run directly
    print("Testing Windows notifications...")
    print()

    status = get_notification_status()
    print("Notification Status:")
    print(f"  Platform: {status['platform']}")
    print(f"  Windows: {status['is_windows']}")
    print(f"  Enabled in config: {status['enabled_in_config']}")
    print(f"  Library available: {status['notification_library']}")
    print(f"  Ready: {status['ready']}")
    print()

    if not status["ready"]:
        if not IS_WINDOWS:
            print("Notifications are only supported on Windows.")
        elif not (status["win10toast_available"] or status["plyer_available"]):
            print("No notification library found.")
            install = input("Would you like to install win10toast? (y/n): ")
            if install.lower() == "y":
                install_notification_support()
        elif not status["enabled_in_config"]:
            print("Notifications are disabled in configuration.")
            print("To enable, add to your .env file: WX_NOTIFICATIONS=1")
    else:
        print("Sending test notification...")
        if test_notification():
            print("✓ Test notification sent successfully!")
        else:
            print("❌ Failed to send test notification.")
