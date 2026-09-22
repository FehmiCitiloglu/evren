---
name: computer-use
description: Operating system interaction, terminal command execution, filesystem navigation, and safe automation
---

# Computer Use Skill

When this skill is active:
1. System & Terminal Execution: Execute shell commands safely and purposefully using available command execution tools. Always inspect command output, return codes, and error streams.
2. File System Operations: Inspect directory hierarchies, verify file paths, and read relevant files before attempting modifications or creating new files.
3. Safety & Idempotency: Avoid dangerous or irreversible operations (such as unconstrained recursive deletes like `rm -rf /` or overwriting critical system files). Validate preconditions and ensure operations are idempotent where possible.
4. Diagnostics & Troubleshooting: When commands or scripts fail, diagnose the root cause from the error output, check environment variables and process states, and rectify underlying issues instead of repeating failed actions.
5. Environment Awareness: Adapt commands and file operations appropriately to the host environment (operating system, shell environment, virtual environments, and available system tools).
