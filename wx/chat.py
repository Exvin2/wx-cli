"""Interactive conversational AI bot interface for wx."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text

from .config import Settings
from .design import DesignSystem
from .orchestrator import Orchestrator


@dataclass(slots=True)
class ConversationMessage:
    """Represents a single message in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConversationSession:
    """Manages a conversational session with context history."""

    messages: list[ConversationMessage] = field(default_factory=list)
    location_context: dict[str, Any] | None = None
    session_start: datetime = field(default_factory=lambda: datetime.now(UTC))
    session_id: str | None = None

    def add_message(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a message to the conversation history."""
        msg = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(msg)

    def get_context_summary(self) -> str:
        """Generate a summary of the conversation context for the AI."""
        if not self.messages:
            return "This is the start of a new conversation."

        context_parts = [
            f"Conversation started at {self.session_start.isoformat()}",
            f"Number of exchanges: {len([m for m in self.messages if m.role == 'user'])}",
        ]

        if self.location_context:
            loc_name = self.location_context.get("resolved", "Unknown")
            context_parts.append(f"Current location context: {loc_name}")

        # Include last few exchanges for context
        recent_messages = self.messages[-6:]  # Last 3 exchanges
        if recent_messages:
            context_parts.append("\nRecent conversation:")
            for msg in recent_messages:
                role_label = "User" if msg.role == "user" else "Assistant"
                # Truncate long messages
                content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                context_parts.append(f"  {role_label}: {content}")

        return "\n".join(context_parts)

    def save_to_file(self, file_path: Path) -> bool:
        """Save conversation session to file.

        Args:
            file_path: Path to save session

        Returns:
            True if saved successfully
        """
        import os
        import tempfile

        try:
            session_data = {
                "session_id": self.session_id,
                "session_start": self.session_start.isoformat(),
                "location_context": self.location_context,
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "metadata": msg.metadata,
                    }
                    for msg in self.messages
                ],
            }

            # Atomic write
            fd, temp_path = tempfile.mkstemp(
                dir=file_path.parent, prefix=".wx_session_", suffix=".json"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(json.dumps(session_data, ensure_ascii=True, indent=2))

                os.chmod(temp_path, 0o600)
                os.replace(temp_path, file_path)
                return True
            except Exception:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
        except OSError:
            return False

    @classmethod
    def load_from_file(cls, file_path: Path) -> ConversationSession | None:
        """Load conversation session from file.

        Args:
            file_path: Path to session file

        Returns:
            ConversationSession or None if failed
        """
        if not file_path.exists():
            return None

        try:
            data = json.loads(file_path.read_text())

            session = cls()
            session.session_id = data.get("session_id")
            session.session_start = datetime.fromisoformat(data["session_start"])
            session.location_context = data.get("location_context")

            for msg_data in data.get("messages", []):
                msg = ConversationMessage(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    metadata=msg_data.get("metadata", {}),
                )
                session.messages.append(msg)

            return session
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return None


class ChatInterface:
    """Interactive chat interface for conversational weather queries."""

    def __init__(self, settings: Settings, orchestrator: Orchestrator, console: Console) -> None:
        self.settings = settings
        self.orchestrator = orchestrator
        self.console = console
        self.session = ConversationSession()

    def run(self, *, verbose: bool = False, json_mode: bool = False) -> None:
        """Start the interactive chat session."""
        self._show_welcome()

        # Try to load last session if it exists
        session_file = self.settings.state_file.parent / "last_session.json"
        if session_file.exists() and not self.settings.privacy_mode:
            loaded_session = ConversationSession.load_from_file(session_file)
            if loaded_session:
                self.session = loaded_session
                self.console.print(
                    f"[green]Resumed previous session ({len(loaded_session.messages)} messages)[/green]"
                )

        while True:
            try:
                user_input = Prompt.ask("\n[bright_blue]▶[/bright_blue]")

                # Handle special commands
                if user_input.lower() in {"/quit", "/exit", "/bye"}:
                    # Save session before quitting
                    if not self.settings.privacy_mode:
                        self.session.save_to_file(session_file)
                    self.console.print()
                    self.console.print(
                        Text("Thanks for using wx chat! Stay weather-aware.", style="bright_cyan")
                    )
                    self.console.print()
                    break

                if user_input.lower() in {"/help", "/?"}:
                    self._show_help()
                    continue

                if user_input.lower() == "/clear":
                    self.session = ConversationSession()
                    self.console.print("[green]Conversation history cleared.[/green]")
                    continue

                if user_input.lower().startswith("/location "):
                    location = user_input[10:].strip()
                    self._set_location_context(location)
                    continue

                if user_input.lower() == "/save":
                    if self._save_session():
                        self.console.print("[green]Session saved successfully.[/green]")
                    else:
                        self.console.print("[red]Failed to save session.[/red]")
                    continue

                if user_input.lower() == "/widget":
                    self._show_weather_widget()
                    continue

                if user_input.lower() == "/favorites":
                    self._show_favorites()
                    continue

                if not user_input.strip():
                    continue

                # Process the question
                self._handle_user_message(user_input, verbose=verbose, json_mode=json_mode)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Chat interrupted. Type /quit to exit.[/yellow]")
                continue
            except EOFError:
                break

    def _show_welcome(self) -> None:
        """Display welcome message with modern design."""
        ds = DesignSystem()

        self.console.print()
        self.console.print(ds.heading("wx AI Weather Bot", level=1))
        self.console.print()

        self.console.print(Text("I can help you with:", style="white"))
        self.console.print(ds.bullet_point("Real-time weather conditions from NWS and other sources"))
        self.console.print(ds.bullet_point("Weather forecasts for any location"))
        self.console.print(ds.bullet_point("Severe weather alerts and risk assessments"))
        self.console.print(ds.bullet_point("Natural language weather questions"))
        self.console.print()

        self.console.print(ds.heading("Commands", level=2))
        self.console.print(ds.info_row("/help", "Show available commands", indent=1))
        self.console.print(ds.info_row("/location", "Set your default location", indent=1))
        self.console.print(ds.info_row("/widget", "Show current weather", indent=1))
        self.console.print(ds.info_row("/favorites", "List saved locations", indent=1))
        self.console.print(ds.info_row("/save", "Save conversation", indent=1))
        self.console.print(ds.info_row("/clear", "Clear history", indent=1))
        self.console.print(ds.info_row("/quit", "Exit chat", indent=1))
        self.console.print()

        self.console.print(Text("Just ask me anything about the weather!", style="dim"))
        self.console.print(ds.separator())
        self.console.print()

    def _show_help(self) -> None:
        """Display help information with modern design."""
        ds = DesignSystem()

        self.console.print()
        self.console.print(ds.heading("Help", level=1))
        self.console.print()

        self.console.print(ds.heading("Available Commands", level=2))
        commands = [
            ("/location <place>", "Set default location context"),
            ("/widget", "Show current weather widget"),
            ("/favorites", "List saved favorite locations"),
            ("/save", "Save current conversation"),
            ("/clear", "Clear conversation history"),
            ("/help or /?", "Show this help message"),
            ("/quit or /exit", "Exit the chat"),
        ]
        for cmd, desc in commands:
            cmd_text = Text()
            cmd_text.append(f"  {cmd}", style="bright_cyan")
            cmd_text.append(f"  {desc}", style="white")
            self.console.print(cmd_text)
        self.console.print()

        self.console.print(ds.heading("Example Questions", level=2))
        examples = [
            "What's the weather like in Seattle?",
            "Are there any severe weather alerts in Texas?",
            "Should I worry about flooding in Miami today?",
            "What's the forecast for tomorrow in Denver?",
            "Tell me about current weather conditions nationwide",
            "Show me marine conditions for coastal areas",
            "What's the aviation weather at KDEN?",
        ]
        for example in examples:
            self.console.print(ds.bullet_point(example))
        self.console.print()

        self.console.print(
            Text(
                "You can ask questions in natural language - I'll fetch live data from NWS and other sources.",
                style="dim",
            )
        )
        self.console.print()

    def _set_location_context(self, location: str) -> None:
        """Set the location context for the conversation."""
        from .fetchers import get_point_context

        self.console.print(f"[dim]Looking up location: {location}...[/dim]")

        try:
            context = get_point_context(location, offline=self.settings.offline)
            if context:
                self.session.location_context = context
                resolved_name = context.get("resolved", location)
                lat = context.get("lat")
                lon = context.get("lon")
                self.console.print(
                    f"[green]✓ Location set to: {resolved_name} ({lat:.3f}, {lon:.3f})[/green]"
                )
                self.session.add_message(
                    "system",
                    f"Location context set to {resolved_name}",
                    metadata=context,
                )
            else:
                self.console.print(f"[red]✗ Could not find location: {location}[/red]")
        except Exception as e:  # noqa: BLE001
            self.console.print(f"[red]✗ Error looking up location: {e!s}[/red]")

    def _handle_user_message(
        self, user_input: str, *, verbose: bool = False, json_mode: bool = False
    ) -> None:
        """Process a user message and generate a response."""
        from .render import render_result

        # Add user message to history
        self.session.add_message("user", user_input)

        # Enhance the query with conversation context
        enhanced_query = self._enhance_query_with_context(user_input)

        # Show thinking indicator
        self.console.print("[dim]Thinking...[/dim]", end="")

        try:
            # Process the question through the orchestrator
            result = self.orchestrator.handle_question(enhanced_query, verbose=verbose)

            # Clear the thinking indicator
            self.console.print("\r" + " " * 20 + "\r", end="")

            # Add assistant response to history
            assistant_message = result.response.summary_text or result.response.bottom_line or "No response"
            self.session.add_message(
                "assistant",
                assistant_message,
                metadata={
                    "provider": result.response.provider,
                    "confidence": result.response.confidence,
                },
            )

            # Render the result
            if not json_mode:
                self.console.print()

            render_result(
                result,
                console=self.console,
                json_mode=json_mode,
                debug=self.settings.debug,
                verbose=verbose,
            )

        except Exception as e:  # noqa: BLE001
            self.console.print("\r" + " " * 20 + "\r", end="")
            self.console.print(f"[red]Error processing your question: {e!s}[/red]")

    def _enhance_query_with_context(self, user_query: str) -> str:
        """Enhance the user query with conversation context."""
        parts = []

        # Add conversation context
        context_summary = self.session.get_context_summary()
        if context_summary and len(self.session.messages) > 1:
            parts.append(f"[Conversation Context: {context_summary}]")

        # Add location context if set
        if self.session.location_context:
            loc_name = self.session.location_context.get("resolved", "Unknown")
            lat = self.session.location_context.get("lat")
            lon = self.session.location_context.get("lon")
            if lat and lon:
                parts.append(f"[User's location context: {loc_name} at {lat:.3f}, {lon:.3f}]")

        # Add the actual user query
        parts.append(user_query)

        return "\n".join(parts)

    def _save_session(self) -> bool:
        """Save current session to file."""
        if self.settings.privacy_mode:
            self.console.print("[yellow]Privacy mode is enabled. Cannot save session.[/yellow]")
            return False

        session_file = self.settings.state_file.parent / "last_session.json"
        return self.session.save_to_file(session_file)

    def _show_weather_widget(self) -> None:
        """Show current weather widget with modern design."""
        if not self.session.location_context:
            self.console.print(Text("No location set. Use /location <place> first.", style="bright_yellow"))
            return

        from .fetchers import get_quick_obs

        lat = self.session.location_context.get("lat")
        lon = self.session.location_context.get("lon")
        loc_name = self.session.location_context.get("resolved", "Unknown")

        if lat is None or lon is None:
            self.console.print(Text("Invalid location coordinates.", style="bright_red"))
            return

        self.console.print(Text(f"Fetching weather for {loc_name}...", style="dim"))

        obs = get_quick_obs(lat, lon, offline=self.settings.offline)

        if obs:
            ds = DesignSystem()

            self.console.print()
            self.console.print(ds.heading(f"Current Weather - {loc_name}", level=1))
            self.console.print()

            # Temperature
            temp_text = Text()
            temp_text.append("  ", style="")
            temp_text.append(f"{obs.get('temp', '?')}°C", style="bold bright_blue")
            temp_text.append(f"  feels like {obs.get('feels_like', '?')}°C", style="bright_black")
            self.console.print(temp_text)

            # Wind
            self.console.print(
                ds.info_row(
                    "Wind:",
                    f"{obs.get('wind', '?')} m/s (gusts: {obs.get('gust', '?')} m/s)",
                    indent=1,
                )
            )

            # Visibility
            self.console.print(ds.info_row("Visibility:", f"{obs.get('vis_km', '?')} km", indent=1))

            # Ceiling
            self.console.print(ds.info_row("Ceiling:", f"{obs.get('ceiling_m', '?')} m", indent=1))

            self.console.print()
        else:
            self.console.print(Text("No weather data available.", style="bright_yellow"))

    def _show_favorites(self) -> None:
        """Show list of favorite locations."""
        from .favorites import FavoritesManager

        favorites_mgr = FavoritesManager(self.settings.state_file.parent)
        favorites = favorites_mgr.list_favorites()

        if not favorites:
            self.console.print("[yellow]No favorite locations saved.[/yellow]")
            self.console.print("Add favorites using: /addfavorite <name>")
            return

        lines = ["[bold]Favorite Locations:[/bold]\n"]
        for fav in favorites:
            lines.append(f"  {fav.name}: {fav.display_name} ({fav.lat:.3f}, {fav.lon:.3f})")
            if fav.notes:
                lines.append(f"    Notes: {fav.notes}")

        self.console.print("\n".join(lines))


def start_chat_session(
    settings: Settings,
    orchestrator: Orchestrator,
    console: Console,
    *,
    verbose: bool = False,
    json_mode: bool = False,
) -> None:
    """Start an interactive chat session."""
    chat = ChatInterface(settings, orchestrator, console)
    chat.run(verbose=verbose, json_mode=json_mode)
