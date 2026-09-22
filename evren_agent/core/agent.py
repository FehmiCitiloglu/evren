from __future__ import annotations
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple, Union

from evren_agent.config import load_config
from evren_agent.core.shell import run_shell
from evren_agent.core.tools import ToolRegistry
from evren_agent.core.types import (
    Message,
    ModelInfo,
    StreamChunk,
    ToolCall,
    ToolCallFunction,
    ToolDefinition,
    ToolResult,
)
from evren_agent.mcp.manager import MCPManager
from evren_agent.plugins.manager import PluginManager
from evren_agent.providers.base import BaseProvider
from evren_agent.providers.registry import ProviderRegistry
from evren_agent.skills.manager import SkillManager

logger = logging.getLogger(__name__)


class Agent:
    """
    Autonomous, extensible AI Agent.
    Features:
    - Multi-provider support (EVREN direct, LLMTR Gateway, OpenAI, etc.)
    - Model Context Protocol (MCP) server integration (stdio and HTTP)
    - Dynamic Skills discovery, activation, and prompt augmentation
    - Dynamic Plugins with lifecycle hooks and custom tool injection
    - Autonomous Agent loop with recursive tool execution
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
    ):
        self.config_path = config_path
        self.config = config or load_config(config_path)
        agent_conf = self.config.get("agent", {})
        self.name: str = agent_conf.get("name", "EvrenAgent")
        self.base_system_prompt: str = agent_conf.get(
            "system_prompt",
            "You are EvrenAgent, an autonomous AI assistant.",
        )
        self.max_iterations: int = agent_conf.get("max_iterations", 15)
        self.temperature: float = agent_conf.get("temperature", 0.7)

        # Core registries and managers
        self.tools = ToolRegistry()
        self.providers = ProviderRegistry.from_config(self.config)
        self.mcp = MCPManager(self.tools)

        skills_conf = self.config.get("skills", {})
        self.skills = SkillManager(skills_dir=skills_conf.get("directory", "skills"))

        plugins_conf = self.config.get("plugins", {})
        self.plugins = PluginManager(self.tools, plugins_dir=plugins_conf.get("directory", "plugins"))

        self.messages: List[Message] = []
        self._is_initialized = False

    async def initialize(self) -> None:
        """Bootstraps skills, plugins, MCP servers, and agent meta-tools."""
        if self._is_initialized:
            return

        # 1. Register Built-in Meta-Tools (allows agent to add MCPs, skills, plugins, and files)
        self._register_meta_tools()

        # 2. Discover and load skills
        builtin_skills_dir = Path(__file__).parent.parent / "builtin_skills"
        self.skills.discover_skills(additional_dirs=[builtin_skills_dir])

        # Activate configured skills
        active_skills = self.config.get("skills", {}).get("active_skills", [])
        for s_name in active_skills:
            self.skills.activate_skill(s_name)

        # 3. Load plugins
        plugins_conf = self.config.get("plugins", {})
        if plugins_conf.get("autoload_builtins", True):
            enabled_p = plugins_conf.get("enabled_plugins", ["logger", "calculator", "web_search"])
            self.plugins.load_builtins(enabled_p)
        self.plugins.discover_plugins()

        # 4. Connect configured MCP servers
        mcp_conf = self.config.get("mcp_servers", {})
        for name, s_conf in mcp_conf.items():
            try:
                await self.mcp.add_server(
                    name=name,
                    command=s_conf.get("command"),
                    args=s_conf.get("args"),
                    env=s_conf.get("env"),
                    url=s_conf.get("url"),
                )
            except Exception as e:
                logger.error("Failed connecting to MCP server %s: %s", name, e)

        # 5. Dispatch agent init hook
        await self.plugins.dispatch_agent_init(self)

        self._is_initialized = True
        logger.info("EvrenAgent '%s' initialized with provider '%s'", self.name, self.providers.active_name)

    def _register_meta_tools(self) -> None:
        """Registers self-management tools available to the LLM agent."""

        # Tool 1: add_mcp_server
        self.tools.register(
            ToolDefinition(
                name="add_mcp_server",
                description="Connect and dynamically add a new Model Context Protocol (MCP) server. Tools from the server are automatically registered.",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Unique identifier name for this MCP server"},
                        "command": {"type": "string", "description": "Executable command (e.g. 'npx', 'python3', 'uvx') for stdio server"},
                        "args": {"type": "array", "items": {"type": "string"}, "description": "Command-line arguments"},
                        "url": {"type": "string", "description": "Optional HTTP/SSE endpoint URL for remote MCP servers"},
                    },
                    "required": ["name"],
                },
                source="meta:agent",
            ),
            self.add_mcp_server,
        )

        # Tool 2: remove_mcp_server
        self.tools.register(
            ToolDefinition(
                name="remove_mcp_server",
                description="Disconnect and remove an active MCP server and its tools.",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name of the MCP server to remove"}
                    },
                    "required": ["name"],
                },
                source="meta:agent",
            ),
            self.remove_mcp_server,
        )

        # Tool 3: list_mcp_servers
        self.tools.register(
            ToolDefinition(
                name="list_mcp_servers",
                description="List all active and configured MCP servers and their exposed tools.",
                parameters={"type": "object", "properties": {}},
                source="meta:agent",
            ),
            self.list_mcp_servers,
        )

        # Tool 4: add_skill
        self.tools.register(
            ToolDefinition(
                name="add_skill",
                description="Create and activate a new modular skill with custom system instructions.",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Skill name (e.g. 'turkish_lawyer', 'sql_optimizer')"},
                        "description": {"type": "string", "description": "Short description of what the skill does"},
                        "instructions": {"type": "string", "description": "System prompt instructions that guide agent behavior when skill is active"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"},
                    },
                    "required": ["name", "description", "instructions"],
                },
                source="meta:agent",
            ),
            self.add_skill,
        )

        # Tool 5: list_skills
        self.tools.register(
            ToolDefinition(
                name="list_skills",
                description="List all available skills and their active status.",
                parameters={"type": "object", "properties": {}},
                source="meta:agent",
            ),
            self.list_skills,
        )

        # Tool 6: activate_skill / deactivate_skill
        self.tools.register(
            ToolDefinition(
                name="activate_skill",
                description="Activate an existing skill by name so its instructions are injected into the agent prompt.",
                parameters={
                    "type": "object",
                    "properties": {"name": {"type": "string", "description": "Name of the skill to activate"}},
                    "required": ["name"],
                },
                source="meta:agent",
            ),
            self.activate_skill,
        )

        self.tools.register(
            ToolDefinition(
                name="deactivate_skill",
                description="Deactivate a skill by name.",
                parameters={
                    "type": "object",
                    "properties": {"name": {"type": "string", "description": "Name of the skill to deactivate"}},
                    "required": ["name"],
                },
                source="meta:agent",
            ),
            self.deactivate_skill,
        )

        # Tool 7: add_plugin
        self.tools.register(
            ToolDefinition(
                name="add_plugin",
                description="Install a new Python plugin dynamically from Python code. The code must define a subclass of BasePlugin.",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Plugin filename identifier (e.g. 'custom_formatter')"},
                        "python_code": {"type": "string", "description": "Valid Python code defining the plugin class"},
                    },
                    "required": ["name", "python_code"],
                },
                source="meta:agent",
            ),
            self.add_plugin,
        )

        # Tool 8: list_plugins
        self.tools.register(
            ToolDefinition(
                name="list_plugins",
                description="List installed plugins, their status, and the tools they provide.",
                parameters={"type": "object", "properties": {}},
                source="meta:agent",
            ),
            self.list_plugins,
        )

        # Tool 9: switch_provider
        self.tools.register(
            ToolDefinition(
                name="switch_provider",
                description="Switch active LLM provider (e.g. 'evren', 'llmtr', 'openai') and optionally model.",
                parameters={
                    "type": "object",
                    "properties": {
                        "provider_name": {"type": "string", "description": "Provider name ('evren', 'llmtr', 'openai')"},
                        "model_name": {"type": "string", "description": "Optional model name to switch to"},
                    },
                    "required": ["provider_name"],
                },
                source="meta:agent",
            ),
            self.switch_provider,
        )

        # Tool 10: run_shell_command
        self.tools.register(
            ToolDefinition(
                name="run_command",
                description="Execute a shell command in the local environment (supports PowerShell and CMD on Windows, or bash/zsh on Unix) and return stdout/stderr.",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The command string to execute"},
                        "shell": {
                            "type": "string",
                            "description": "Optional shell interpreter, e.g. bash, zsh, powershell, pwsh, cmd. Defaults to the system shell.",
                        },
                        "cwd": {"type": "string", "description": "Working directory for this command only"},
                        "timeout": {"type": "number", "exclusiveMinimum": 0, "description": "Timeout in seconds (default 60)"},
                    },
                    "required": ["command"],
                },
                source="meta:agent",
            ),
            self.run_command_async,
        )

        # Tool 11: file operations
        self.tools.register(
            ToolDefinition(
                name="read_file",
                description="Read the text content of a file on disk.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to file"},
                    },
                    "required": ["path"],
                },
                source="meta:agent",
            ),
            self.read_file,
        )

        self.tools.register(
            ToolDefinition(
                name="write_file",
                description="Create or overwrite a file with given text content.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to file"},
                        "content": {"type": "string", "description": "Text content to write"},
                    },
                    "required": ["path", "content"],
                },
                source="meta:agent",
            ),
            self.write_file,
        )

    # --- Meta Tool Implementations ---

    async def add_mcp_server(
        self,
        name: str,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        url: Optional[str] = None,
    ) -> str:
        tools = await self.mcp.add_server(name=name, command=command, args=args, url=url)
        return f"Successfully added MCP server '{name}'. Registered {len(tools)} tools: {', '.join(tools)}"

    async def remove_mcp_server(self, name: str) -> str:
        removed = await self.mcp.remove_server(name)
        if removed:
            return f"MCP server '{name}' successfully removed."
        return f"MCP server '{name}' was not found."

    def list_mcp_servers(self) -> List[Dict[str, Any]]:
        return self.mcp.list_servers()

    def add_skill(
        self,
        name: str,
        description: str,
        instructions: str,
        tags: Optional[List[str]] = None,
    ) -> str:
        skill = self.skills.add_skill(
            name=name,
            description=description,
            instructions=instructions,
            tags=tags,
            activate=True,
        )
        return f"Skill '{skill.name}' created and activated successfully."

    def list_skills(self) -> List[Dict[str, Any]]:
        return self.skills.list_skills()

    def activate_skill(self, name: str) -> str:
        if self.skills.activate_skill(name):
            return f"Skill '{name}' activated."
        return f"Skill '{name}' not found."

    def deactivate_skill(self, name: str) -> str:
        if self.skills.deactivate_skill(name):
            return f"Skill '{name}' deactivated."
        return f"Skill '{name}' not found."

    def add_plugin(self, name: str, python_code: str) -> str:
        plugin = self.plugins.load_plugin_from_code(name, python_code)
        tools = [t[0].name for t in plugin.get_tools()]
        return f"Plugin '{plugin.name}' loaded successfully. Mounted tools: {tools}"

    def list_plugins(self) -> List[Dict[str, Any]]:
        return self.plugins.list_plugins()

    def switch_provider(self, provider_name: str, model_name: Optional[str] = None) -> str:
        prov = self.providers.set_active(provider_name)
        if model_name:
            prov.set_model(model_name)
        return f"Switched to provider '{prov.name}' with model '{prov.current_model}'."

    def run_command(self, command: str, shell: Optional[str] = None,
                    cwd: Optional[str] = None, timeout: float = 60) -> str:
        """Synchronous SDK compatibility; async callers should use run_command_async."""
        def execute():
            return asyncio.run(self.run_command_async(command, shell, cwd, timeout))

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return execute()
        # Existing SDK callers may invoke this synchronous method inside a loop.
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(execute).result()

    async def run_command_async(self, command: str, shell: Optional[str] = None,
                                cwd: Optional[str] = None, timeout: float = 60) -> str:
        return await run_shell(command, shell=shell, cwd=cwd, timeout=timeout)

    async def run_local_command(self, command: str) -> str:
        """Execute an explicit user command without a model call, retaining context."""
        if not command.strip():
            return "Usage: !<command> (for example: !ls -la)"
        call = ToolCall(
            id=f"shell_{uuid4().hex}",
            function=ToolCallFunction(name="run_command", arguments=json.dumps({"command": command})),
        )
        self.messages.append(Message(role="user", content=f"!{command}"))
        self.messages.append(Message(role="assistant", tool_calls=[call]))
        try:
            result = await self.run_command_async(command)
        except asyncio.CancelledError:
            self.messages.append(ToolResult(tool_call_id=call.id, name="run_command",
                                            content="Command interrupted by user.", is_error=True).to_message())
            raise
        self.messages.append(ToolResult(tool_call_id=call.id, name="run_command", content=result).to_message())
        return result

    def read_file(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            return f"Error: File not found: {path}"
        try:
            return p.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"

    def write_file(self, path: str, content: str) -> str:
        p = Path(path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"Successfully wrote {len(content)} characters to {path}"
        except Exception as e:
            return f"Error writing file: {e}"

    # --- Agent Execution Loop ---

    def _build_full_system_prompt(self) -> str:
        prompt = self.base_system_prompt
        # Inject active skills
        skills_aug = self.skills.get_prompt_augmentation()
        if skills_aug:
            prompt += "\n" + skills_aug
        return prompt

    async def run(
        self,
        prompt: str,
        on_thought: Optional[Callable[[str], None]] = None,
        on_tool_start: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_tool_end: Optional[Callable[[str, str], None]] = None,
    ) -> str:
        """Run the agent loop until completion or max_iterations reached."""
        if prompt.lstrip().startswith("!"):
            return await self.run_local_command(prompt.lstrip()[1:].strip())

        if not self._is_initialized:
            await self.initialize()

        # Preprocess message with plugins
        processed_prompt = await self.plugins.dispatch_user_message(prompt)
        self.messages.append(Message(role="user", content=processed_prompt))

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            # Prepare message chain for LLM
            system_msg = Message(role="system", content=self._build_full_system_prompt())
            request_messages = [system_msg] + self.messages
            tools_schemas = self.tools.get_schemas()

            await self.plugins.dispatch_model_request(request_messages, tools_schemas)

            provider = self.providers.get_active()
            try:
                response = await provider.chat(
                    messages=request_messages,
                    tools=tools_schemas if tools_schemas else None,
                    temperature=self.temperature,
                )
            except Exception as e:
                await self.plugins.dispatch_error(e)
                raise

            # If model returned reasoning/thinking, notify callback
            if response.reasoning and on_thought:
                on_thought(response.reasoning)

            await self.plugins.dispatch_model_response(response)
            self.messages.append(response)

            # Check if model requested tool execution
            if not response.tool_calls:
                # No more tools needed; final answer produced
                return response.content or ""

            # Execute tool calls
            for tc in response.tool_calls:
                fn_name = tc.function.name
                args_dict = {}
                try:
                    args_dict = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except Exception:
                    pass

                if on_tool_start:
                    on_tool_start(fn_name, args_dict)

                await self.plugins.dispatch_tool_call(tc)
                result = await self.tools.execute(tc)
                await self.plugins.dispatch_tool_result(result)

                if on_tool_end:
                    on_tool_end(fn_name, result.content)

                # Append tool result to conversation
                self.messages.append(result.to_message())

        return "Agent reached maximum tool iterations without finishing."

    async def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages.clear()

    async def close(self) -> None:
        """Cleanup resources, disconnect MCP servers."""
        await self.mcp.shutdown()
