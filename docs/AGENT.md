# EVREN Agent — önceki agent modu kılavuzu

Doğrudan EVREN API komutları için [ana kılavuza](../README.md) bakın. Bu dosya agent/MCP/skill/plugin kullanımını anlatır.

An extensible, AI Agent framework designed with **Model Context Protocol (MCP)**, **modular Skills**, and **lifecycle Plugins**, with native first-class integration for **EVREN** (Savunma Sanayii Başkanlığı / SAYZEK) and **LLMTR Gateway**, as well as OpenAI-compatible providers.

---

## 🌟 Highlights

- 🇹🇷 **Native EVREN & LLMTR Integration**:
  - Direct EVREN platform: `https://evren-llmapi.ssyz.org.tr/v1`
  - LLMTR Gateway routing: `https://llmtr.com/v1` (documentation: [llmtr.com/docs/gateway/evren](https://llmtr.com/docs/gateway/evren/))
  - Full support for models: `glm-5.3`, `deepseek-v4-flash`, `qwen3.8-flash-next`, `gemma-4-31b`, `qwen3-vl-30b`, `auto` (and `evren/glm-5.3-fp8`, `evren/deepseek-v4-flash-tr` via LLMTR).
  - Real-time **reasoning stream extraction** (`delta.reasoning` / `delta.reasoning_content`) for thinking models.
  - Explicit Terms of Service status, text, and version acceptance (`/v1/terms/status`, `/v1/terms/text`, `/v1/terms/accept`).
- 🔌 **Model Context Protocol (MCP)**:
  - Connect to standard stdio and HTTP/SSE MCP servers dynamically.
  - Automatic JSON-RPC 2.0 handshake and tool discovery.
  - Prefixing and collision prevention across servers.
  - The agent itself can dynamically connect new MCP servers during its reasoning loop!
- 🧠 **Modular Skills System**:
  - Clean `SKILL.md` format with YAML frontmatter.
  - Active skills automatically inject specialized instructions into system prompts.
  - Create and activate skills on the fly via CLI or Python API.
- 🧩 **Extensible Plugins**:
  - Full lifecycle hooks: `on_user_message`, `on_model_request`, `on_model_response`, `on_tool_call`, `on_tool_result`, `on_error`.
  - Plugins can inject custom tools directly into the agent's tool registry.
  - Built-in plugins: `logger`, `calculator`, `web_search`.
- 💻 **Interactive CLI & REPL**:
  - Rich terminal formatting with syntax highlighting, thinking panels, and tool call audit trails.
  - Full slash commands: `/provider`, `/model`, `/mcp`, `/skill`, `/plugin`, `/tools`, `/terms`, `/clear`.

---

## 📦 Installation

```bash
# Clone and enter directory
cd /Users/alien/Development/evren

# Create virtual environment with uv or python
uv venv .venv
source .venv/bin/activate

# Install dependencies and editable package
uv pip install -e .
```

---

## ⚙️ Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```ini
# Direct EVREN endpoint
EVREN_API_KEY=evren_llm_your_key_here

# Or LLMTR Gateway endpoint (https://llmtr.com/v1)
LLMTR_API_KEY=llmtr-your_key_here

# Optional: Other providers
OPENAI_API_KEY=sk-...
```

You can customize defaults in `config.yaml`.

---

## 🖥️ Interactive CLI

Launch the interactive terminal session:

```bash
evren-agent
```

Or pass a single prompt directly:

```bash
evren-agent -p "Summarize the latest developments in Turkish AI"
```

Switch providers and models on startup:

```bash
evren-agent --provider llmtr --model evren/glm-5.3-fp8
```

### Slash Commands in REPL

| Command | Category | Description & Practical Example |
|---|---|---|
| `/help` | General | Show the categorized beneficial commands reference guide |
| `/status` | Diagnostics | Display full agent diagnostics (provider, model, tools, skills, message count) |
| `/provider [name]` | Providers | Switch or list providers (`/provider evren`, `/provider llmtr`, `/provider openai`) |
| `/model [name]` | Models | Switch active model (`/model glm-5.3`, `/model evren/glm-5.3-fp8`) or list models |
| `/mcp list` | MCP | Show connected MCP servers and their exposed tools |
| `/mcp add <name> <cmd> [args]` | MCP | Connect a stdio MCP server on the fly (`/mcp add telemetry python3 examples/mock_mcp_server.py`) |
| `/mcp remove <name>` | MCP | Disconnect an MCP server and unmount its tools |
| `/skill list` | Skills | View available skills and their active status |
| `/skill on <name>` / `/skill off` | Skills | Toggle skill prompt augmentation (`/skill on computer-use`, `/skill on code_assistant`) |
| `/skill info <name>` | Skills | Inspect full prompt instructions and tags of a skill |
| `/skill add` | Skills | Interactive wizard to create and persist a new skill with `SKILL.md` |
| `/plugin list` | Plugins | View loaded plugins, versions, and injected tools |
| `/plugin add <file.py>` | Plugins | Load a Python plugin dynamically (`/plugin add plugins/weather_plugin.py`) |
| `/tools` | Tools | List all registered tools, their parameters, and sources (`builtin`, `mcp`, `skill`, `plugin`) |
| `/api <command>` | EVREN | All direct API commands; `/api --help`, `/api quota`, `/api ocr --file scan.png` |
| `/terms text` | EVREN | Read the current terms before explicit acceptance |
| `/terms` | EVREN | Check EVREN direct endpoint terms of service status |
| `/terms accept <version>` | EVREN | Accept EVREN terms of service directly |
| `/history` | Session | View conversation turns summary and context stats |
| `/export [file.md]` | Session | Export conversation transcript with reasoning to Markdown |
| `/clear` | Session | Clear chat history and reset context window |
| `/exit`, `/quit` | Session | Safely disconnect MCP servers and exit the session |

---

## 🧩 Architecture Overview

```
evren/
├── evren_agent/
│   ├── core/
│   │   ├── agent.py          # Autonomous execution loop & meta-tools
│   │   ├── tools.py          # ToolRegistry & @tool decorator
│   │   └── types.py          # Message, ToolCall, StreamChunk types
│   ├── providers/
│   │   ├── base.py           # BaseProvider abstract class
│   │   ├── evren.py          # Direct EVREN & LLMTR Gateway provider
│   │   ├── openai_provider.py# OpenAI-compatible provider
│   │   └── registry.py       # ProviderRegistry for dynamic switching
│   ├── mcp/
│   │   ├── client.py         # MCP JSON-RPC 2.0 stdio & HTTP client
│   │   ├── manager.py        # Dynamic MCP server manager & tool mapper
│   │   └── protocol.py       # MCP schemas
│   ├── skills/
│   │   ├── skill.py          # Skill parser & directory serializer
│   │   └── manager.py        # Discovery, activation & prompt injection
│   └── plugins/
│       ├── base.py           # BasePlugin & lifecycle hooks
│       ├── manager.py        # Dynamic loader & hook dispatcher
│       └── builtins/         # logger, calculator, web_search
├── skills/                   # User custom skills
├── plugins/                  # User custom plugins
├── examples/                 # Python scripts & mock MCP server
└── tests/                    # Unit & integration test suite
```

---

## 🐍 Python SDK Usage

### 1. Basic Chat with EVREN

```python
import asyncio
from evren_agent import Agent

async def main():
    agent = Agent()
    await agent.initialize()

    response = await agent.run("Hello! What capabilities do you have?")
    print(response)

    await agent.close()

asyncio.run(main())
```

### 2. Dynamically Adding an MCP Server

```python
import asyncio
import sys
from evren_agent import Agent

async def main():
    agent = Agent()
    await agent.initialize()

    # Connect an MCP server (e.g. mock server or any stdio/npx tool)
    tools = await agent.mcp.add_server(
        name="system_tools",
        command=sys.executable,
        args=["examples/mock_mcp_server.py"],
    )
    print("Registered MCP tools:", tools)

    # Now the agent can autonomously call text_transformer or get_system_time!
    response = await agent.run("What is the current system time according to system_tools?")
    print(response)

    await agent.close()

asyncio.run(main())
```

### 3. Creating & Activating a Skill Dynamically

```python
import asyncio
from evren_agent import Agent

async def main():
    agent = Agent()
    await agent.initialize()

    # Add a specialized skill
    agent.skills.add_skill(
        name="defense_analyst",
        description="Turkish defense industry analysis specialist",
        instructions="Focus on unmanned systems (UAVs, USVs), sensor fusion, and sovereign algorithms.",
        tags=["defense", "sayzek"],
        activate=True,
    )

    response = await agent.run("Assess the significance of sovereign H200 AI clusters.")
    print(response)

    await agent.close()

asyncio.run(main())
```

### 4. Writing a Custom Plugin with Tools & Hooks

```python
from evren_agent.plugins.base import BasePlugin
from evren_agent.core.types import ToolDefinition

class TranslationPlugin(BasePlugin):
    name = "translator"
    description = "Provides language translation helper"

    def get_tools(self):
        tool_def = ToolDefinition(
            name="translate_phrase",
            description="Translate text to target language",
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "target_lang": {"type": "string"},
                },
                "required": ["text", "target_lang"],
            },
            source="plugin:translator",
        )
        return [(tool_def, lambda text, target_lang: f"[{target_lang}] {text}")]

    async def on_user_message(self, text: str):
        print(f"[Audit] User input: {text}")
        return text
```

---

## 🧪 Testing

Run the test suite with pytest:

```bash
uv pip install -e . pytest-asyncio
pytest tests/ -v
```
