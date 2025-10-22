"""Tests for the conversational chat interface."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from wx.chat import ConversationMessage, ConversationSession


class TestConversationMessage:
    """Test ConversationMessage dataclass."""

    def test_create_message(self):
        """Test creating a conversation message."""
        msg = ConversationMessage(
            role="user",
            content="What's the weather like?",
            metadata={"location": "Seattle"},
        )
        assert msg.role == "user"
        assert msg.content == "What's the weather like?"
        assert msg.metadata["location"] == "Seattle"
        assert isinstance(msg.timestamp, datetime)

    def test_message_defaults(self):
        """Test message with default values."""
        msg = ConversationMessage(role="assistant", content="It's sunny!")
        assert msg.metadata == {}
        assert isinstance(msg.timestamp, datetime)


class TestConversationSession:
    """Test ConversationSession class."""

    def test_empty_session(self):
        """Test creating an empty session."""
        session = ConversationSession()
        assert len(session.messages) == 0
        assert session.location_context is None
        assert isinstance(session.session_start, datetime)

    def test_add_message(self):
        """Test adding messages to session."""
        session = ConversationSession()
        session.add_message("user", "What's the forecast?")
        assert len(session.messages) == 1
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "What's the forecast?"

    def test_add_multiple_messages(self):
        """Test adding multiple messages."""
        session = ConversationSession()
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")
        session.add_message("user", "What's the weather?")
        assert len(session.messages) == 3

    def test_location_context(self):
        """Test setting location context."""
        session = ConversationSession()
        session.location_context = {
            "resolved": "Seattle, WA",
            "lat": 47.6,
            "lon": -122.3,
        }
        assert session.location_context["resolved"] == "Seattle, WA"

    def test_get_context_summary_empty(self):
        """Test context summary for empty session."""
        session = ConversationSession()
        summary = session.get_context_summary()
        assert "start of a new conversation" in summary.lower()

    def test_get_context_summary_with_messages(self):
        """Test context summary with messages."""
        session = ConversationSession()
        session.add_message("user", "What's the weather?")
        session.add_message("assistant", "It's sunny!")
        summary = session.get_context_summary()
        assert "Number of exchanges: 1" in summary
        assert "Recent conversation:" in summary

    def test_get_context_summary_with_location(self):
        """Test context summary with location context."""
        session = ConversationSession()
        session.location_context = {"resolved": "Denver, CO"}
        session.add_message("user", "What's the forecast?")
        summary = session.get_context_summary()
        assert "Denver, CO" in summary

    def test_message_truncation_in_summary(self):
        """Test that long messages are truncated in context summary."""
        session = ConversationSession()
        long_message = "a" * 300
        session.add_message("user", long_message)
        summary = session.get_context_summary()
        # Message should be truncated with "..."
        assert "..." in summary
        assert len(summary) < len(long_message) + 200  # Much shorter than full message


class TestChatInterface:
    """Test ChatInterface class (integration tests with mocks)."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.offline = False
        settings.debug = False
        return settings

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator."""
        return MagicMock()

    @pytest.fixture
    def mock_console(self):
        """Create mock console."""
        return MagicMock()

    def test_enhance_query_with_context_basic(self, mock_settings, mock_orchestrator, mock_console):
        """Test query enhancement without context."""
        from wx.chat import ChatInterface

        chat = ChatInterface(mock_settings, mock_orchestrator, mock_console)
        enhanced = chat._enhance_query_with_context("What's the weather?")
        assert "What's the weather?" in enhanced

    def test_enhance_query_with_location(self, mock_settings, mock_orchestrator, mock_console):
        """Test query enhancement with location context."""
        from wx.chat import ChatInterface

        chat = ChatInterface(mock_settings, mock_orchestrator, mock_console)
        chat.session.location_context = {
            "resolved": "Seattle",
            "lat": 47.6,
            "lon": -122.3,
        }
        enhanced = chat._enhance_query_with_context("What's the forecast?")
        assert "Seattle" in enhanced
        assert "47.6" in enhanced
        assert "What's the forecast?" in enhanced

    def test_enhance_query_with_conversation_history(
        self, mock_settings, mock_orchestrator, mock_console
    ):
        """Test query enhancement with conversation history."""
        from wx.chat import ChatInterface

        chat = ChatInterface(mock_settings, mock_orchestrator, mock_console)
        chat.session.add_message("user", "Tell me about the weather")
        chat.session.add_message("assistant", "It's sunny")
        enhanced = chat._enhance_query_with_context("What about tomorrow?")
        assert "What about tomorrow?" in enhanced
        # Should not include conversation context for first exchange
        # Context only added after multiple messages
