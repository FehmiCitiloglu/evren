#!/usr/bin/env python3
"""
EVREN CLI & Agent — Cross-Platform Installer
Supports: macOS, Linux, and Windows (PowerShell / CMD)
Requirements: Python 3.10+
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

MIN_PYTHON = (3, 10)


def log(msg: str, color: str = ""):
    colors = {
        "green": "\033[92m",
        "cyan": "\033[96m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
    }
    # On Windows without VT terminal support, print plain text
    if sys.platform == "win32" and not os.environ.get("WT_SESSION") and not os.environ.get("TERM"):
        print(msg)
    else:
        prefix = colors.get(color, "")
        reset = colors["reset"] if color else ""
        print(f"{prefix}{msg}{reset}")


def check_python_version():
    if sys.version_info < MIN_PYTHON:
        log(f"Error: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required.", "red")
        log(f"Current version: {sys.version}", "yellow")
        sys.exit(1)
    log(f"✔ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} detected", "green")


def main():
    root_dir = Path(__file__).resolve().parent
    os.chdir(root_dir)

    log("\n" + "=" * 55, "cyan")
    log("  🚀 EVREN CLI & Agent — Installation Setup", "bold")
    log("=" * 55, "cyan")

    check_python_version()

    # Detect UV or fallback to python -m venv
    uv_bin = shutil.which("uv")
    is_windows = sys.platform == "win32"
    venv_dir = root_dir / ".venv"

    # Virtual environment paths
    if is_windows:
        venv_python = venv_dir / "Scripts" / "python.exe"
        activate_cmd = ".\\.venv\\Scripts\\Activate.ps1"
        cmd_activate = ".venv\\Scripts\\activate.bat"
    else:
        venv_python = venv_dir / "bin" / "python"
        activate_cmd = "source .venv/bin/activate"
        cmd_activate = ""

    # Step 1: Create venv
    if not venv_dir.exists():
        log("\n[1/3] Creating virtual environment (.venv)...", "cyan")
        if uv_bin:
            log("  Using 'uv venv'...", "dim")
            subprocess.run([uv_bin, "venv", str(venv_dir)], check=True)
        else:
            log("  Using 'python -m venv'...", "dim")
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        log("✔ Virtual environment created at .venv", "green")
    else:
        log("\n[1/3] Existing virtual environment detected (.venv)", "green")

    # Step 2: Install dependencies & package in editable mode
    log("\n[2/3] Installing dependencies and package...", "cyan")
    if uv_bin:
        log("  Running 'uv pip install -e .[dev]'...", "dim")
        subprocess.run([uv_bin, "pip", "install", "-e", ".[dev]"], check=True)
    else:
        log("  Upgrading pip...", "dim")
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
        log("  Running 'pip install -e .[dev]'...", "dim")
        subprocess.run([str(venv_python), "-m", "pip", "install", "-e", ".[dev]"], check=True)
    log("✔ Package evren-agent and dependencies installed successfully", "green")

    # Step 3: Setup .env file
    log("\n[3/3] Checking environment configuration (.env)...", "cyan")
    env_file = root_dir / ".env"
    env_example = root_dir / ".env.example"
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        log("✔ Created .env from .env.example", "green")
    elif env_file.exists():
        log("✔ Existing .env preserved (not overwritten)", "green")

    # Done! Display instructions
    log("\n" + "=" * 55, "green")
    log("  🎉 Installation Complete!", "bold")
    log("=" * 55, "green")

    log("\n📌 Next Steps:", "cyan")
    if is_windows:
        log(f"  1. Activate virtual environment:", "yellow")
        log(f"     PowerShell:  {activate_cmd}", "bold")
        log(f"     CMD:         {cmd_activate}", "bold")
    else:
        log(f"  1. Activate virtual environment:", "yellow")
        log(f"     {activate_cmd}", "bold")

    log("\n  2. Configure your EVREN API Key in .env:", "yellow")
    log("     EVREN_API_KEY=evren_llm_your_key_here", "dim")

    log("\n  3. Test & Run:", "yellow")
    log("     evren --help           (Direct EVREN API CLI)", "bold")
    log("     evren-agent            (Interactive Agent REPL)", "bold")
    log("     evren-agent --commands (List all available commands)\n", "bold")


if __name__ == "__main__":
    main()
