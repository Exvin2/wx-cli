"""Modern design system for wx-cli - inspired by Claude, Codex, and Material Design."""

from __future__ import annotations

from typing import Any

from rich.console import Console, Group
from rich.text import Text


class DesignSystem:
    """Clean, modern design system with minimal borders and sophisticated colors."""

    # Color palette - sophisticated and minimal
    COLORS = {
        # Primary colors
        "primary": "#6B9FED",  # Soft blue
        "accent": "#A78BFA",  # Soft purple
        "success": "#6EE7B7",  # Soft green
        "warning": "#FCD34D",  # Soft yellow
        "danger": "#F87171",  # Soft red
        "info": "#67E8F9",  # Soft cyan
        # Text colors
        "text_primary": "#E5E7EB",  # Light gray for main text
        "text_secondary": "#9CA3AF",  # Medium gray for secondary
        "text_dim": "#6B7280",  # Dim gray for hints
        # Background accents
        "bg_subtle": "#1F2937",  # Subtle background
        "border": "#374151",  # Subtle border
    }

    # Rich color names (approximations)
    RICH_COLORS = {
        "primary": "bright_blue",
        "accent": "bright_magenta",
        "success": "bright_green",
        "warning": "bright_yellow",
        "danger": "bright_red",
        "info": "bright_cyan",
        "text_primary": "white",
        "text_secondary": "bright_black",
        "text_dim": "dim",
    }

    @classmethod
    def heading(cls, text: str, level: int = 1) -> Text:
        """Create a heading with appropriate styling.

        Args:
            text: Heading text
            level: Heading level (1-3)

        Returns:
            Styled Text object
        """
        if level == 1:
            return Text(text, style="bold bright_blue")
        elif level == 2:
            return Text(text, style="bold white")
        else:
            return Text(text, style="bright_black")

    @classmethod
    def subtext(cls, text: str) -> Text:
        """Create dimmed subtext.

        Args:
            text: Text content

        Returns:
            Styled Text object
        """
        return Text(text, style="dim")

    @classmethod
    def label(cls, text: str) -> Text:
        """Create a label for data.

        Args:
            text: Label text

        Returns:
            Styled Text object
        """
        return Text(text, style="bright_black")

    @classmethod
    def value(cls, text: str, color: str | None = None) -> Text:
        """Create a value display.

        Args:
            text: Value text
            color: Optional color override

        Returns:
            Styled Text object
        """
        style = color if color else "white"
        return Text(text, style=style)

    @classmethod
    def card_header(cls, title: str, subtitle: str | None = None) -> Text:
        """Create a card header with optional subtitle.

        Args:
            title: Card title
            subtitle: Optional subtitle

        Returns:
            Styled Text object
        """
        result = Text()
        result.append(title, style="bold bright_blue")
        if subtitle:
            result.append(f"\n{subtitle}", style="dim")
        return result

    @classmethod
    def separator(cls, width: int = 80, char: str = "─") -> Text:
        """Create a subtle separator line.

        Args:
            width: Line width
            char: Character to use

        Returns:
            Styled Text object
        """
        return Text(char * width, style="bright_black")

    @classmethod
    def bullet_point(cls, text: str, color: str = "bright_blue") -> Text:
        """Create a modern bullet point.

        Args:
            text: Bullet text
            color: Bullet color

        Returns:
            Styled Text object
        """
        result = Text()
        result.append("• ", style=color)
        result.append(text, style="white")
        return result

    @classmethod
    def badge(cls, text: str, variant: str = "default") -> Text:
        """Create a colored badge/tag.

        Args:
            text: Badge text
            variant: Badge variant (default, success, warning, danger)

        Returns:
            Styled Text object
        """
        colors = {
            "default": "bright_black",
            "success": "bright_green",
            "warning": "bright_yellow",
            "danger": "bright_red",
            "info": "bright_cyan",
        }
        color = colors.get(variant, "bright_black")
        return Text(f" {text} ", style=f"bold {color}")

    @classmethod
    def card(
        cls,
        title: str,
        content: list[tuple[str, str]],
        subtitle: str | None = None,
    ) -> Text:
        """Create a clean card layout without heavy borders.

        Args:
            title: Card title
            content: List of (label, value) tuples
            subtitle: Optional subtitle

        Returns:
            Styled Text object
        """
        result = Text()

        # Header
        result.append(title, style="bold bright_blue")
        if subtitle:
            result.append(f"  {subtitle}", style="dim")
        result.append("\n")

        # Content with clean layout
        for label, value in content:
            result.append(f"  {label}", style="bright_black")
            result.append(f" {value}\n", style="white")

        return result

    @classmethod
    def info_row(cls, label: str, value: str, indent: int = 0) -> Text:
        """Create a clean info row with label and value.

        Args:
            label: Row label
            value: Row value
            indent: Indentation level

        Returns:
            Styled Text object
        """
        result = Text()
        prefix = "  " * indent
        result.append(f"{prefix}{label}", style="bright_black")
        result.append(f" {value}", style="white")
        return result

    @classmethod
    def alert_badge(cls, severity: str) -> Text:
        """Create severity badge for alerts.

        Args:
            severity: Alert severity

        Returns:
            Styled Text object
        """
        severity_lower = severity.lower()
        styles = {
            "extreme": "bold bright_red",
            "severe": "bright_red",
            "moderate": "bright_yellow",
            "minor": "bright_cyan",
            "unknown": "dim",
        }
        style = styles.get(severity_lower, "white")
        return Text(severity.upper(), style=style)

    @classmethod
    def progress_indicator(cls, percentage: float, width: int = 30) -> Text:
        """Create a modern progress indicator.

        Args:
            percentage: Progress percentage (0-100)
            width: Indicator width

        Returns:
            Styled Text object
        """
        percentage = max(0, min(100, percentage))
        filled = int((percentage / 100) * width)
        empty = width - filled

        result = Text()

        # Determine color
        if percentage >= 70:
            color = "bright_red"
        elif percentage >= 40:
            color = "bright_yellow"
        else:
            color = "bright_green"

        # Modern thin bar
        result.append("▓" * filled, style=color)
        result.append("░" * empty, style="dim")
        result.append(f" {percentage:.0f}%", style="white")

        return result

    @classmethod
    def metric(cls, value: str, label: str, unit: str = "") -> Text:
        """Create a metric display.

        Args:
            value: Metric value
            label: Metric label
            unit: Optional unit

        Returns:
            Styled Text object
        """
        result = Text()
        result.append(f"{value}", style="bold bright_blue")
        if unit:
            result.append(f" {unit}", style="bright_black")
        result.append(f"\n{label}", style="dim")
        return result

    @classmethod
    def section_title(cls, text: str) -> Text:
        """Create a section title with subtle underline.

        Args:
            text: Section title

        Returns:
            Styled Text object
        """
        result = Text()
        result.append(text, style="bold white")
        result.append("\n")
        result.append("─" * len(text), style="bright_black")
        return result


def create_clean_card(title: str, items: list[tuple[str, Any]], console: Console | None = None) -> Group:
    """Create a clean card without borders.

    Args:
        title: Card title
        items: List of (label, value) tuples
        console: Optional console (unused, for compatibility)

    Returns:
        Rich Group containing card elements
    """
    ds = DesignSystem()
    elements = []

    # Title
    elements.append(ds.heading(title, level=2))
    elements.append(Text())  # Blank line

    # Items
    for label, value in items:
        elements.append(ds.info_row(label, str(value)))

    # Bottom spacing
    elements.append(Text())

    return Group(*elements)


def create_list_section(title: str, items: list[str], style: str = "bullet") -> Group:
    """Create a clean list section.

    Args:
        title: Section title
        items: List items
        style: List style (bullet or numbered)

    Returns:
        Rich Group containing list elements
    """
    ds = DesignSystem()
    elements = []

    # Title
    elements.append(ds.heading(title, level=2))
    elements.append(Text())

    # Items
    for i, item in enumerate(items, 1):
        if style == "numbered":
            text = Text()
            text.append(f"{i}. ", style="bright_blue")
            text.append(item, style="white")
            elements.append(text)
        else:
            elements.append(ds.bullet_point(item))

    elements.append(Text())

    return Group(*elements)
