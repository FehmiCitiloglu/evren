"""Local, non-interactive shell execution with bounded output and process cleanup."""
from __future__ import annotations

import asyncio
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
from typing import Optional

OUTPUT_LIMIT = 32_768  # bytes per stream retained for display and model context


def shell_args(command: str, shell: Optional[str] = None) -> list[str]:
    selected = shell or (os.environ.get("COMSPEC", "cmd.exe") if sys.platform == "win32"
                         else os.environ.get("SHELL") or "/bin/sh")
    name = Path(selected).name.lower()
    executable = shutil.which(selected)
    if executable is None:
        raise ValueError(f"Shell not found: {selected}")
    if name in ("powershell", "powershell.exe", "pwsh", "pwsh.exe"):
        return [executable, "-NoProfile", "-NonInteractive", "-Command", command]
    if name in ("cmd", "cmd.exe"):
        return [executable, "/d", "/s", "/c", command]
    return [executable, "-c", command]


async def _capture(stream: asyncio.StreamReader, output: bytearray) -> bool:
    truncated = False
    while chunk := await stream.read(8192):
        available = max(0, OUTPUT_LIMIT - len(output))
        output.extend(chunk[:available])
        truncated |= len(chunk) > available
    return truncated


async def _stop(process: asyncio.subprocess.Process) -> None:
    if sys.platform == "win32":
        if process.returncode is None:
            killer = await asyncio.create_subprocess_exec(
                "taskkill", "/PID", str(process.pid), "/T", "/F",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await killer.wait()
            if process.returncode is None:
                process.kill()
    else:
        # Kill the whole group, including children holding output pipes open.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    await process.wait()


async def run_shell(command: str, shell: Optional[str] = None,
                    cwd: Optional[str] = None, timeout: float = 60) -> str:
    if not isinstance(command, str) or not command.strip():
        return "Command execution error: command cannot be empty."
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        return "Command execution error: timeout must be a positive number of seconds."
    try:
        args = shell_args(command, shell)
        options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform == "win32" else {"start_new_session": True}
        process = await asyncio.create_subprocess_exec(
            *args, cwd=cwd, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, **options,
        )
    except (OSError, ValueError) as exc:
        return f"Command execution error: {exc}"

    stdout, stderr = bytearray(), bytearray()
    readers = [asyncio.create_task(_capture(process.stdout, stdout)),
               asyncio.create_task(_capture(process.stderr, stderr))]
    completion = asyncio.gather(process.wait(), *readers)
    timed_out = False
    try:
        await asyncio.wait_for(asyncio.shield(completion), timeout=timeout)
    except asyncio.TimeoutError:
        timed_out = True
        await _stop(process)
        await completion
    except asyncio.CancelledError:
        await _stop(process)
        await completion
        raise

    def decode(data: bytearray, truncated: bool) -> str:
        value = data.decode("utf-8", errors="replace")
        return value + (f"\n[output truncated after {OUTPUT_LIMIT} bytes]" if truncated else "")

    out = decode(stdout, readers[0].result())
    if stderr:
        out += "\n[stderr]:\n" + decode(stderr, readers[1].result())
    status = f"Command timed out after {timeout:g}s; process terminated." if timed_out else f"Exit code {process.returncode}:"
    return f"{status}\n{out.strip()}"
