"""
Agent Interaction Tool for Unreal MCP.
Handles user interaction through Cursor/Copilot chat interface and Agent responses.
"""
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("UnrealMCP.Tools.agent")


def _get_engine_status_display(get_connection: Callable) -> str:
    """Get formatted engine status string for display in tool responses."""
    conn = get_connection()
    if conn and getattr(conn, "connected", False):
        status = "🔗 CONNECTED"
    else:
        status = "❌ DISCONNECTED"
    return f"\n---\n**Engine Status:** {status}"


class DialogueType(Enum):
    """Types of dialogue interactions."""
    QUESTION = "question"
    CONFIRMATION = "confirmation"
    SELECTION = "selection"
    INPUT = "input"
    NOTIFICATION = "notification"


@dataclass
class DialogueState:
    """Represents the state of a pending user interaction."""
    dialogue_id: str
    dialogue_type: DialogueType
    title: str
    message: str
    options: List[str]
    response: Optional[str] = None
    is_completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for transmission."""
        return {
            "id": self.dialogue_id,
            "type": self.dialogue_type.value,
            "title": self.title,
            "message": self.message,
            "options": self.options,
            "is_completed": self.is_completed,
        }


class ChatInteractionManager:
    """Manages dialogue states and user interactions."""

    def __init__(self) -> None:
        self._dialogues: Dict[str, DialogueState] = {}
        self._dialogue_counter = 0

    def create_question(self, title: str, message: str, options: List[str]) -> str:
        """Create a new question dialogue and return its ID."""
        self._dialogue_counter += 1
        dialogue_id = f"dlg_{self._dialogue_counter}"
        state = DialogueState(
            dialogue_id=dialogue_id,
            dialogue_type=DialogueType.QUESTION,
            title=title,
            message=message,
            options=options,
        )
        self._dialogues[dialogue_id] = state
        logger.info("Created dialogue: %s - %s", dialogue_id, title)
        return dialogue_id

    def create_confirmation(self, title: str, message: str) -> str:
        """Create a confirmation dialogue (Yes/No)."""
        self._dialogue_counter += 1
        dialogue_id = f"dlg_{self._dialogue_counter}"
        state = DialogueState(
            dialogue_id=dialogue_id,
            dialogue_type=DialogueType.CONFIRMATION,
            title=title,
            message=message,
            options=["Yes", "No"],
        )
        self._dialogues[dialogue_id] = state
        logger.info("Created confirmation dialogue: %s - %s", dialogue_id, title)
        return dialogue_id

    def get_dialogue(self, dialogue_id: str) -> Optional[DialogueState]:
        """Get a dialogue state by ID."""
        return self._dialogues.get(dialogue_id)

    def set_response(self, dialogue_id: str, option_index: int) -> bool:
        """Set the user's response to a dialogue."""
        dialogue = self.get_dialogue(dialogue_id)
        if not dialogue:
            logger.warning("Dialogue not found: %s", dialogue_id)
            return False
        if option_index < 0 or option_index >= len(dialogue.options):
            logger.warning("Invalid option index %s for dialogue %s", option_index, dialogue_id)
            return False
        dialogue.response = dialogue.options[option_index]
        dialogue.is_completed = True
        logger.info("Dialogue %s completed - Selected: %s", dialogue_id, dialogue.response)
        return True

    def get_response(self, dialogue_id: str) -> Optional[str]:
        """Get the user's response to a dialogue."""
        dialogue = self.get_dialogue(dialogue_id)
        if dialogue and dialogue.is_completed:
            return dialogue.response
        return None

    def is_completed(self, dialogue_id: str) -> bool:
        """Check if a dialogue has been completed."""
        dialogue = self.get_dialogue(dialogue_id)
        return dialogue.is_completed if dialogue else False

    def clear_dialogue(self, dialogue_id: str) -> bool:
        """Clear a completed dialogue."""
        if dialogue_id in self._dialogues:
            del self._dialogues[dialogue_id]
            logger.info("Cleared dialogue: %s", dialogue_id)
            return True
        return False

    def ask_and_wait(
        self,
        title: str,
        message: str,
        options: List[str],
        timeout_seconds: float = 300.0,
    ) -> Optional[str]:
        """Ask a question and wait for user response (blocking)."""
        dialogue_id = self.create_question(title, message, options)
        options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
        logger.info("User prompt: %s\n%s\n%s\nDialogue ID: %s", title, message, options_text, dialogue_id)
        start_time = time.time()
        poll_interval = 0.5
        while time.time() - start_time < timeout_seconds:
            if self.is_completed(dialogue_id):
                response = self.get_response(dialogue_id)
                logger.info("User responded: %s", response)
                return response
            time.sleep(poll_interval)
        logger.warning("Dialogue %s timed out after %s seconds", dialogue_id, timeout_seconds)
        return None


_manager = ChatInteractionManager()


def register_tools(mcp: FastMCP, get_connection: Callable) -> None:
    """Register Agent interaction tools with MCP server."""
    def get_engine_status() -> str:
        return _get_engine_status_display(get_connection)

    @mcp.tool()
    def show_notification(title: str, message: str, level: str = "info") -> Dict[str, Any]:
        """Display a notification in the Cursor UI.

        Args:
            title: Title of the notification
            message: Notification message
            level: Notification level ('info', 'warning', 'error', 'success')

        Returns:
            Confirmation that notification was displayed
        """
        try:
            icons = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}
            icon = icons.get(level.lower(), "ℹ️")
            display_text = f"{icon} **{title}**\n\n{message}"
            display_text += get_engine_status()
            return {
                "success": True,
                "title": title,
                "message": message,
                "level": level,
                "display": display_text,
            }
        except Exception as e:
            logger.exception("Error in show_notification: %s", e)
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def show_question(title: str, message: str, options: List[str]) -> Dict[str, Any]:
        """Display a question with multiple choice options in the chat interface.

        Args:
            title: Title of the question
            message: Message/question text
            options: List of option strings to choose from

        Returns:
            Dictionary containing dialogue_id and instructions.
            Use submit_response tool with dialogue_id and selected_index to respond.
        """
        try:
            logger.info('show_question() called - title="%s"', title)
            dialogue_id = _manager.create_question(title, message, options)
            options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
            display_message = f"**{title}**\n\n{message}\n\n{options_text}\n\n---\n*Use the `submit_response` tool with dialogue_id=\"{dialogue_id}\" and selected_index to respond*"
            return {
                "success": True,
                "dialogue_id": dialogue_id,
                "type": "question",
                "display": display_message,
                "message": message,
                "options": options,
            }
        except Exception as e:
            logger.exception("Error in show_question: %s", e)
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def show_confirmation(title: str, message: str) -> Dict[str, Any]:
        """Display a yes/no confirmation dialog.

        Args:
            title: Title of the confirmation
            message: Confirmation message

        Returns:
            Dictionary containing dialogue_id and instructions.
            Use submit_response tool with dialogue_id and selected_index (1=Yes, 2=No).
        """
        try:
            logger.info('show_confirmation() called - title="%s"', title)
            dialogue_id = _manager.create_confirmation(title, message)
            display_message = f"**{title}**\n\n{message}\n\n1. Yes\n2. No\n\n---\n*Use the `submit_response` tool with dialogue_id=\"{dialogue_id}\" and selected_index to respond*"
            return {
                "success": True,
                "dialogue_id": dialogue_id,
                "type": "confirmation",
                "display": display_message,
                "message": message,
            }
        except Exception as e:
            logger.exception("Error in show_confirmation: %s", e)
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def submit_response(dialogue_id: str, selected_index: int) -> Dict[str, Any]:
        """Submit the user's response to a dialogue.

        Args:
            dialogue_id: The ID of the dialogue to respond to
            selected_index: The 1-based index of the selected option

        Returns:
            Result of the submission
        """
        try:
            logger.info('submit_response() - dialogue_id="%s", selected_index=%s', dialogue_id, selected_index)
            dialogue = _manager.get_dialogue(dialogue_id)
            if not dialogue:
                return {"success": False, "error": f"Dialogue not found: {dialogue_id}"}
            option_index = selected_index - 1
            if not _manager.set_response(dialogue_id, option_index):
                return {"success": False, "error": f"Invalid option index: {selected_index}"}
            selected_option = dialogue.options[option_index]
            return {
                "success": True,
                "dialogue_id": dialogue_id,
                "selected": selected_option,
                "selected_index": selected_index,
                "message": f"✅ Response recorded: {selected_option}",
            }
        except Exception as e:
            logger.exception("Error in submit_response: %s", e)
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def get_dialogue_response(dialogue_id: str) -> Dict[str, Any]:
        """Get the response to a completed dialogue.

        Args:
            dialogue_id: The ID of the dialogue

        Returns:
            The user's response if available
        """
        try:
            logger.info('get_dialogue_response() - dialogue_id="%s"', dialogue_id)
            dialogue = _manager.get_dialogue(dialogue_id)
            if not dialogue:
                return {"success": False, "error": f"Dialogue not found: {dialogue_id}"}
            if not dialogue.is_completed:
                return {
                    "success": False,
                    "completed": False,
                    "message": "Dialogue pending user response",
                }
            return {
                "success": True,
                "dialogue_id": dialogue_id,
                "completed": True,
                "response": dialogue.response,
                "type": dialogue.dialogue_type.value,
            }
        except Exception as e:
            logger.exception("Error in get_dialogue_response: %s", e)
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def clear_dialogue(dialogue_id: str) -> Dict[str, Any]:
        """Clear a completed dialogue from memory.

        Args:
            dialogue_id: The ID of the dialogue to clear

        Returns:
            Confirmation of clearing
        """
        try:
            logger.info('clear_dialogue() - dialogue_id="%s"', dialogue_id)
            if _manager.clear_dialogue(dialogue_id):
                return {"success": True, "message": f"✅ Dialogue cleared: {dialogue_id}"}
            return {"success": False, "error": f"Dialogue not found: {dialogue_id}"}
        except Exception as e:
            logger.exception("Error in clear_dialogue: %s", e)
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def get_engine_status_update() -> Dict[str, Any]:
        """Get the current Unreal Engine connection status for Agent chat display."""
        logger.debug("get_engine_status_update() called")
        conn = get_connection()
        connected = bool(conn and getattr(conn, "connected", False))
        status = "CONNECTED" if connected else "DISCONNECTED"
        icon = "🔗" if connected else "❌"
        display_msg = f"{icon} **{status}**\n\nEngine is {'connected' if connected else 'not connected'}."
        return {
            "success": True,
            "has_update": True,
            "status": status,
            "connected": connected,
            "message": display_msg,
            "display": display_msg,
        }

    logger.info("Agent interaction tools registered")
