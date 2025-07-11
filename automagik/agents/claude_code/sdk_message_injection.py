"""SDK Message Injection for Claude Code execution.

This module handles injecting additional messages into ongoing Claude conversations.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SDKMessageInjector:
    """Handles message injection for Claude Code workflows."""
    
    def __init__(self):
        self.processed_messages = set()
    
    async def check_and_process_pending_messages(
        self, 
        workspace_path: Path, 
        run_id: str
    ) -> List[str]:
        """
        Check for pending injected messages and process them.
        
        Args:
            workspace_path: Path to the workflow workspace
            run_id: The workflow run ID
            
        Returns:
            List of messages to inject into the conversation
        """
        try:
            message_queue_file = workspace_path / ".pending_messages.json"
            
            if not message_queue_file.exists():
                return []
            
            # Read and parse pending messages
            try:
                with open(message_queue_file, 'r') as f:
                    pending_messages = json.load(f)
                
                if not isinstance(pending_messages, list):
                    return []
                    
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read pending messages file: {e}")
                return []
            
            # Filter unprocessed messages
            unprocessed_messages = [
                msg for msg in pending_messages 
                if not msg.get("processed", False) and 
                   msg.get("id") not in self.processed_messages
            ]
            
            if not unprocessed_messages:
                return []
            
            # Extract messages to inject
            messages_to_inject = []
            for msg in unprocessed_messages:
                messages_to_inject.append(msg["message"])
                # Mark as processed
                msg["processed"] = True
                msg["processed_at"] = datetime.utcnow().isoformat()
                msg["processed_by_run"] = run_id
                
                # Track processed message ID
                if "id" in msg:
                    self.processed_messages.add(msg["id"])
            
            # Write back the updated queue with processed flags
            try:
                with open(message_queue_file, 'w') as f:
                    json.dump(pending_messages, f, indent=2)
                
                logger.info(f"Processed {len(messages_to_inject)} injected messages for run {run_id}")
                
            except IOError as e:
                logger.error(f"Failed to update message queue file: {e}")
                # Still return the messages even if we can't update the file
            
            return messages_to_inject
            
        except Exception as e:
            logger.error(f"Error checking pending messages for run {run_id}: {e}")
            return []
    
    def build_enhanced_prompt_with_injected_messages(
        self,
        original_prompt: str,
        collected_messages: List[Any],
        injected_messages: List[str]
    ) -> str:
        """
        Build an enhanced prompt that includes conversation history and injected messages.
        
        Args:
            original_prompt: The original user prompt
            collected_messages: Messages collected so far in the conversation
            injected_messages: New messages to inject
            
        Returns:
            Enhanced prompt string
        """
        try:
            # Build conversation context
            context_parts = [f"Original request: {original_prompt}"]
            
            # Add conversation history summary
            if collected_messages:
                context_parts.append("\nConversation progress so far:")
                for i, msg in enumerate(collected_messages[-5:]):  # Last 5 messages for context
                    if hasattr(msg, 'content'):
                        content_preview = self._extract_content_preview(msg.content)
                        context_parts.append(f"- {content_preview}...")
            
            # Add injected messages
            if injected_messages:
                context_parts.append("\nAdditional instructions:")
                for msg in injected_messages:
                    context_parts.append(f"- {msg}")
            
            # Combine into enhanced prompt
            enhanced_prompt = "\n".join(context_parts)
            logger.info(f"Built enhanced prompt with {len(injected_messages)} injected messages")
            
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Error building enhanced prompt: {e}")
            # Fallback to original prompt
            return original_prompt
    
    def format_injection_notice(self, injected_msg: str, index: int) -> str:
        """Format an injected message as a notice for the conversation."""
        return f"""
━━━ NEW USER MESSAGE #{index+1} ━━━
{injected_msg}
━━━ END MESSAGE #{index+1} ━━━

Please acknowledge this additional request and incorporate it into your ongoing work.
"""
    
    def create_message_queue_file(self, workspace_path: Path) -> Path:
        """Create an empty message queue file if it doesn't exist."""
        message_queue_file = workspace_path / ".pending_messages.json"
        
        if not message_queue_file.exists():
            try:
                with open(message_queue_file, 'w') as f:
                    json.dump([], f)
                logger.info(f"Created message queue file: {message_queue_file}")
            except Exception as e:
                logger.error(f"Failed to create message queue file: {e}")
        
        return message_queue_file
    
    def add_message_to_queue(
        self, 
        workspace_path: Path, 
        message: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a new message to the pending queue."""
        try:
            message_queue_file = self.create_message_queue_file(workspace_path)
            
            # Read existing messages
            pending_messages = []
            if message_queue_file.exists():
                try:
                    with open(message_queue_file, 'r') as f:
                        pending_messages = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pending_messages = []
            
            # Create new message entry
            import uuid
            message_entry = {
                "id": str(uuid.uuid4()),
                "message": message,
                "created_at": datetime.utcnow().isoformat(),
                "processed": False,
                "metadata": metadata or {}
            }
            
            # Add to queue
            pending_messages.append(message_entry)
            
            # Write back
            with open(message_queue_file, 'w') as f:
                json.dump(pending_messages, f, indent=2)
            
            logger.info(f"Added message to queue: {message_entry['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add message to queue: {e}")
            return False
    
    def _extract_content_preview(self, content: Any, max_length: int = 200) -> str:
        """Extract a preview of message content."""
        if isinstance(content, str):
            return content[:max_length]
        elif isinstance(content, list):
            # Handle content blocks
            text_parts = []
            for block in content:
                if hasattr(block, 'text'):
                    text_parts.append(block.text)
            combined = " ".join(text_parts)
            return combined[:max_length]
        else:
            return str(content)[:max_length]