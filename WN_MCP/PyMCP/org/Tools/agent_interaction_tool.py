"""
Agent Interaction Tool for MCP
Handles user interaction through Cursor/Copilot chat interface and Agent responses
"""

import json
import sys
import time
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass

from .log_tool import log_info as _log, log_debug, log_debug
from .params import get_mcp_params
from . import ue_interaction_tool

def _get_engine_status_display() -> str:
    """Get formatted engine status string for display in tool responses."""
    if ue_interaction_tool.LAST_STATUS_CHANGE:
        change = ue_interaction_tool.LAST_STATUS_CHANGE
        return f"\n---\n**Engine Status:** {change['status']}\n{change['message']}"
    else:
        connected = ue_interaction_tool.is_ue_connected()
        status = '🔗 CONNECTED' if connected else '❌ DISCONNECTED'
        return f"\n---\n**Engine Status:** {status}"

class DialogueType(Enum):
    """Types of dialogue interactions"""
    QUESTION = "question"           # Simple question with options
    CONFIRMATION = "confirmation"   # Yes/No confirmation
    SELECTION = "selection"         # Multiple choice selection
    INPUT = "input"                 # Free text input
    NOTIFICATION = "notification"   # Info/Warning display


@dataclass
class DialogueState:
    """Represents the state of a pending user interaction"""
    dialogue_id: str
    dialogue_type: DialogueType
    title: str
    message: str
    options: List[str]
    response: Optional[str] = None
    is_completed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for transmission"""
        return {
            'id': self.dialogue_id,
            'type': self.dialogue_type.value,
            'title': self.title,
            'message': self.message,
            'options': self.options,
            'is_completed': self.is_completed
        }


class ChatInteractionManager:
    """Manages dialogue states and user interactions"""
    
    def __init__(self):
        self._dialogues: Dict[str, DialogueState] = {}
        self._dialogue_counter = 0
    
    def create_question(self, title: str, message: str, options: List[str]) -> str:
        """Create a new question dialogue and return its ID"""
        self._dialogue_counter += 1
        dialogue_id = f"dlg_{self._dialogue_counter}"
        
        state = DialogueState(
            dialogue_id=dialogue_id,
            dialogue_type=DialogueType.QUESTION,
            title=title,
            message=message,
            options=options
        )
        
        self._dialogues[dialogue_id] = state
        _log(f'Created dialogue: {dialogue_id} - {title}')
        
        return dialogue_id
    
    def create_confirmation(self, title: str, message: str) -> str:
        """Create a confirmation dialogue (Yes/No)"""
        self._dialogue_counter += 1
        dialogue_id = f"dlg_{self._dialogue_counter}"
        
        state = DialogueState(
            dialogue_id=dialogue_id,
            dialogue_type=DialogueType.CONFIRMATION,
            title=title,
            message=message,
            options=['Yes', 'No']
        )
        
        self._dialogues[dialogue_id] = state
        _log(f'Created confirmation dialogue: {dialogue_id} - {title}')
        
        return dialogue_id
    
    def get_dialogue(self, dialogue_id: str) -> Optional[DialogueState]:
        """Get a dialogue state by ID"""
        return self._dialogues.get(dialogue_id)
    
    def set_response(self, dialogue_id: str, option_index: int) -> bool:
        """Set the user's response to a dialogue"""
        dialogue = self.get_dialogue(dialogue_id)
        if not dialogue:
            _log(f'Warning - Dialogue not found: {dialogue_id}')
            return False
        
        if option_index < 0 or option_index >= len(dialogue.options):
            _log(f'Warning - Invalid option index {option_index} for dialogue {dialogue_id}')
            return False
        
        dialogue.response = dialogue.options[option_index]
        dialogue.is_completed = True
        
        _log(f'Dialogue {dialogue_id} completed - Selected: {dialogue.response}')
        return True
    
    def get_response(self, dialogue_id: str) -> Optional[str]:
        """Get the user's response to a dialogue"""
        dialogue = self.get_dialogue(dialogue_id)
        if dialogue and dialogue.is_completed:
            return dialogue.response
        return None
    
    def is_completed(self, dialogue_id: str) -> bool:
        """Check if a dialogue has been completed"""
        dialogue = self.get_dialogue(dialogue_id)
        return dialogue.is_completed if dialogue else False
    
    def clear_dialogue(self, dialogue_id: str) -> bool:
        """Clear a completed dialogue"""
        if dialogue_id in self._dialogues:
            del self._dialogues[dialogue_id]
            _log(f'Cleared dialogue: {dialogue_id}')
            return True
        return False
    
    def ask_and_wait(self, title: str, message: str, options: List[str], 
                     timeout_seconds: float = 300.0) -> Optional[str]:
        """Ask a question and wait for user response (blocking).
        
        This is a convenience method for use within tool logic.
        It creates a question, displays it, and polls for the response.
        
        Args:
            title: Title of the question
            message: Question message
            options: List of options
            timeout_seconds: Maximum time to wait for response (default 5 minutes)
        
        Returns:
            The selected option string, or None if timeout or error
        """
        dialogue_id = self.create_question(title, message, options)
        
        # Log the question for display
        options_text = '\n'.join([f'{i+1}. {opt}' for i, opt in enumerate(options)])
        _log(f"User prompt: {title}\n{message}\n{options_text}\nDialogue ID: {dialogue_id}")
        
        start_time = time.time()
        poll_interval = 0.5  # Check every 500ms
        
        while time.time() - start_time < timeout_seconds:
            if self.is_completed(dialogue_id):
                response = self.get_response(dialogue_id)
                _log(f'User responded: {response}')
                return response
            
            time.sleep(poll_interval)
        
        _log(f'Warning - Dialogue {dialogue_id} timed out after {timeout_seconds} seconds')
        return None


# Global instance
_manager = ChatInteractionManager()

# Track if tools have been registered (per module import)
_agent_tools_registered = False


def register_tools(mcp) -> None:
    """Register Agent interaction tools with MCP server"""
    
    global _agent_tools_registered
    
    if _agent_tools_registered:
        log_debug('Agent interaction tools already registered, skipping')
        return
    
    
    @mcp.tool
    def show_notification() -> Dict[str, Any]:
        """Display a notification in the Cursor UI.
        
        Expects params (via get_mcp_params()):
            title: Title of the notification
            message: Notification message
            level: Notification level ('info', 'warning', 'error', 'success'), default='info'
        
        Returns:
            Confirmation that notification was displayed
        """
        try:
            params = get_mcp_params()
            title = params.get('title', 'Notification')
            message = params.get('message', '')
            level = params.get('level', 'info')
            
            # Determine icon based on level
            icons = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'error': '❌',
                'success': '✅'
            }
            icon = icons.get(level.lower(), 'ℹ️')
            
            # Include engine status in display
            display_text = f'{icon} **{title}**\n\n{message}'
            engine_status = _get_engine_status_display()
            display_text += engine_status
            
            return {
                'success': True,
                'title': title,
                'message': message,
                'level': level,
                'display': display_text
            }
        except Exception as e:
            _log(f'Tool: Error in show_notification: {e}')
            return {'success': False, 'error': str(e)}
    
    @mcp.tool
    def show_question() -> Dict[str, Any]:
        """Display a question with multiple choice options in the chat interface.
        
        Expects params (via get_mcp_params()):
            title: Title of the question
            message: Message/question text
            options: List of option strings to choose from
        
        Returns:
            Dictionary containing dialogue_id and instructions
        """
        try:
            params = get_mcp_params()
            title = params.get('title', 'Question')
            message = params.get('message', '')
            options = params.get('options', [])
            
            _log(f'Tool: show_question() called - title="{title}"')
            dialogue_id = _manager.create_question(title, message, options)
            _log(f'Tool: Created dialogue {dialogue_id}')
            
            # Format options for display
            options_text = '\n'.join(
                [f'{i+1}. {opt}' for i, opt in enumerate(options)]
            )
            
            display_message = f"""
**{title}**

{message}

{options_text}

---
*Use the `submit_response` tool with dialogue_id="{dialogue_id}" and selected_index to respond*
"""
            
            return {
                'success': True,
                'dialogue_id': dialogue_id,
                'type': 'question',
                'display': display_message,
                'message': message,
                'options': options
            }
        except Exception as e:
            _log(f'Tool: Error in show_question: {e}')
            return {'success': False, 'error': str(e)}
    
    @mcp.tool
    def show_confirmation() -> Dict[str, Any]:
        """Display a yes/no confirmation dialog.
        
        Expects params (via get_mcp_params()):
            title: Title of the confirmation
            message: Confirmation message
        
        Returns:
            Dictionary containing dialogue_id and instructions
        """
        try:
            params = get_mcp_params()
            title = params.get('title', 'Confirm')
            message = params.get('message', '')
            _log(f'Tool: show_confirmation() called - title="{title}"')
            dialogue_id = _manager.create_confirmation(title, message)
            _log(f'Tool: Created confirmation dialogue {dialogue_id}')
            
            display_message = f"""
**{title}**

{message}

1. Yes
2. No

---
*Use the `submit_response` tool with dialogue_id="{dialogue_id}" and selected_index to respond*
"""
            
            return {
                'success': True,
                'dialogue_id': dialogue_id,
                'type': 'confirmation',
                'display': display_message,
                'message': message
            }
        except Exception as e:
            _log(f'Tool: Error in show_confirmation: {e}')
            return {'success': False, 'error': str(e)}
    
    @mcp.tool
    def submit_response() -> Dict[str, Any]:
        """Submit the user's response to a dialogue.
        
        Expects params (via get_mcp_params()):
            dialogue_id: The ID of the dialogue to respond to
            selected_index: The 1-based index of the selected option
        
        Returns:
            Result of the submission
        """
        try:
            params = get_mcp_params()
            dialogue_id = params.get('dialogue_id')
            selected_index = params.get('selected_index')
            _log(f'Tool: submit_response() called - dialogue_id="{dialogue_id}", selected_index={selected_index}')
            dialogue = _manager.get_dialogue(dialogue_id)
            if not dialogue:
                _log(f'Tool: Dialogue not found: {dialogue_id}')
                return {
                    'success': False,
                    'error': f'Dialogue not found: {dialogue_id}'
                }
            
            # Convert to 0-based index
            option_index = selected_index - 1
            
            if not _manager.set_response(dialogue_id, option_index):
                _log(f'Tool: Invalid option index: {selected_index}')
                return {
                    'success': False,
                    'error': f'Invalid option index: {selected_index}'
                }
            
            selected_option = dialogue.options[option_index]
            _log(f'Tool: Response recorded - dialogue_id={dialogue_id}, selected={selected_option}')
            
            return {
                'success': True,
                'dialogue_id': dialogue_id,
                'selected': selected_option,
                'selected_index': selected_index,
                'message': f'✅ Response recorded: {selected_option}'
            }
        except Exception as e:
            _log(f'Tool: Error in submit_response: {e}')
            return {'success': False, 'error': str(e)}
    
    @mcp.tool
    def get_dialogue_response() -> Dict[str, Any]:
        """Get the response to a completed dialogue.
        
        Expects params (via get_mcp_params()):
            dialogue_id: The ID of the dialogue
        
        Returns:
            The user's response if available
        """
        try:
            params = get_mcp_params()
            dialogue_id = params.get('dialogue_id')
            _log(f'Tool: get_dialogue_response() called - dialogue_id="{dialogue_id}"')
            dialogue = _manager.get_dialogue(dialogue_id)
            if not dialogue:
                print(f'Tool: Dialogue not found: {dialogue_id}')
                return {
                    'success': False,
                    'error': f'Dialogue not found: {dialogue_id}'
                }
            
            if not dialogue.is_completed:
                _log(f'Tool: Dialogue pending user response: {dialogue_id}')
                return {
                    'success': False,
                    'completed': False,
                    'message': 'Dialogue pending user response'
                }
            
            _log(f'Tool: Dialogue completed - response={dialogue.response}')
            return {
                'success': True,
                'dialogue_id': dialogue_id,
                'completed': True,
                'response': dialogue.response,
                'type': dialogue.dialogue_type.value
            }
        except Exception as e:
            _log(f'Tool: Error in get_dialogue_response: {e}')
            return {'success': False, 'error': str(e)}
    
    @mcp.tool
    def clear_dialogue() -> Dict[str, Any]:
        """Clear a completed dialogue from memory.
        
        Expects params (via get_mcp_params()):
            dialogue_id: The ID of the dialogue to clear
        
        Returns:
            Confirmation of clearing
        """
        try:
            params = get_mcp_params()
            dialogue_id = params.get('dialogue_id')
            _log(f'Tool: clear_dialogue() called - dialogue_id="{dialogue_id}"')
            if _manager.clear_dialogue(dialogue_id):
                _log(f'Tool: Dialogue cleared successfully: {dialogue_id}')
                return {
                    'success': True,
                    'message': f'✅ Dialogue cleared: {dialogue_id}'
                }
            else:
                _log(f'Tool: Dialogue not found: {dialogue_id}')
                return {
                    'success': False,
                    'error': f'Dialogue not found: {dialogue_id}'
                }
        except Exception as e:
            _log(f'Tool: Error in clear_dialogue: {e}')
            return {'success': False, 'error': str(e)}
    
    @mcp.tool
    def get_engine_status_update() -> Dict[str, Any]:
        """Get the latest engine connection status change for Agent chat display.
        
        Returns the most recent connection/disconnection event with timestamp.
        Use this tool to display real-time engine status updates in the Agent chat area.
        """
        _log(f'Tool: get_engine_status_update() called')
        
        if ue_interaction_tool.LAST_STATUS_CHANGE:
            change = ue_interaction_tool.LAST_STATUS_CHANGE
            status_icon = '🔗' if change['connected'] else '❌'
            display_msg = f"{status_icon} **{change['status']}**\n\n{change['message']}\n\n*Last updated: {change['timestamp']}*"
            
            return {
                'success': True,
                'has_update': True,
                'status': change['status'],
                'connected': change['connected'],
                'timestamp': change['timestamp'],
                'message': change['message'],
                'display': display_msg
            }
        
        return {
            'success': True,
            'has_update': False,
            'display': '⚠️  No recent engine status changes. Use check_ue_connection() to get current status.'
        }
    
    _agent_tools_registered = True
    _log('Agent interaction tools registered')


def ask_user_sync(title: str, message: str, options: List[str], 
                  timeout_seconds: float = 300.0) -> Optional[str]:
    """Synchronous wrapper for asking user questions during tool execution.
    
    This function is designed to be called from within MCP tool logic.
    It displays a question in the chat and waits for the user's response.
    
    Args:
        title: Title/heading for the question
        message: Main question text
        options: List of string options for user to choose from
        timeout_seconds: How long to wait for response (default 5 minutes)
    
    Returns:
        The selected option text, or None if timeout/error
        
    Example:
        In a tool function:
        response = ask_user_sync(
            'Continue Operation?',
            'Are you sure you want to export all assets?',
            ['Yes, continue', 'No, cancel']
        )
        if response == 'Yes, continue':
            # do something
        elif response is None:
            return {'error': 'User did not respond'}
    """
    return _manager.ask_and_wait(title, message, options, timeout_seconds)


def ask_user_confirmation(title: str, message: str) -> Optional[bool]:
    """Convenience function for yes/no confirmation during tool execution.
    
    Args:
        title: Title for the confirmation
        message: Confirmation message
    
    Returns:
        True if user selected 'Yes', False if 'No', None if timeout
        
    Example:
        if ask_user_confirmation('Delete?', 'Are you sure?'):
            delete_files()
        else:
            print('Cancelled')
    """
    response = _manager.ask_and_wait(title, message, ['Yes', 'No'], timeout_seconds=300.0)
    if response == 'Yes':
        return True
    elif response == 'No':
        return False
    else:
        return None


"""
=== USAGE EXAMPLES FOR TOOL DEVELOPERS ===

In your tool files, you can import and use these functions:

from agent_interaction_tool import ask_user_sync, ask_user_confirmation

Example 1: Multiple choice question
-------
def my_tool(asset_name: str):
    action = ask_user_sync(
        'Select Action',
        f'What do you want to do with "{asset_name}"?',
        ['Export', 'Import', 'Modify', 'Delete', 'Cancel'],
        timeout_seconds=180
    )
    
    if action == 'Export':
        # Export logic
    elif action == 'Import':
        # Import logic
    # ...
    
Example 2: Confirmation with processing
-------
def delete_assets(asset_list: list):
    confirmed = ask_user_confirmation(
        'Confirm Delete',
        f'Delete {len(asset_list)} assets? This cannot be undone.'
    )
    
    if confirmed:
        # Perform deletion
        for asset in asset_list:
            delete_asset(asset)
        return {'success': True, 'deleted': len(asset_list)}
    elif confirmed is False:
        return {'success': False, 'reason': 'User cancelled'}
    else:  # None (timeout)
        return {'success': False, 'reason': 'No response from user'}

Example 3: Sequential questions
-------
def import_settings():
    # Ask first question
    source = ask_user_sync(
        'Select Source',
        'Where do you want to import from?',
        ['File', 'Preset', 'Default', 'Cancel']
    )
    
    if not source or source == 'Cancel':
        return {'cancelled': True}
    
    # Ask follow-up question
    overwrite = ask_user_confirmation(
        'Overwrite',
        'Overwrite existing settings?'
    )
    
    # Process based on answers
    if source == 'File' and overwrite:
        # Import from file with overwrite
        pass
    elif source == 'Preset':
        # Import preset
        pass
"""
