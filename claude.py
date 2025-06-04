#!/usr/bin/env python3
"""
Claude Chat CLI - Interactive streaming chat interface for automagik-agents Claude workflows
"""

import subprocess
import json
import sys
import os
import asyncio
import tempfile
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.columns import Columns
    from rich.align import Align
    from rich.table import Table
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.status import Status
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.syntax import Syntax
    
    # Advanced prompt with autocomplete
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import WordCompleter, Completer, Completion
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.shortcuts import CompleteStyle
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.key_binding import KeyBindings
except ImportError:
    print("❌ Missing required dependencies. Installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "rich", "prompt_toolkit"], check=True)
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.columns import Columns
    from rich.align import Align
    from rich.table import Table
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.status import Status
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.syntax import Syntax
    
    # Advanced prompt with autocomplete
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import WordCompleter, Completer, Completion
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.shortcuts import CompleteStyle
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.key_binding import KeyBindings

console = Console()

# Additional imports for interactive session selector
try:
    from prompt_toolkit.shortcuts import radiolist_dialog
    from prompt_toolkit.styles import Style
except ImportError:
    # Fallback if these specific imports aren't available
    radiolist_dialog = None
    Style = None

class WorkflowLogger:
    """Simple, human-readable logger for workflow activity"""
    
    def __init__(self, workflow_name: str, log_file: str = "logs/workflow_run.log"):
        self.workflow_name = workflow_name.upper()
        self.log_file = log_file
        
    def _log(self, level: str, message: str, details: str = ""):
        """Write a log entry"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"[{timestamp}] [{self.workflow_name}] [{level}]"
        
        log_line = f"{prefix} {message}"
        if details:
            log_line += f" | {details}"
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
                f.flush()  # Ensure immediate write
        except Exception as e:
            # Don't let logging errors break the main flow
            console.print(f"[dim red]⚠️ Logging error: {e}[/dim red]")
    
    def session_start(self, session_id: str, tools_count: int = 0):
        """Log session initialization"""
        details = f"Session: {session_id[:12]}... | Tools: {tools_count}"
        self._log("INIT", "Session started", details)
    
    def user_message(self, message: str):
        """Log user input"""
        preview = message[:100] + "..." if len(message) > 100 else message
        self._log("USER", f"Message sent", f"Content: {preview}")
    
    def assistant_thinking(self):
        """Log when assistant starts processing"""
        self._log("PROC", "Assistant processing request")
    
    def tool_call(self, tool_name: str, tool_id: str, input_preview: str = ""):
        """Log tool execution"""
        details = f"Tool: {tool_name} | ID: {tool_id[:8]}..."
        if input_preview:
            details += f" | Input: {input_preview[:50]}..."
        self._log("TOOL", "Tool called", details)
    
    def tool_result(self, tool_name: str, tool_id: str, success: bool = True, result_size: int = 0):
        """Log tool completion"""
        status = "SUCCESS" if success else "ERROR"
        details = f"Tool: {tool_name} | ID: {tool_id[:8]}... | Size: {result_size} chars"
        self._log("TOOL", f"Tool completed ({status})", details)
    
    def assistant_response(self, message_preview: str, tokens_used: dict = None):
        """Log assistant response"""
        details = f"Response: {message_preview[:80]}..."
        if tokens_used:
            input_tokens = tokens_used.get('input_tokens', 0)
            output_tokens = tokens_used.get('output_tokens', 0)
            details += f" | Tokens: {input_tokens}→{output_tokens}"
        self._log("RESP", "Assistant responded", details)
    
    def workflow_complete(self, success: bool = True, duration: float = 0):
        """Log workflow completion"""
        status = "SUCCESS" if success else "ERROR"
        details = f"Duration: {duration:.1f}s" if duration > 0 else ""
        self._log("DONE", f"Workflow completed ({status})", details)
    
    def error(self, error_msg: str, context: str = ""):
        """Log errors"""
        details = f"Error: {error_msg}"
        if context:
            details += f" | Context: {context}"
        self._log("ERROR", "Error occurred", details)
    
    def config_change(self, setting: str, old_value: str, new_value: str):
        """Log configuration changes"""
        details = f"{setting}: {old_value} → {new_value}"
        self._log("CONFIG", "Setting changed", details)

class ClaudeCommandCompleter(Completer):
    """Custom completer for Claude CLI commands with smart suggestions"""
    
    def __init__(self, chat_instance):
        self.chat = chat_instance
        self.commands = {
            '/help': 'Show available commands',
            '/session': 'Switch session (use Tab for options)',
            '/history': 'Show conversation history',
            '/clear': 'Clear conversation display',
            '/reset': 'Start new session',
            '/debug': 'Toggle debug mode',
            '/config': 'Show current configuration',
            '/workflows': 'List available workflows',
            '/max-turns': 'Set max conversation turns (1-100)',
            '/workflow': 'Switch to different workflow',
            '/quit': 'Exit the application'
        }
    
    def get_completions(self, document, complete_event):
        text = document.text
        
        # If we're completing a command
        if text.startswith('/'):
            # Get the word being completed
            word = text.split()[-1] if text.split() else text
            
            # For /workflow command, suggest available workflows
            if text.startswith('/workflow '):
                workflow_part = text[len('/workflow '):]
                for workflow_name in self.chat.available_workflows.keys():
                    if workflow_name.startswith(workflow_part):
                        yield Completion(
                            workflow_name, 
                            start_position=-len(workflow_part),
                            display=f"{workflow_name} - {self.chat.available_workflows[workflow_name]['description']}"
                        )
            
            # For /session command, suggest available sessions
            elif text.startswith('/session '):
                session_part = text[len('/session '):]
                
                # Add "new" option
                if "new".startswith(session_part.lower()):
                    yield Completion(
                        "new",
                        start_position=-len(session_part),
                        display="new - Start a fresh conversation"
                    )
                
                # Add saved sessions
                for session_id, session_data in self.chat.saved_sessions.items():
                    session_name = session_data.get('name', 'Unnamed').lower()
                    workflow = session_data.get('workflow', 'unknown')
                    msg_count = session_data.get('conversation_length', 0)
                    
                    # Format last message date
                    last_msg_date = session_data.get('last_message_date', session_data.get('last_used', ''))
                    try:
                        if last_msg_date:
                            dt = datetime.fromisoformat(last_msg_date.replace('Z', '+00:00'))
                            date_str = dt.strftime("%m/%d %H:%M")
                        else:
                            date_str = "Unknown"
                    except:
                        date_str = "Unknown"
                    
                    # Match by session name or workflow
                    if (session_name.startswith(session_part.lower()) or 
                        workflow.lower().startswith(session_part.lower())):
                        display_name = session_data.get('name', 'Unnamed')
                        current_indicator = "(CURRENT) " if session_id == self.chat.session_id else ""
                        
                        yield Completion(
                            session_id,
                            start_position=-len(session_part),
                            display=f"{current_indicator}{display_name} - {workflow.upper()} | {msg_count} msgs | {date_str}"
                        )
            
            # For /max-turns command, suggest numbers
            elif text.startswith('/max-turns '):
                num_part = text[len('/max-turns '):]
                for num in ['1', '2', '3', '5', '10', '20', '30', '40', '50', '60', '70', '80', '90', '100']:
                    if num.startswith(num_part):
                        yield Completion(
                            num,
                            start_position=-len(num_part),
                            display=f"{num} turns"
                        )
            

            
            # Complete command names
            else:
                for command, description in self.commands.items():
                    if command.startswith(text):
                        yield Completion(
                            command,
                            start_position=-len(text),
                            display=f"{command} - {description}"
                        )

class ClaudeStreamingChat:
    """Modern streaming chat interface for Claude CLI"""
    
    def __init__(self):
        self.session_id: Optional[str] = None
        self.conversation_history: List[tuple] = []
        self.active_tools: Dict[str, Dict] = {}
        self.current_message = ""
        
        # Configuration settings with defaults
        self.max_turns = 3
        self.current_workflow = "implement"
        self.available_workflows = {}
        
        # Settings persistence
        self.settings_file = os.path.expanduser("~/.claude_cli_settings.json")
        self.sessions_file = os.path.expanduser("~/.claude_cli_sessions.json")
        self.sessions_dir = os.path.expanduser("~/.claude_cli_sessions")
        self.saved_sessions = {}
        self.command_history = []
        
        # Create sessions directory
        os.makedirs(self.sessions_dir, exist_ok=True)
        
        # Create logs directory for workflow logging
        os.makedirs("logs", exist_ok=True)
        
        # Setup components
        self.check_dependencies()
        self.discover_workflows()
        self.load_settings()
        self.load_sessions()
        
        # Initialize autocomplete with persistent history
        self.completer = ClaudeCommandCompleter(self)
        self.history = InMemoryHistory()
        self.load_command_history()
        
        # Initialize logger
        self.logger = WorkflowLogger(self.current_workflow)
        self.workflow_start_time = None
        
        # Auto-load last session
        self.auto_load_last_session()
    
    def check_dependencies(self):
        """Check if required files exist"""
        required_files = [
            ".mcp.json",
            "allowed_tools.json", 
            "src/agents/claude_code/workflows/implement/prompt.md"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            console.print(Panel(
                f"❌ Missing required files:\n" + "\n".join(f"• {f}" for f in missing_files),
                title="[red]Configuration Error[/red]",
                border_style="red"
            ))
            console.print("\n[yellow]Make sure you're running from the project root directory.[/yellow]")
            console.print("\n[yellow]If files were recently deleted, try:[/yellow]")
            console.print("  [cyan]git status[/cyan] - Check what was deleted")
            console.print("  [cyan]git restore <file>[/cyan] - Restore deleted files")
            console.print("  [cyan]git checkout HEAD -- <file>[/cyan] - Force restore from last commit")
            sys.exit(1)
    
    def discover_workflows(self):
        """Discover available workflows in the workflows directory"""
        workflows_dir = "src/agents/claude_code/workflows"
        self.available_workflows = {}
        
        if os.path.exists(workflows_dir):
            for item in os.listdir(workflows_dir):
                workflow_path = os.path.join(workflows_dir, item)
                prompt_file = os.path.join(workflow_path, "prompt.md")
                
                if os.path.isdir(workflow_path) and os.path.exists(prompt_file):
                    # Read the first line for description
                    try:
                        with open(prompt_file, 'r', encoding='utf-8') as f:
                            first_line = f.readline().strip()
                            # Remove markdown header if present
                            description = first_line.lstrip('#').strip() if first_line.startswith('#') else item.title()
                    except:
                        description = item.title()
                    
                    self.available_workflows[item] = {
                        "path": prompt_file,
                        "description": description
                    }
        
        # Ensure current workflow exists
        if self.current_workflow not in self.available_workflows:
            if self.available_workflows:
                self.current_workflow = list(self.available_workflows.keys())[0]
            else:
                console.print("[red]⚠️ No workflows found in src/agents/claude_code/workflows/[/red]")
    
    def load_settings(self):
        """Load settings from JSON file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.max_turns = settings.get('max_turns', 3)
                    saved_workflow = settings.get('current_workflow', 'implement')
                    self.command_history = settings.get('command_history', [])
                    
                    # Validate saved workflow exists
                    if saved_workflow in self.available_workflows:
                        self.current_workflow = saved_workflow
                    
                    console.print(f"[dim]✅ Settings loaded from {self.settings_file}[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not load settings: {e}[/yellow]")
    
    def save_settings(self):
        """Save current settings to JSON file"""
        try:
            settings = {
                'max_turns': self.max_turns,
                'current_workflow': self.current_workflow,
                'command_history': self.command_history[-100:],  # Keep last 100 commands
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
                
            console.print(f"[dim]💾 Settings saved to {self.settings_file}[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not save settings: {e}[/yellow]")
    
    def load_sessions(self):
        """Load saved sessions from JSON file"""
        try:
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r') as f:
                    self.saved_sessions = json.load(f)
                    console.print(f"[dim]✅ {len(self.saved_sessions)} saved sessions loaded[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not load sessions: {e}[/yellow]")
            self.saved_sessions = {}
    
    def save_sessions(self):
        """Save sessions to JSON file"""
        try:
            with open(self.sessions_file, 'w') as f:
                json.dump(self.saved_sessions, f, indent=2)
                
            console.print(f"[dim]💾 Sessions saved to {self.sessions_file}[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not save sessions: {e}[/yellow]")
    
    def load_command_history(self):
        """Load command history into prompt_toolkit history"""
        try:
            for command in self.command_history:
                self.history.append_string(command)
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not load command history: {e}[/yellow]")
    
    def add_command_to_history(self, command: str):
        """Add command to persistent history"""
        if command and not command.startswith('/'):  # Don't save slash commands in history
            self.command_history.append(command)
            self.history.append_string(command)
            
            # Keep history manageable
            if len(self.command_history) > 100:
                self.command_history = self.command_history[-100:]
    
    def auto_save_session(self):
        """Automatically save current session"""
        if not self.session_id:
            return
            
        try:
            # Generate session name based on workflow and conversation
            session_name = f"{self.current_workflow.title()} Session"
            if self.conversation_history:
                # Use first user message as hint for name
                first_message = ""
                for role, content in self.conversation_history:
                    if role == "user":
                        first_message = content[:30].replace('\n', ' ').strip()
                        break
                if first_message:
                    session_name = f"{self.current_workflow.title()}: {first_message}..."
            
            session_data = {
                'session_id': self.session_id,
                'name': session_name,
                'workflow': self.current_workflow,
                'max_turns': self.max_turns,
                'created': self.saved_sessions.get(self.session_id, {}).get('created', datetime.now().isoformat()),
                'conversation_length': len(self.conversation_history),
                'last_used': datetime.now().isoformat(),
                'last_message_date': datetime.now().isoformat()
            }
            
            # Save session metadata
            self.saved_sessions[self.session_id] = session_data
            self.save_sessions()
            
            # Save conversation history to individual session file
            session_file = os.path.join(self.sessions_dir, f"{self.session_id}.json")
            conversation_data = {
                'session_id': self.session_id,
                'name': session_name,
                'workflow': self.current_workflow,
                'conversation_history': self.conversation_history,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(session_file, 'w') as f:
                json.dump(conversation_data, f, indent=2)
                
        except Exception as e:
            # Don't break the flow if auto-save fails
            console.print(f"[dim yellow]⚠️ Auto-save failed: {e}[/dim yellow]")
            

    def auto_load_last_session(self):
        """Automatically load the most recently used session"""
        if not self.saved_sessions:
            return False
            
        # Find most recent session
        most_recent = None
        most_recent_time = ""
        
        for session_id, session_data in self.saved_sessions.items():
            last_used = session_data.get('last_used', '')
            if last_used > most_recent_time:
                most_recent_time = last_used
                most_recent = session_id
                
        if most_recent:
            return self.resume_session_by_id(most_recent)
        return False
    
    def resume_session_by_id(self, session_id: str) -> bool:
        """Resume a session by session ID"""
        target_session = self.saved_sessions.get(session_id)
        
        if not target_session:
            return False
        
        try:
            # Update current session info
            self.session_id = session_id
            
            # Update configuration to match saved session
            self.current_workflow = target_session.get('workflow', self.current_workflow)
            self.max_turns = target_session.get('max_turns', self.max_turns)
            
            # Update last used timestamp
            target_session['last_used'] = datetime.now().isoformat()
            self.saved_sessions[session_id] = target_session
            self.save_sessions()
            
            # Reinitialize logger with correct workflow
            self.logger = WorkflowLogger(self.current_workflow)
            
            # Load conversation history from session file
            session_file = os.path.join(self.sessions_dir, f"{session_id}.json")
            
            if os.path.exists(session_file):
                try:
                    with open(session_file, 'r') as f:
                        conversation_data = json.load(f)
                        self.conversation_history = conversation_data.get('conversation_history', [])
                except Exception as e:
                    console.print(f"[dim yellow]⚠️ Could not load conversation history: {e}[/dim yellow]")
                    self.conversation_history = []
            else:
                self.conversation_history = []
            
            return True
            
        except Exception as e:
            console.print(f"[dim yellow]⚠️ Could not resume session: {e}[/dim yellow]")
            return False
    
    def show_header(self):
        """Display the application header"""
        header_text = Text()
        header_text.append("🤖 Claude Chat CLI", style="bold blue")
        header_text.append(" | ", style="dim")
        
        # Show current workflow
        workflow_display = self.current_workflow.upper()
        header_text.append(f"{workflow_display} Workflow", style="bold cyan")
        
        # Show max turns
        header_text.append(f" | Max Turns: {self.max_turns}", style="dim yellow")
        
        # Show session if active
        if self.session_id:
            header_text.append(f" | Session: {self.session_id[:8]}...", style="dim green")
        
        header_panel = Panel(
            Align.center(header_text),
            style="blue"
        )
        
        console.print(header_panel)
    
    def build_command(self, message: str, resume_session: bool = False) -> List[str]:
        """Build the claude command"""
        cmd = ["claude", "-p"]
        
        if resume_session and self.session_id:
            cmd.extend(["-r", self.session_id])
        
        # Get current workflow prompt path
        workflow_prompt = "src/agents/claude_code/workflows/implement/prompt.md"  # fallback
        if self.current_workflow in self.available_workflows:
            workflow_prompt = self.available_workflows[self.current_workflow]["path"]
        
        # Pre-process allowed tools by reading file directly
        try:
            with open("allowed_tools.json", "r") as f:
                tools_data = json.load(f)
                allowed_tools = ",".join(tools_data) if isinstance(tools_data, list) else ""
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not read allowed_tools.json: {e}[/yellow]")
            allowed_tools = ""
        
        # Pre-process system prompt by reading file directly
        try:
            with open(workflow_prompt, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not read workflow prompt: {e}[/yellow]")
            system_prompt = "You are Claude, a helpful AI assistant."
        
        cmd.extend([
            "--model", "sonnet",
            "--output-format", "stream-json",
            "--max-turns", str(self.max_turns),
            "--mcp-config", ".mcp.json",
            "--allowedTools", allowed_tools,
            "--verbose",
            "--system-prompt", system_prompt,
            message
        ])
        
        return cmd
    
    def display_tool_call(self, tool_name: str, tool_input: Dict, tool_id: str):
        """Display a tool call in modern chat style"""
        # Create input preview for logging
        input_preview = ""
        if tool_input:
            if isinstance(tool_input, dict):
                # Get first few key-value pairs as preview
                preview_items = list(tool_input.items())[:2]
                input_preview = ", ".join(f"{k}={v}" for k, v in preview_items)
            else:
                input_preview = str(tool_input)[:50]
        
        # Log tool call
        self.logger.tool_call(tool_name, tool_id, input_preview)
        
        # Create tool display
        tool_content = f"🔧 **{tool_name}**\n\n"
        
        # Format tool input nicely
        if tool_input:
            # Handle different input types
            if isinstance(tool_input, dict):
                for key, value in tool_input.items():
                    if isinstance(value, str) and len(value) > 100:
                        tool_content += f"**{key}:** `{value[:100]}...`\n"
                    else:
                        tool_content += f"**{key}:** `{value}`\n"
            else:
                tool_content += f"**Input:** `{tool_input}`"
        
        # Store tool info for later result display
        self.active_tools[tool_id] = {
            "name": tool_name,
            "input": tool_input,
            "timestamp": datetime.now()
        }
        
        console.print(Panel(
            Markdown(tool_content),
            title=f"[yellow]⚙️ Tool Call #{len(self.active_tools)}[/yellow]",
            border_style="yellow",
            padding=(1, 2),
            subtitle=f"[dim]{tool_id[:8]}...[/dim]"
        ))
    
    def display_tool_result(self, tool_id: str, result: Any):
        """Display tool result in modern chat style"""
        tool_info = self.active_tools.get(tool_id, {})
        tool_name = tool_info.get("name", "unknown")
        
        # Log tool result
        result_size = len(str(result)) if result else 0
        success = result is not None and str(result) != "error"
        self.logger.tool_result(tool_name, tool_id, success, result_size)
        
        # Format result based on content type
        if isinstance(result, str):
            if len(result) > 500:
                # Large text result - show preview
                result_text = f"```\n{result[:500]}...\n```\n\n[dim]({len(result)} characters total)[/dim]"
            elif result.strip().startswith('{') or result.strip().startswith('['):
                # JSON result - format as code
                try:
                    parsed = json.loads(result)
                    formatted = json.dumps(parsed, indent=2)
                    result_text = f"```json\n{formatted}\n```"
                except:
                    result_text = f"```\n{result}\n```"
            else:
                result_text = f"```\n{result}\n```"
        else:
            result_text = f"```\n{str(result)}\n```"
        
        console.print(Panel(
            Markdown(result_text),
            title=f"[green]✅ {tool_name} Result[/green]",
            border_style="green",
            padding=(1, 2),
            subtitle=f"[dim]{tool_id[:8]}...[/dim]"
        ))
    
    def execute_command_streaming(self, message: str) -> Dict[str, Any]:
        """Execute Claude command with real-time streaming"""
        cmd = self.build_command(message, resume_session=bool(self.session_id))
        
        # Log user message and start timing
        self.logger.user_message(message)
        if not self.workflow_start_time:
            self.workflow_start_time = datetime.now()
        
        console.print()
        
        try:
            # Start process with streaming - use list form to avoid shell escaping issues
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Initialize streaming state
            self.current_message = ""
            session_started = False
            tool_calls_active = False
            parsed_data = []
            
            # Reset thinking logged flag for this message
            if hasattr(self, '_thinking_logged'):
                delattr(self, '_thinking_logged')
            
            with Live(console=console, auto_refresh=True, transient=False) as live:
                # Initial status
                live.update(Panel(
                    "[cyan]🤖 Claude is thinking...[/cyan]",
                    title="[blue]Processing[/blue]",
                    border_style="blue"
                ))
                
                # Read stdout line by line
                for line in iter(process.stdout.readline, ''):
                    if not line:
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        parsed_data.append(data)
                        
                        # Handle different message types with beautiful displays
                        if data.get("type") == "system" and data.get("subtype") == "init":
                            self.session_id = data.get("session_id")
                            session_started = True
                            
                            # Log session start
                            tools_count = len(data.get('tools', []))
                            self.logger.session_start(self.session_id, tools_count)
                            
                            # Show session info beautifully
                            session_info = Table.grid(padding=1)
                            session_info.add_column(style="dim")
                            session_info.add_column(style="green")
                            session_info.add_row("Session ID:", f"{self.session_id[:12]}...")
                            session_info.add_row("Tools:", f"{tools_count} available")
                            
                            live.update(Panel(
                                session_info,
                                title="[green]✅ Connected[/green]",
                                border_style="green"
                            ))
                            
                        elif data.get("type") == "assistant" and "message" in data:
                            msg_data = data["message"]
                            
                            # Process content
                            if "content" in msg_data:
                                for content in msg_data["content"]:
                                    if content.get("type") == "text":
                                        text = content.get("text", "")
                                        self.current_message += text
                                        
                                        # Log assistant thinking on first text
                                        if not hasattr(self, '_thinking_logged'):
                                            self.logger.assistant_thinking()
                                            self._thinking_logged = True
                                        
                                        # Real-time text streaming
                                        if self.current_message.strip():
                                            live.update(Panel(
                                                Markdown(self.current_message),
                                                title=f"[bold blue]🤖 Claude ({self.current_workflow.upper()})[/bold blue]",
                                                border_style="blue",
                                                padding=(1, 2)
                                            ))
                                    
                                    elif content.get("type") == "tool_use":
                                        # Display tool call immediately
                                        tool_calls_active = True
                                        live.stop()  # Stop live to show tool call
                                        
                                        self.display_tool_call(
                                            content.get("name", "unknown"),
                                            content.get("input", {}),
                                            content.get("id", "")
                                        )
                                        
                                        live.start()  # Resume live display
                                        live.update(Panel(
                                            "[yellow]⏳ Executing tools...[/yellow]",
                                            title="[yellow]Tool Execution[/yellow]",
                                            border_style="yellow"
                                        ))
                            
                            # Handle stop reasons
                            stop_reason = msg_data.get("stop_reason")
                            if stop_reason == "tool_use":
                                live.update(Panel(
                                    "[yellow]⚙️ Running tools...[/yellow]",
                                    title="[yellow]Tool Execution[/yellow]",
                                    border_style="yellow"
                                ))
                        
                        elif data.get("type") == "user" and "message" in data:
                            # Tool results
                            msg_data = data["message"]
                            if "content" in msg_data:
                                for content in msg_data["content"]:
                                    if content.get("type") == "tool_result":
                                        live.stop()  # Stop live to show tool result
                                        
                                        self.display_tool_result(
                                            content.get("tool_use_id", ""),
                                            content.get("content", "")
                                        )
                                        
                                        live.start()  # Resume
                                        live.update(Panel(
                                            "[cyan]🤖 Processing tool results...[/cyan]",
                                            title="[blue]Thinking[/blue]",
                                            border_style="blue"
                                        ))
                    
                    except json.JSONDecodeError:
                        # Handle non-JSON output
                        if line.strip():
                            self.current_message += line + "\n"
                
                # Final message display
                if self.current_message.strip():
                    live.update(Panel(
                        Markdown(self.current_message),
                        title=f"[bold blue]🤖 Claude ({self.current_workflow.upper()})[/bold blue]",
                        border_style="blue",
                        padding=(1, 2)
                    ))
            
            # Wait for process completion
            process.wait()
            
            # Show any errors
            if process.returncode != 0:
                stderr_output = process.stderr.read()
                if stderr_output:
                    console.print(Panel(
                        stderr_output,
                        title="[red]⚠️ Errors[/red]",
                        border_style="red"
                    ))
            
            return self.process_response(parsed_data)
            
        except Exception as e:
            # Log error
            self.logger.error(str(e), "execute_command_streaming")
            
            console.print(Panel(
                f"❌ Execution error: {str(e)}",
                title="[red]Error[/red]",
                border_style="red"
            ))
            return {}
    
    def process_response(self, data: List[Dict]) -> Dict[str, Any]:
        """Process Claude's response data"""
        if not data:
            return {}
        
        # Extract useful information
        assistant_message = None
        session_id = None
        usage_info = None
        
        for item in data:
            if item.get("type") == "assistant" and "message" in item:
                assistant_message = item["message"]
                session_id = item.get("session_id")
                usage_info = assistant_message.get("usage")
            elif item.get("type") == "system":
                session_id = item.get("session_id")
        
        # Update session if found
        if session_id:
            self.session_id = session_id
        
        # Log assistant response and usage
        if assistant_message and usage_info:
            # Get message preview for logging
            message_preview = ""
            content = assistant_message.get("content", [])
            for item in content:
                if item.get("type") == "text":
                    text = item.get("text", "").strip()
                    if text:
                        message_preview = text[:80]
                        break
            
            self.logger.assistant_response(message_preview, usage_info)
        
        # Show usage info if available
        if usage_info:
            self.show_usage_info(usage_info)
        
        return {
            "assistant_message": assistant_message,
            "session_id": session_id,
            "usage": usage_info
        }
    
    def show_usage_info(self, usage: Dict[str, Any]):
        """Display token usage information"""
        usage_table = Table.grid(padding=1)
        usage_table.add_column(style="dim")
        usage_table.add_column(style="cyan")
        
        usage_table.add_row("Input tokens:", f"{usage.get('input_tokens', 0):,}")
        usage_table.add_row("Output tokens:", f"{usage.get('output_tokens', 0):,}")
        
        if usage.get('cache_creation_input_tokens'):
            usage_table.add_row("Cache creation:", f"{usage.get('cache_creation_input_tokens', 0):,}")
        if usage.get('cache_read_input_tokens'):
            usage_table.add_row("Cache read:", f"{usage.get('cache_read_input_tokens', 0):,}")
        
        # Calculate rough cost (estimate)
        total_tokens = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
        estimated_cost = total_tokens * 0.000003  # Rough estimate
        
        if estimated_cost > 0:
            usage_table.add_row("Est. cost:", f"${estimated_cost:.4f}")
        
        console.print(Panel(
            usage_table,
            title="[dim]📊 Token Usage[/dim]",
            style="dim",
            border_style="dim"
        ))
    
    def show_help(self):
        """Show help information"""
        help_table = Table.grid(padding=1)
        help_table.add_column(style="bold cyan")
        help_table.add_column(style="white")
        
        help_table.add_row("/help", "Show this help message")
        help_table.add_row("/session", "Show current session info")
        help_table.add_row("/session <id|new>", "Switch to session (use Tab for options)")
        help_table.add_row("/history", "Show conversation history")
        help_table.add_row("/clear", "Clear conversation display")
        help_table.add_row("/reset", "Start new session")
        help_table.add_row("/debug", "Toggle debug mode")
        help_table.add_row("", "")
        help_table.add_row("/max-turns <number>", "Set max conversation turns (1-100)")
        help_table.add_row("/workflow <name>", "Switch to different workflow")
        help_table.add_row("/workflows", "List available workflows")
        help_table.add_row("/config", "Show current configuration")
        help_table.add_row("", "")
        help_table.add_row("/quit", "Exit the application")
        help_table.add_row("", "")
        help_table.add_row("Regular text", "Send message to Claude")
        
        console.print(Panel(
            help_table,
            title="[bold]📚 Available Commands[/bold]",
            border_style="cyan"
        ))
        
        # Show autocomplete help
        autocomplete_help = Panel(
            "[bold cyan]✨ Input & Navigation:[/bold cyan]\n\n"
            "• Type [cyan]/[/cyan] + [cyan]Tab[/cyan] to see command suggestions\n"
            "• Use [cyan]↑↓[/cyan] arrow keys to browse command history\n"
            "• Press [cyan]Tab[/cyan] to complete commands and arguments\n"
            "• Use [cyan]Ctrl+R[/cyan] to search command history\n"
            "• Normal mouse selection/copy/scroll works everywhere\n"
            "• Type [cyan]/workflow [/cyan] + [cyan]Tab[/cyan] for workflow options\n"
            "• Type [cyan]/session [/cyan] + [cyan]Tab[/cyan] for session options",
            title="[dim]💡 Pro Tips[/dim]",
            border_style="dim"
        )
        
        # Show logging info
        logging_help = Panel(
            "[bold cyan]📝 Live Activity Logging:[/bold cyan]\n\n"
            "• All activity logged to [cyan]logs/workflow_run.log[/cyan]\n"
            "• Session starts, tool calls, responses tracked\n"
            "• Workflow prefix shows current mode\n"
            "• Real-time monitoring for AI agents\n"
            "• Timestamped entries with details",
            title="[dim]🔍 Monitoring[/dim]",
            border_style="dim"
        )
        
        console.print(autocomplete_help)
        console.print(logging_help)
    
    def show_workflows(self):
        """Show available workflows"""
        if not self.available_workflows:
            console.print("[yellow]No workflows found in src/agents/claude_code/workflows/[/yellow]")
            return
        
        workflows_table = Table.grid(padding=1)
        workflows_table.add_column(style="bold cyan")
        workflows_table.add_column(style="white")
        workflows_table.add_column(style="dim")
        
        for name, info in self.available_workflows.items():
            indicator = "👉" if name == self.current_workflow else "  "
            workflows_table.add_row(f"{indicator} {name}", info["description"], f"({info['path']})")
        
        console.print(Panel(
            workflows_table,
            title="[bold]🔧 Available Workflows[/bold]",
            border_style="cyan"
        ))
    
    def show_config(self):
        """Show current configuration"""
        config_table = Table.grid(padding=1)
        config_table.add_column(style="dim")
        config_table.add_column(style="cyan")
        
        config_table.add_row("Current Workflow:", f"{self.current_workflow}")
        if self.current_workflow in self.available_workflows:
            config_table.add_row("Workflow Description:", self.available_workflows[self.current_workflow]["description"])
            config_table.add_row("Prompt File:", self.available_workflows[self.current_workflow]["path"])
        
        config_table.add_row("Max Turns:", f"{self.max_turns}")
        config_table.add_row("Session ID:", self.session_id or "None (new session)")
        config_table.add_row("Available Workflows:", f"{len(self.available_workflows)}")
        
        console.print(Panel(
            config_table,
            title="[bold]⚙️ Current Configuration[/bold]",
            border_style="cyan"
        ))
    

    
    def show_session_info(self):
        """Show current session information"""
        if self.session_id:
            session_data = self.saved_sessions.get(self.session_id, {})
            name = session_data.get('name', 'Unnamed')
            console.print(f"[cyan]📱 Current session: {name}[/cyan]")
            console.print(f"[dim]ID: {self.session_id[:12]}... | Workflow: {self.current_workflow} | Messages: {len(self.conversation_history)}[/dim]")
        else:
            console.print("[yellow]📱 No active session (next message starts new session)[/yellow]")
        
        if self.saved_sessions:
            console.print(f"[dim]💾 {len(self.saved_sessions)} saved sessions available[/dim]")
    
    def show_conversation_history(self):
        """Show current conversation history"""
        if not self.conversation_history:
            console.print("[yellow]No conversation history in current session[/yellow]")
            return
        
        console.print(f"[bold cyan]💬 Conversation History ({len(self.conversation_history)} messages)[/bold cyan]\n")
        
        for i, (role, content) in enumerate(self.conversation_history, 1):
            if role == "user":
                # Truncate long user messages
                preview = content[:100] + "..." if len(content) > 100 else content
                console.print(f"[bold green]{i:2d}. 👤 User:[/bold green] {preview}")
            elif role == "assistant":
                # For assistant messages, try to extract text content
                if isinstance(content, dict) and "content" in content:
                    text_parts = []
                    for item in content["content"]:
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                    text = " ".join(text_parts)
                    preview = text[:100] + "..." if len(text) > 100 else text
                else:
                    preview = str(content)[:100] + "..." if len(str(content)) > 100 else str(content)
                console.print(f"[bold blue]{i:2d}. 🤖 Assistant:[/bold blue] {preview}")
            else:
                preview = str(content)[:100] + "..." if len(str(content)) > 100 else str(content)
                console.print(f"[dim]{i:2d}. {role}:[/dim] {preview}")
        
        console.print(f"\n[dim]📊 Total messages: {len(self.conversation_history)}[/dim]")
    
    def set_max_turns(self, turns: str) -> bool:
        """Set max turns with validation"""
        try:
            num_turns = int(turns)
            if 1 <= num_turns <= 100:
                old_turns = self.max_turns
                self.max_turns = num_turns
                self.save_settings()  # Auto-save settings
                
                # Log configuration change
                self.logger.config_change("max_turns", str(old_turns), str(num_turns))
                
                console.print(f"[green]✅ Max turns set to {num_turns}[/green]")
                return True
            else:
                console.print("[red]❌ Max turns must be between 1 and 100[/red]")
                return False
        except ValueError:
            console.print(f"[red]❌ Invalid number: {turns}[/red]")
            return False
    
    def set_workflow(self, workflow_name: str) -> bool:
        """Switch to a different workflow"""
        if workflow_name in self.available_workflows:
            old_workflow = self.current_workflow
            self.current_workflow = workflow_name
            self.session_id = None  # Reset session when changing workflow
            self.save_settings()  # Auto-save settings
            
            # Log configuration change
            self.logger.config_change("workflow", old_workflow, workflow_name)
            
            # Reinitialize logger with new workflow
            self.logger = WorkflowLogger(self.current_workflow)
            
            console.print(f"[green]✅ Switched from '{old_workflow}' to '{workflow_name}' workflow[/green]")
            console.print(f"[dim]Description: {self.available_workflows[workflow_name]['description']}[/dim]")
            console.print("[yellow]🔄 Session reset - next message will start a new conversation[/yellow]")
            return True
        else:
            console.print(f"[red]❌ Workflow '{workflow_name}' not found[/red]")
            console.print("[dim]Use /workflows to see available options[/dim]")
            return False
    
    def run(self):
        """Main chat loop"""
        console.clear()
        self.show_header()
        
        # Show session info in welcome
        session_info = ""
        if self.session_id:
            session_info = f" | Session: {self.session_id[:8]}..."
        
        saved_count = len(self.saved_sessions)
        sessions_info = f"💾 {saved_count} saved sessions available\n" if saved_count > 0 else ""
        
        # Update session info display
        session_display = ""
        if self.session_id:
            session_data = self.saved_sessions.get(self.session_id, {})
            session_name = session_data.get('name', 'Unnamed')
            session_display = f"📱 **{session_name}** session loaded | "
        
        console.print(Panel(
            "[bold green]Welcome to Claude Streaming Chat![/bold green]\n\n"
            f"🎯 Connected to **{self.current_workflow.upper()}** workflow (Max turns: {self.max_turns})\n"
            f"{session_display}💬 Type your message and watch Claude work in real-time\n"
            "🔧 Tool calls are displayed as they happen\n"
            "✨ Type [cyan]/[/cyan] + [cyan]Tab[/cyan] for smart autocomplete\n"
            "🖱️ Normal mouse selection, copy & scroll work everywhere\n"
            f"💾 Sessions auto-save | {len(self.saved_sessions)} saved sessions available\n"
            "📝 Activity logged to [cyan]logs/workflow_run.log[/cyan] for monitoring\n\n"
            "Use [cyan]/session[/cyan] + [cyan]Tab[/cyan] for session picker | [cyan]/help[/cyan] for all commands | [cyan]/quit[/cyan] to exit.",
            title="[green]🚀 Getting Started[/green]",
            border_style="green"
        ))
        console.print()
        
        try:
            while True:
                # Get user input with autocomplete
                try:
                    user_input = prompt(
                        HTML('<b><style fg="green">💬 You:</style></b> '),
                        completer=self.completer,
                        complete_style=CompleteStyle.MULTI_COLUMN,
                        history=self.history,
                        mouse_support=False,  # Disable mouse capture for normal terminal selection
                        complete_while_typing=False,  # Only complete on Tab, not while typing
                        enable_history_search=True,  # Allow Ctrl+R history search
                        multiline=False,  # Single line input
                        wrap_lines=True,  # Allow text wrapping
                        vi_mode=False,  # Use emacs key bindings (more familiar)
                        auto_suggest=None,  # Disable auto-suggestions to reduce interference
                    ).strip()
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[dim]👋 Interrupted. Goodbye![/dim]")
                    break
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    # Parse command and arguments
                    parts = user_input.split(None, 1)
                    command = parts[0]
                    args = parts[1] if len(parts) > 1 else ""
                    
                    if command == '/quit':
                        console.print("[dim]👋 Goodbye![/dim]")
                        break
                    elif command == '/help':
                        self.show_help()
                        continue
                    elif command == '/session':
                        if args:
                            if args.lower() == 'new':
                                self.session_id = None
                                self.conversation_history.clear()
                                console.print("[green]✅ Started new session[/green]")
                                self.show_header()  # Refresh header
                            else:
                                # Try to resume session by ID
                                success = self.resume_session_by_id(args)
                                if success:
                                    session_data = self.saved_sessions.get(args, {})
                                    console.print(f"[green]✅ Resumed session: {session_data.get('name', 'Unnamed')}[/green]")
                                    console.print(f"[dim]Workflow: {self.current_workflow} | Messages: {len(self.conversation_history)}[/dim]")
                                    self.show_header()  # Refresh header
                                else:
                                    console.print(f"[red]❌ Session not found: {args}[/red]")
                                    console.print("[dim]Use /session + Tab to see available sessions[/dim]")
                        else:
                            # Show current session info
                            self.show_session_info()
                            console.print("[dim]💡 Use [cyan]/session [/cyan] + [cyan]Tab[/cyan] to see available sessions[/dim]")
                        continue
                    elif command == '/history':
                        self.show_conversation_history()
                        continue
                    elif command == '/clear':
                        console.clear()
                        self.show_header()
                        continue
                    elif command == '/reset':
                        self.session_id = None
                        self.active_tools.clear()
                        console.print("[yellow]🔄 Session reset. Next message starts fresh.[/yellow]")
                        continue
                    elif command == '/debug':
                        debug_status = "enabled" if os.getenv("DEBUG") else "disabled"
                        console.print(f"[cyan]Debug mode: {debug_status}[/cyan]")
                        if not os.getenv("DEBUG"):
                            console.print("[dim]Set DEBUG=1 to enable debug output[/dim]")
                        continue
                    elif command == '/config':
                        self.show_config()
                        continue
                    elif command == '/workflows':
                        self.show_workflows()
                        continue
                    elif command == '/max-turns':
                        if args:
                            success = self.set_max_turns(args)
                            if success:
                                self.show_header()  # Refresh header to show new setting
                        else:
                            console.print("[red]❌ Please specify a number: /max-turns <1-100>[/red]")
                        continue
                    elif command == '/workflow':
                        if args:
                            success = self.set_workflow(args)
                            if success:
                                self.show_header()  # Refresh header to show new workflow
                        else:
                            console.print("[red]❌ Please specify a workflow: /workflow <name>[/red]")
                            console.print("[dim]Use /workflows to see available options[/dim]")
                        continue
                    else:
                        console.print(f"[red]Unknown command: {command}[/red]")
                        console.print("[dim]Use /help for available commands[/dim]")
                        continue
                
                # Add to conversation history and command history
                self.conversation_history.append(("user", user_input))
                self.add_command_to_history(user_input)
                
                # Execute with streaming
                response = self.execute_command_streaming(user_input)
                
                # Add response to history
                if response.get("assistant_message"):
                    self.conversation_history.append(("assistant", response["assistant_message"]))
                    
                    # Auto-save session after each exchange
                    self.auto_save_session()
                    
                    # Log workflow completion timing
                    if self.workflow_start_time:
                        duration = (datetime.now() - self.workflow_start_time).total_seconds()
                        self.logger.workflow_complete(True, duration)
                        self.workflow_start_time = None  # Reset for next workflow
                
                console.print()  # Add spacing
        
        except KeyboardInterrupt:
            console.print("\n[dim]👋 Interrupted. Goodbye![/dim]")
            self.logger.workflow_complete(False, 0)
        except Exception as e:
            self.logger.error(str(e), "main_run_loop")
            console.print(f"\n[red]❌ Unexpected error: {e}[/red]")
        finally:
            # Save settings on exit to persist command history
            self.save_settings()

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        console.print(Panel(
            "[bold]Claude Chat CLI - Streaming Interface[/bold]\n\n"
            "A beautiful terminal chat interface for Claude with real-time streaming,\n"
            "tool call visualization, and session management.\n\n"
            "[cyan]Usage:[/cyan]\n"
            "  python claude.py\n\n"
            "[cyan]Features:[/cyan]\n"
            "• Real-time streaming output\n"
            "• Beautiful tool call displays\n"
            "• Session persistence\n"
            "• Modern chat UI\n"
            "• Token usage tracking\n\n"
            "[cyan]Requirements:[/cyan]\n"
            "• .mcp.json (MCP configuration)\n"
            "• allowed_tools.json (Tool permissions)\n"
            "• src/agents/claude_code/workflows/implement/prompt.md",
            title="[blue]Claude Chat CLI[/blue]",
            border_style="blue"
        ))
        return
    
    chat = ClaudeStreamingChat()
    chat.run()

if __name__ == "__main__":
    main() 