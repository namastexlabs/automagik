"""
Stderr memory limit patch for claude-code-sdk.

The official SDK (as of 0.0.14) has unbounded stderr collection which can
cause memory exhaustion. This patch adds safety limits.

This patch can be removed once the official SDK adds stderr limits.
"""

import logging
from typing import AsyncIterator, Any

import anyio

logger = logging.getLogger(__name__)

# Safety constants
MAX_STDERR_SIZE = 10 * 1024 * 1024  # 10MB max stderr
STDERR_TIMEOUT = 30.0  # 30 second timeout


def apply_stderr_memory_patch():
    """Apply memory safety patch to SubprocessCLITransport."""
    try:
        from claude_code_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
        from claude_code_sdk._errors import CLIConnectionError, ProcessError
        from claude_code_sdk._errors import CLIJSONDecodeError as SDKJSONDecodeError
    except ImportError:
        logger.warning("claude-code-sdk not installed, skipping stderr patch")
        return

    # Save original method
    _original_receive_messages = SubprocessCLITransport.receive_messages
    
    async def patched_receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        """Patched receive_messages with stderr memory limits."""
        if not self._process or not self._stdout_stream:
            raise CLIConnectionError("Not connected")

        stderr_lines = []
        stderr_size = 0

        async def read_stderr() -> None:
            """Read stderr with memory limits."""
            nonlocal stderr_size
            if self._stderr_stream:
                try:
                    # Use timeout to prevent hanging
                    with anyio.fail_after(STDERR_TIMEOUT):
                        async for line in self._stderr_stream:
                            line_text = line.strip()
                            line_size = len(line_text)

                            # Enforce memory limit
                            if stderr_size + line_size > MAX_STDERR_SIZE:
                                stderr_lines.append(f"[stderr truncated after {stderr_size} bytes]")
                                # Drain rest of stream without storing
                                async for _ in self._stderr_stream:
                                    pass
                                break

                            stderr_lines.append(line_text)
                            stderr_size += line_size

                except TimeoutError:
                    stderr_lines.append(f"[stderr collection timed out after {STDERR_TIMEOUT}s]")
                except anyio.ClosedResourceError:
                    pass

        # Run the rest of the original method with our patched stderr reader
        async with anyio.create_task_group() as tg:
            tg.start_soon(read_stderr)

            json_buffer = ""

            try:
                async for line in self._stdout_stream:
                    line_str = line.strip()
                    if not line_str:
                        continue

                    json_lines = line_str.split("\n")

                    for json_line in json_lines:
                        json_line = json_line.strip()
                        if not json_line:
                            continue

                        # Keep accumulating partial JSON until we can parse it
                        json_buffer += json_line

                        if len(json_buffer) > 1024 * 1024:  # 1MB limit from original
                            json_buffer = ""
                            raise SDKJSONDecodeError(
                                f"JSON message exceeded maximum buffer size of 1MB",
                                ValueError(f"Buffer size exceeds limit")
                            )

                        try:
                            import json
                            data = json.loads(json_buffer)
                            json_buffer = ""
                            try:
                                yield data
                            except GeneratorExit:
                                return
                        except json.JSONDecodeError:
                            continue

            except anyio.ClosedResourceError:
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

    # Apply the patch
    SubprocessCLITransport.receive_messages = patched_receive_messages
    logger.info("Applied stderr memory limit patch to claude-code-sdk")