"""Weather notification system with custom alert rules."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.text import Text


@dataclass
class AlertRule:
    """Weather alert rule configuration."""

    name: str
    condition: str  # e.g., "temp < 32", "wind > 50", "aqi > 150"
    location: str
    enabled: bool = True
    last_triggered: datetime | None = None
    notification_method: str = "console"  # console, desktop, email


@dataclass
class WeatherNotification:
    """Weather notification message."""

    rule_name: str
    message: str
    severity: str  # info, warning, critical
    timestamp: datetime
    data: dict[str, Any]


class NotificationManager:
    """Manage weather notifications and alert rules."""

    def __init__(self, config_dir: Path):
        """Initialize notification manager.

        Args:
            config_dir: Directory for config files
        """
        self.config_dir = config_dir
        self.rules_file = config_dir / "alert_rules.json"
        self.history_file = config_dir / "notification_history.json"

        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.rules: list[AlertRule] = self._load_rules()

    def _load_rules(self) -> list[AlertRule]:
        """Load alert rules from file."""
        if not self.rules_file.exists():
            return []

        try:
            data = json.loads(self.rules_file.read_text())
            rules = []

            for rule_data in data:
                # Parse datetime
                if rule_data.get("last_triggered"):
                    rule_data["last_triggered"] = datetime.fromisoformat(
                        rule_data["last_triggered"]
                    )

                rules.append(AlertRule(**rule_data))

            return rules

        except (OSError, json.JSONDecodeError, TypeError):
            return []

    def _save_rules(self) -> bool:
        """Save alert rules to file."""
        try:
            rules_data = []
            for rule in self.rules:
                rule_dict = asdict(rule)
                if rule_dict["last_triggered"]:
                    rule_dict["last_triggered"] = rule_dict["last_triggered"].isoformat()
                rules_data.append(rule_dict)

            # Atomic write
            fd, temp_path = tempfile.mkstemp(
                dir=self.config_dir, prefix=".rules_", suffix=".json"
            )

            try:
                with os.fdopen(fd, "w") as f:
                    f.write(json.dumps(rules_data, indent=2))

                os.chmod(temp_path, 0o600)
                os.replace(temp_path, self.rules_file)
                return True

            except Exception:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise

        except OSError:
            return False

    def add_rule(
        self,
        name: str,
        condition: str,
        location: str,
        notification_method: str = "console",
    ) -> bool:
        """Add new alert rule.

        Args:
            name: Rule name
            condition: Alert condition
            location: Location to monitor
            notification_method: How to notify

        Returns:
            True if added successfully
        """
        rule = AlertRule(
            name=name,
            condition=condition,
            location=location,
            notification_method=notification_method,
        )

        self.rules.append(rule)
        return self._save_rules()

    def remove_rule(self, name: str) -> bool:
        """Remove alert rule by name.

        Args:
            name: Rule name

        Returns:
            True if removed
        """
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.name != name]

        if len(self.rules) < original_count:
            return self._save_rules()

        return False

    def toggle_rule(self, name: str) -> bool:
        """Enable/disable rule by name.

        Args:
            name: Rule name

        Returns:
            True if toggled
        """
        for rule in self.rules:
            if rule.name == name:
                rule.enabled = not rule.enabled
                return self._save_rules()

        return False

    def check_rules(self, weather_data: dict[str, Any]) -> list[WeatherNotification]:
        """Check all rules against current weather data.

        Args:
            weather_data: Current weather data

        Returns:
            List of triggered notifications
        """
        notifications = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            # Evaluate condition
            triggered = self._evaluate_condition(rule.condition, weather_data)

            if triggered:
                notification = WeatherNotification(
                    rule_name=rule.name,
                    message=f"Alert: {rule.condition} for {rule.location}",
                    severity=self._determine_severity(rule.condition, weather_data),
                    timestamp=datetime.now(UTC),
                    data=weather_data,
                )

                notifications.append(notification)
                rule.last_triggered = datetime.now(UTC)

        if notifications:
            self._save_rules()

        return notifications

    def _evaluate_condition(self, condition: str, data: dict[str, Any]) -> bool:
        """Evaluate alert condition against data.

        Args:
            condition: Condition string
            data: Weather data

        Returns:
            True if condition is met
        """
        # Simple condition parser
        # Format: "variable operator value"
        # Examples: "temp < 32", "wind > 50", "aqi > 150"

        try:
            parts = condition.split()
            if len(parts) != 3:
                return False

            variable, operator, threshold = parts
            threshold = float(threshold)

            # Get value from data
            value = data.get(variable)
            if value is None:
                return False

            value = float(value)

            # Evaluate
            if operator == "<":
                return value < threshold
            elif operator == "<=":
                return value <= threshold
            elif operator == ">":
                return value > threshold
            elif operator == ">=":
                return value >= threshold
            elif operator == "==":
                return value == threshold
            elif operator == "!=":
                return value != threshold

        except (ValueError, TypeError):
            return False

        return False

    def _determine_severity(self, condition: str, data: dict[str, Any]) -> str:
        """Determine notification severity.

        Args:
            condition: Condition string
            data: Weather data

        Returns:
            Severity level
        """
        # Simplified severity detection
        if "temp" in condition and "<" in condition:
            temp = data.get("temp", 50)
            if temp < 0:
                return "critical"
            elif temp < 32:
                return "warning"

        if "wind" in condition and ">" in condition:
            wind = data.get("wind", 0)
            if wind > 75:
                return "critical"
            elif wind > 50:
                return "warning"

        if "aqi" in condition and ">" in condition:
            aqi = data.get("aqi", 0)
            if aqi > 200:
                return "critical"
            elif aqi > 150:
                return "warning"

        return "info"

    def send_notification(self, notification: WeatherNotification) -> bool:
        """Send notification via configured method.

        Args:
            notification: Notification to send

        Returns:
            True if sent successfully
        """
        # Find rule
        rule = next((r for r in self.rules if r.name == notification.rule_name), None)
        if not rule:
            return False

        if rule.notification_method == "console":
            return self._send_console_notification(notification)
        elif rule.notification_method == "desktop":
            return self._send_desktop_notification(notification)
        elif rule.notification_method == "email":
            return self._send_email_notification(notification)

        return False

    def _send_console_notification(self, notification: WeatherNotification) -> bool:
        """Send console notification.

        Args:
            notification: Notification

        Returns:
            True if sent
        """
        console = Console()

        if notification.severity == "critical":
            style = "bold bright_red"
        elif notification.severity == "warning":
            style = "bright_yellow"
        else:
            style = "bright_cyan"

        console.print()
        console.print(Text(f"⚠️  {notification.message}", style=style))
        console.print(Text(f"Time: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}", style="dim"))
        console.print()

        return True

    def _send_desktop_notification(self, notification: WeatherNotification) -> bool:
        """Send desktop notification.

        Args:
            notification: Notification

        Returns:
            True if sent
        """
        # Would use system notification APIs
        # For now, just log
        return self._send_console_notification(notification)

    def _send_email_notification(self, notification: WeatherNotification) -> bool:
        """Send email notification.

        Args:
            notification: Notification

        Returns:
            True if sent
        """
        # Would use SMTP
        # For now, just log
        return self._send_console_notification(notification)


def display_notification_config(
    config_dir: Path, console: Console | None = None
) -> None:
    """Display current notification configuration.

    Args:
        config_dir: Config directory
        console: Rich console
    """
    from .design import DesignSystem

    if console is None:
        console = Console()

    ds = DesignSystem()
    manager = NotificationManager(config_dir)

    console.print()
    console.print(ds.heading(f"Weather Alert Rules ({len(manager.rules)})", level=1))
    console.print()

    if not manager.rules:
        console.print(Text("No alert rules configured", style="dim"))
        console.print()
        console.print(Text("Add a rule with: wx notify add <name> <condition> <location>", style="dim"))
        console.print(Text('Example: wx notify add freeze "temp < 32" Denver', style="dim"))
        console.print()
        return

    for rule in manager.rules:
        # Status indicator
        status = "✓" if rule.enabled else "✗"
        status_color = "bright_green" if rule.enabled else "bright_black"

        rule_text = Text()
        rule_text.append(f"{status} ", style=status_color)
        rule_text.append(rule.name, style="bold white")
        console.print(rule_text)

        console.print(ds.info_row("Condition:", rule.condition, indent=1))
        console.print(ds.info_row("Location:", rule.location, indent=1))
        console.print(ds.info_row("Method:", rule.notification_method, indent=1))

        if rule.last_triggered:
            console.print(
                ds.info_row(
                    "Last triggered:",
                    rule.last_triggered.strftime("%Y-%m-%d %H:%M:%S"),
                    indent=1,
                )
            )

        console.print()
