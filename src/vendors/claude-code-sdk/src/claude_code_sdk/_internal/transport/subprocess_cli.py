"""Subprocess transport implementation using Claude Code CLI."""

import json
import os
import shutil
import datetime
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from subprocess import PIPE
from typing import Any
import asyncio
import sys

logger = logging.getLogger(__name__)

# Global shared log file path for this process - ensures all transports use same file
_SHARED_LOG_FILE_PATH = None
_SHARED_LOG_FILE = None

import anyio
from anyio.abc import Process
from anyio.streams.text import TextReceiveStream

from ..._errors import CLIConnectionError, CLINotFoundError, ProcessError
from ..._errors import CLIJSONDecodeError as SDKJSONDecodeError
from ...types import ClaudeCodeOptions
from . import Transport


class SubprocessCLITransport(Transport):
    """Subprocess transport using Claude Code CLI."""

    def __init__(
        self,
        prompt: str,
        options: ClaudeCodeOptions,
        cli_path: str | Path | None = None,
    ):
        self._prompt = prompt
        self._options = options
        self._cli_path = str(cli_path) if cli_path else self._find_cli()
        self._cwd = str(options.cwd) if options.cwd else None
        self._process: Process | None = None
        self._stderr_stream: TextReceiveStream | None = None
        
        # Use shared log file for all transports in this process
        global _SHARED_LOG_FILE_PATH, _SHARED_LOG_FILE
        if _SHARED_LOG_FILE_PATH is None:
            # Find the workspace root by looking for .git directory
            current_dir = Path.cwd()
            workspace_root = None
            
            # Walk up to find .git directory (root of workspace)
            for parent in [current_dir] + list(current_dir.parents):
                if (parent / ".git").exists():
                    workspace_root = parent
                    break
            
            # If not found, fall back to current directory
            if workspace_root is None:
                workspace_root = current_dir
            
            # DISABLED: No more shared claude_sdk_stream files - using individual workflow logs instead
            # log_dir = workspace_root / "logs"
            # os.makedirs(log_dir, exist_ok=True)
            # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            # _SHARED_LOG_FILE_PATH = str(log_dir / f"claude_sdk_stream_{timestamp}.json")
        
        self._log_file_path = None  # Disabled shared log file
        self._log_file = None

    def _find_cli(self) -> str:
        """Find Claude Code CLI binary."""
        if cli := shutil.which("claude"):
            return cli

        locations = [
            Path.home() / ".npm-global/bin/claude",
            Path("/usr/local/bin/claude"),
            Path.home() / ".local/bin/claude",
            Path.home() / "node_modules/.bin/claude",
            Path.home() / ".yarn/bin/claude",
        ]

        for path in locations:
            if path.exists() and path.is_file():
                return str(path)

        node_installed = shutil.which("node") is not None

        if not node_installed:
            error_msg = "Claude Code requires Node.js, which is not installed.\n\n"
            error_msg += "Install Node.js from: https://nodejs.org/\n"
            error_msg += "\nAfter installing Node.js, install Claude Code:\n"
            error_msg += "  npm install -g @anthropic-ai/claude-code"
            raise CLINotFoundError(error_msg)

        raise CLINotFoundError(
            "Claude Code not found. Install with:\n"
            "  npm install -g @anthropic-ai/claude-code\n"
            "\nIf already installed locally, try:\n"
            '  export PATH="$HOME/node_modules/.bin:$PATH"\n'
            "\nOr specify the path when creating transport:\n"
            "  SubprocessCLITransport(..., cli_path='/path/to/claude')"
        )

    def _build_command(self) -> list[str]:
        """Build CLI command with arguments."""
        cmd = [self._cli_path, "--output-format", "stream-json", "--verbose"]

        if self._options.system_prompt:
            cmd.extend(["--system-prompt", self._options.system_prompt])

        if self._options.append_system_prompt:
            cmd.extend(["--append-system-prompt", self._options.append_system_prompt])

        if self._options.allowed_tools:
            cmd.extend(["--allowedTools", ",".join(self._options.allowed_tools)])

        if self._options.max_turns:
            cmd.extend(["--max-turns", str(self._options.max_turns)])

        if self._options.disallowed_tools:
            cmd.extend(["--disallowedTools", ",".join(self._options.disallowed_tools)])

        if self._options.model:
            cmd.extend(["--model", self._options.model])

        if self._options.permission_prompt_tool_name:
            cmd.extend(
                ["--permission-prompt-tool", self._options.permission_prompt_tool_name]
            )

        if self._options.permission_mode:
            cmd.extend(["--permission-mode", self._options.permission_mode])

        if self._options.continue_conversation:
            cmd.append("--continue")

        if self._options.resume:
            cmd.extend(["--resume", self._options.resume])

        if self._options.mcp_servers:
            cmd.extend(
                ["--mcp-config", json.dumps({"mcpServers": self._options.mcp_servers})]
            )

        cmd.extend(["--print", self._prompt])
        
        # Debug: Log the exact command being executed
        logger.info(f"Claude CLI command: {' '.join(cmd)}")
        
        return cmd

    async def connect(self) -> None:
        """Start subprocess."""
        if self._process:
            return

        # DISABLED: No more shared log file creation - using individual workflow logs
        # global _SHARED_LOG_FILE
        # if _SHARED_LOG_FILE is None:
        #     _SHARED_LOG_FILE = open(self._log_file_path, "w")
        self._log_file = None  # Disabled shared log file

        cmd = self._build_command()
        try:
            self._process = await anyio.open_process(
                cmd,
                stdin=None,
                stdout=PIPE,
                stderr=PIPE,
                cwd=self._cwd,
                env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "sdk-py"},
            )

            # Keep raw streams for manual processing
            # stdout will be processed manually in receive_messages
            if self._process.stderr:
                self._stderr_stream = TextReceiveStream(self._process.stderr)

        except FileNotFoundError as e:
            raise CLINotFoundError(f"Claude Code not found at: {self._cli_path}") from e
        except Exception as e:
            raise CLIConnectionError(f"Failed to start Claude Code: {e}") from e

    async def disconnect(self) -> None:
        """Terminate subprocess."""
        if not self._process:
            return

        if self._process.returncode is None:
            try:
                self._process.terminate()
                with anyio.fail_after(5.0):
                    await self._process.wait()
            except TimeoutError:
                self._process.kill()
                await self._process.wait()
            except ProcessLookupError:
                pass

        # Don't close shared log file here - it will be closed when process exits
        self._log_file = None

        self._process = None
        self._stderr_stream = None

    async def send_request(self, messages: list[Any], options: dict[str, Any]) -> None:
        """Not used for CLI transport - args passed via command line."""

    async def receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        """Receive messages from CLI."""
        if not self._process or not self._process.stdout:
            raise CLIConnectionError("Not connected")

        stderr_lines = []

        async def read_stderr() -> None:
            """Read stderr in background."""
            if self._stderr_stream:
                try:
                    async for line in self._stderr_stream:
                        stderr_lines.append(line.strip())
                except anyio.ClosedResourceError:
                    pass

        # Simple implementation without TaskGroup complexity
        stderr_task = asyncio.create_task(read_stderr())
        
        # Use readline from the raw stdout stream to handle large lines
        buffer = b""
        
        try:
            while True:
                # Read chunks from stdout
                chunk = await self._process.stdout.receive(8192)  # 8KB chunks
                if not chunk:
                    break  # EOF
                    
                buffer += chunk
                
                # Process complete lines
                while b"\n" in buffer:
                    line_bytes, buffer = buffer.split(b"\n", 1)
                    line_str = line_bytes.decode("utf-8", errors="replace").strip()
                    
                    if not line_str:
                        continue

                    try:
                        # DISABLED: No more raw JSON stream logging to shared file
                        # Individual workflow logs handle this now
                        # if self._log_file:
                        #     self._log_file.write(line_str + "\n")
                        #     self._log_file.flush()
                        
                        data = json.loads(line_str)
                        try:
                            yield data
                        except GeneratorExit:
                            # Handle generator cleanup gracefully
                            stderr_task.cancel()
                            return
                    except json.JSONDecodeError as e:
                        # Log the exact line that failed to parse
                        logger.error(f"Failed to parse JSON: {line_str[:200]}...")
                        
                        # DISABLED: No more error logging to shared file
                        # if self._log_file:
                        #     self._log_file.write(f"JSON_ERROR: {line_str}\n")
                        #     self._log_file.flush()
                        
                        if line_str.startswith("{") or line_str.startswith("["):
                            raise SDKJSONDecodeError(line_str, e) from e
                        continue
                        
            # Process any remaining data in buffer
            if buffer:
                line_str = buffer.decode("utf-8", errors="replace").strip()
                if line_str:
                    try:
                        data = json.loads(line_str)
                        yield data
                    except json.JSONDecodeError:
                        pass  # Ignore incomplete final line
        except anyio.ClosedResourceError:
            pass
        finally:
            # Ensure stderr task is cancelled
            stderr_task.cancel()
            try:
                await stderr_task
            except asyncio.CancelledError:
                pass

        await self._process.wait()
        if self._process.returncode is not None and self._process.returncode != 0:
            stderr_output = "\n".join(stderr_lines)
            if stderr_output and "error" in stderr_output.lower():
                raise ProcessError(
                    "CLI process failed",
                    exit_code=self._process.returncode,
                    stderr=stderr_output,
                )

    def is_connected(self) -> bool:
        """Check if subprocess is running."""
        return self._process is not None and self._process.returncode is None
