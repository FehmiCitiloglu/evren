from __future__ import annotations
import argparse
import asyncio
import json
import logging
import sys
import shlex
from typing import Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from evren_agent.core.agent import Agent

console = Console()


def print_banner(agent: Agent) -> None:
    prov = agent.providers.get_active()
    active_skills = [s.name for s in agent.skills.skills.values() if s.is_active]
    mcp_count = len(agent.mcp.clients)
    plugins_count = len(agent.plugins.plugins)

    content = f"""[bold cyan]EVREN Agent[/bold cyan] — Extensible AI with MCP, Skills & Plugins
[green]Provider:[/green] [bold]{prov.name}[/bold] ([dim]{prov.base_url}[/dim])
[green]Model:[/green]    [bold yellow]{prov.current_model}[/bold yellow]
[green]Skills:[/green]   {', '.join(active_skills) or '[dim]none[/dim]'}
[green]MCPs:[/green]     {mcp_count} servers connected
[green]Plugins:[/green]  {plugins_count} active
[dim]Type [bold]/help[/bold] for commands or start chatting below.[/dim]"""

    console.print(Panel(content, title="🚀 EvrenAgent", border_style="cyan"))


def print_help() -> None:
    """Displays categorized beneficial commands with practical examples."""
    console.print(
        Panel(
            "[bold cyan]EVREN Agent — Command Center[/bold cyan]\n"
            "[dim]Manage providers, models, MCP servers, skills, plugins, and session diagnostics.[/dim]",
            border_style="cyan",
        )
    )

    # 1. Providers & Models
    p_table = Table(title="🌐 Providers & Models", border_style="blue", show_header=True, header_style="bold blue")
    p_table.add_column("Command", style="bold cyan", no_wrap=True)
    p_table.add_column("Description & Beneficial Usage Example")
    p_table.add_row("/provider", "Show current active provider and list of available providers")
    p_table.add_row("/provider evren", "Switch to direct EVREN endpoint [dim](https://evren-llmapi.ssyz.org.tr/v1)[/dim]")
    p_table.add_row("/provider llmtr", "Switch to LLMTR Gateway [dim](https://llmtr.com/v1 - zero-margin EVREN routing)[/dim]")
    p_table.add_row("/provider openai", "Switch to OpenAI or OpenAI-compatible endpoint")
    p_table.add_row("/model", "Query and list available models for the current provider")
    p_table.add_row("/model <id>", "Switch active model (e.g. [bold yellow]/model glm-5.3[/bold yellow], [bold yellow]/model deepseek-v4-flash[/bold yellow])")
    console.print(p_table)

    # 2. Model Context Protocol (MCP)
    m_table = Table(title="🔌 Model Context Protocol (MCP)", border_style="green", show_header=True, header_style="bold green")
    m_table.add_column("Command", style="bold cyan", no_wrap=True)
    m_table.add_column("Description & Beneficial Usage Example")
    m_table.add_row("/mcp list", "List all connected MCP servers and their discovered tools")
    m_table.add_row(
        "/mcp add <name> <cmd> [args]",
        "Connect a new stdio MCP server on the fly.\n"
        "[dim]Example:[/dim] [italic]/mcp add telemetry python3 examples/mock_mcp_server.py[/italic]\n"
        "[dim]Example:[/dim] [italic]/mcp add git npx -y @modelcontextprotocol/server-git[/italic]",
    )
    m_table.add_row("/mcp remove <name>", "Disconnect an MCP server and unmount its tools cleanly")
    console.print(m_table)

    # 3. Skills (Instruction Augmentation)
    s_table = Table(title="🧠 Skills & Specialized Knowledge", border_style="magenta", show_header=True, header_style="bold magenta")
    s_table.add_column("Command", style="bold cyan", no_wrap=True)
    s_table.add_column("Description & Beneficial Usage Example")
    s_table.add_row("/skill list", "List all available skills and their active/inactive status")
    s_table.add_row("/skill on <name>", "Activate a skill (e.g. [bold yellow]/skill on code_assistant[/bold yellow], [bold yellow]/skill on computer-use[/bold yellow], or [bold yellow]/skill on research_analyst[/bold yellow])")
    s_table.add_row("/skill off <name>", "Deactivate a skill to remove its prompt augmentation")
    s_table.add_row("/skill info <name>", "Inspect full prompt instructions and tags of a skill")
    s_table.add_row("/skill add", "Interactive wizard to create and persist a new skill with [italic]SKILL.md[/italic]")
    console.print(s_table)

    # 4. Plugins & Tools
    t_table = Table(title="🧩 Plugins & Tool Management", border_style="yellow", show_header=True, header_style="bold yellow")
    t_table.add_column("Command", style="bold cyan", no_wrap=True)
    t_table.add_column("Description & Beneficial Usage Example")
    t_table.add_row("/plugin list", "List active plugins, versions, and injected tools")
    t_table.add_row("/plugin add <file.py>", "Dynamically load a python plugin (e.g. [italic]/plugin add plugins/weather_plugin.py[/italic])")
    t_table.add_row("/tools", "Inspect all registered tools, their sources ([italic]builtin, mcp, skill, plugin[/italic]), and schemas")
    console.print(t_table)

    # 5. Diagnostics & Session Controls
    d_table = Table(title="⚙️ Session, Diagnostics & Utilities", border_style="red", show_header=True, header_style="bold red")
    d_table.add_column("Command", style="bold cyan", no_wrap=True)
    d_table.add_column("Description & Beneficial Usage Example")
    d_table.add_row("/status", "Display complete agent diagnostics (provider, model, tools, skills, memory)")
    d_table.add_row("/terms", "Check EVREN terms of service status [dim](GET /v1/terms/status)[/dim]")
    d_table.add_row("/api <command>", "All direct API commands: /api --help, /api quota, /api ocr --file scan.png")
    d_table.add_row("/terms text", "Read the current terms before accepting")
    d_table.add_row("/terms accept <version>", "Explicitly accept the terms version you have read")
    d_table.add_row("/history", "View message history turns and context stats")
    d_table.add_row("/export [file.md]", "Export conversation transcript to a Markdown file [dim](default: session_export.md)[/dim]")
    d_table.add_row("/clear", "Clear conversation history and reset context window")
    d_table.add_row("/exit, /quit", "Safely disconnect all MCP servers and exit the session")
    console.print(d_table)


async def handle_slash_command(agent: Agent, cmd: str) -> bool:
    """Returns True if command was handled, False if user wants to exit."""
    parts = cmd.strip().split()
    root = parts[0].lower()

    if root in ("/exit", "/quit"):
        return False

    if root == "/help":
        print_help()

    elif root == "/api":
        from evren_agent.api.cli import run as run_api
        from evren_agent.providers.evren import EvrenProvider
        prov = agent.providers.get_active()
        if not isinstance(prov, EvrenProvider) or prov.is_gateway:
            console.print("[yellow]Direct API commands require /provider evren.[/yellow]")
        else:
            try:
                await run_api(shlex.split(cmd)[1:], api_key=prov.api_key or "", base_url=prov.base_url,
                              default_model=prov.current_model)
            except SystemExit:
                pass  # argparse help/errors must not terminate the REPL.

    elif root == "/status":
        prov = agent.providers.get_active()
        active_skills = [s.name for s in agent.skills.skills.values() if s.is_active]
        mcp_servers = agent.mcp.list_servers()
        plugins = agent.plugins.list_plugins()
        all_tools = agent.tools.list_tools()

        info = f"""[bold cyan]Agent Status & Diagnostics[/bold cyan]
• [bold]Name:[/bold] {agent.name}
• [bold]Active Provider:[/bold] [green]{prov.name}[/green] ([dim]{prov.base_url}[/dim])
• [bold]Active Model:[/bold] [bold yellow]{prov.current_model}[/bold yellow]
• [bold]Conversation Turns:[/bold] {len(agent.messages)} messages in context
• [bold]Active Skills ({len(active_skills)}):[/bold] {', '.join(active_skills) or '[dim]none[/dim]'}
• [bold]Connected MCP Servers ({len(mcp_servers)}):[/bold] {', '.join([s['name'] for s in mcp_servers]) or '[dim]none[/dim]'}
• [bold]Loaded Plugins ({len(plugins)}):[/bold] {', '.join([p['name'] for p in plugins]) or '[dim]none[/dim]'}
• [bold]Total Registered Tools:[/bold] {len(all_tools)} tools ready
"""
        console.print(Panel(info, title="🔍 System Diagnostics", border_style="cyan"))

    elif root == "/history":
        if not agent.messages:
            console.print("[dim]No messages in current conversation.[/dim]")
        else:
            table = Table(title="Conversation History", border_style="dim")
            table.add_column("#", justify="right", style="dim")
            table.add_column("Role", style="bold")
            table.add_column("Content Preview / Tool Calls")

            for idx, msg in enumerate(agent.messages, 1):
                role_style = "cyan" if msg.role == "user" else "green" if msg.role == "assistant" else "yellow"
                desc = msg.content[:80] + ("..." if msg.content and len(msg.content) > 80 else "")
                if msg.tool_calls:
                    tc_names = [tc.function.name for tc in msg.tool_calls]
                    desc = f"[magenta]Tool Calls: {', '.join(tc_names)}[/magenta]"
                elif msg.role == "tool":
                    desc = f"[dim][{msg.name}][/dim] {desc}"
                table.add_row(str(idx), f"[{role_style}]{msg.role}[/{role_style}]", desc or "[dim]empty[/dim]")
            console.print(table)

    elif root == "/export":
        filename = parts[1] if len(parts) > 1 else "session_export.md"
        try:
            lines = [
                f"# Evren Agent Session Export",
                f"- Provider: {agent.providers.active_name}",
                f"- Model: {agent.providers.get_active().current_model}",
                f"- Total Messages: {len(agent.messages)}\n",
                "---\n",
            ]
            for m in agent.messages:
                lines.append(f"### {m.role.upper()}\n")
                if m.reasoning:
                    lines.append(f"> **Reasoning / Thought:**\n> {m.reasoning}\n")
                if m.content:
                    lines.append(f"{m.content}\n")
                if m.tool_calls:
                    lines.append("**Tool Calls:**")
                    for tc in m.tool_calls:
                        lines.append(f"- `{tc.function.name}({tc.function.arguments})`")
                    lines.append("")
                lines.append("---\n")

            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            console.print(f"[green]Successfully exported session to [bold]{filename}[/bold][/green]")
        except Exception as e:
            console.print(f"[red]Error exporting session: {e}[/red]")

    elif root == "/provider":
        if len(parts) == 1:
            curr = agent.providers.active_name
            all_p = agent.providers.list_providers()
            console.print(f"[cyan]Active provider:[/cyan] [bold]{curr}[/bold]")
            console.print(f"[dim]Available providers: {', '.join(all_p)}[/dim]")
        else:
            target = parts[1]
            try:
                prov = agent.providers.set_active(target)
                console.print(f"[green]Switched provider to [bold]{prov.name}[/bold] (model: {prov.current_model})[/green]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    elif root == "/model":
        prov = agent.providers.get_active()
        if len(parts) == 1:
            console.print(f"[cyan]Current model for {prov.name}:[/cyan] [bold yellow]{prov.current_model}[/bold yellow]")
            try:
                models = await prov.list_models()
                console.print("[dim]Known models:[/dim]")
                for m in models:
                    console.print(f"  • [bold]{m.id}[/bold] - {m.name}")
            except Exception as e:
                console.print(f"[dim]Could not query remote models: {e}[/dim]")
        else:
            new_model = parts[1]
            prov.set_model(new_model)
            console.print(f"[green]Model set to [bold yellow]{new_model}[/bold yellow] for provider {prov.name}[/green]")

    elif root == "/mcp":
        sub = parts[1] if len(parts) > 1 else "list"
        if sub == "list":
            servers = agent.mcp.list_servers()
            if not servers:
                console.print("[yellow]No MCP servers currently connected. Connect with: /mcp add <name> <cmd> [args...][/yellow]")
            else:
                table = Table(title="Connected MCP Servers")
                table.add_column("Name", style="bold cyan")
                table.add_column("Type")
                table.add_column("Command / URL")
                table.add_column("Exposed Tools", style="green")
                for s in servers:
                    table.add_row(
                        s["name"],
                        s["type"],
                        str(s.get("command") or s.get("url")),
                        ", ".join(s.get("tools", [])) or "[dim]none[/dim]",
                    )
                console.print(table)

        elif sub == "add":
            if len(parts) < 4:
                console.print("[yellow]Usage: /mcp add <name> <command> [args...][/yellow]")
            else:
                s_name = parts[2]
                s_cmd = parts[3]
                s_args = parts[4:]
                with console.status(f"[cyan]Connecting MCP server '{s_name}'...[/cyan]"):
                    try:
                        tools = await agent.mcp.add_server(name=s_name, command=s_cmd, args=s_args)
                        console.print(f"[green]Connected MCP server '{s_name}'. Registered tools: {', '.join(tools)}[/green]")
                    except Exception as e:
                        console.print(f"[red]Failed connecting to MCP server: {e}[/red]")

        elif sub == "remove":
            if len(parts) < 3:
                console.print("[yellow]Usage: /mcp remove <name>[/yellow]")
            else:
                s_name = parts[2]
                ok = await agent.mcp.remove_server(s_name)
                if ok:
                    console.print(f"[green]Removed MCP server '{s_name}'.[/green]")
                else:
                    console.print(f"[red]MCP server '{s_name}' not found.[/red]")

    elif root == "/skill":
        sub = parts[1] if len(parts) > 1 else "list"
        if sub == "list":
            skills = agent.skills.list_skills()
            table = Table(title="Skills")
            table.add_column("Status", justify="center")
            table.add_column("Name", style="bold cyan")
            table.add_column("Description")
            table.add_column("Tags", style="dim")

            for s in skills:
                status = "[green]ACTIVE[/green]" if s["is_active"] else "[dim]INACTIVE[/dim]"
                table.add_row(status, s["name"], s["description"], ", ".join(s["tags"]))
            console.print(table)

        elif sub == "on" and len(parts) > 2:
            s_name = parts[2]
            if agent.skills.activate_skill(s_name):
                console.print(f"[green]Activated skill '{s_name}'.[/green]")
            else:
                console.print(f"[red]Skill '{s_name}' not found.[/red]")

        elif sub == "off" and len(parts) > 2:
            s_name = parts[2]
            if agent.skills.deactivate_skill(s_name):
                console.print(f"[yellow]Deactivated skill '{s_name}'.[/yellow]")
            else:
                console.print(f"[red]Skill '{s_name}' not found.[/red]")

        elif sub == "info" and len(parts) > 2:
            s_name = parts[2]
            skill = agent.skills.get_skill(s_name)
            if skill:
                content = f"[bold cyan]Skill:[/bold cyan] {skill.name} (Active: {skill.is_active})\n"
                content += f"[bold]Description:[/bold] {skill.description}\n"
                content += f"[bold]Tags:[/bold] {', '.join(skill.tags) or 'none'}\n\n"
                content += f"[bold]Instructions:[/bold]\n{skill.instructions}"
                console.print(Panel(content, title=f"Skill: {skill.name}", border_style="magenta"))
            else:
                console.print(f"[red]Skill '{s_name}' not found.[/red]")

        elif sub == "add":
            name = Prompt.ask("[cyan]Skill name[/cyan]")
            desc = Prompt.ask("[cyan]Short description[/cyan]")
            console.print("[dim]Enter instructions (end with empty line):[/dim]")
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            instructions = "\n".join(lines)
            agent.skills.add_skill(name, desc, instructions, activate=True)
            console.print(f"[green]Created and activated skill '{name}'.[/green]")

    elif root == "/plugin":
        sub = parts[1] if len(parts) > 1 else "list"
        if sub == "list":
            plugins = agent.plugins.list_plugins()
            table = Table(title="Plugins")
            table.add_column("Name", style="bold cyan")
            table.add_column("Version", style="dim")
            table.add_column("Description")
            table.add_column("Tools", style="green")
            for p in plugins:
                table.add_row(
                    p["name"],
                    p["version"],
                    p["description"],
                    ", ".join(p["tools"]) or "[dim]none[/dim]",
                )
            console.print(table)

        elif sub == "add" and len(parts) > 2:
            f_path = parts[2]
            try:
                p = agent.plugins.load_plugin_from_file(f_path)
                if p:
                    console.print(f"[green]Loaded plugin '{p.name}'.[/green]")
                else:
                    console.print(f"[red]No valid plugin class found in {f_path}[/red]")
            except Exception as e:
                console.print(f"[red]Error loading plugin: {e}[/red]")

    elif root == "/tools":
        tools = agent.tools.list_tools()
        table = Table(title="Registered Tools")
        table.add_column("Name", style="bold cyan")
        table.add_column("Source", style="dim")
        table.add_column("Description")

        for t in tools:
            table.add_row(t.name, t.source, t.description)
        console.print(table)

    elif root == "/terms":
        prov = agent.providers.get_active()
        from evren_agent.providers.evren import EvrenProvider
        if isinstance(prov, EvrenProvider) and not prov.is_gateway:
            sub = parts[1] if len(parts) > 1 else "status"
            if sub == "accept":
                with console.status("Accepting EVREN terms..."):
                    try:
                        if len(parts) < 3:
                            raise ValueError("Read /terms text, then use /terms accept <version>.")
                        ver = int(parts[2])
                        res = await prov.accept_terms(ver)
                        console.print(Panel(json.dumps(res, indent=2), title=f"Accepted Terms ({ver})"))
                    except Exception as e:
                        console.print(f"[red]Error accepting terms: {e}[/red]")
            else:
                with console.status("Checking EVREN terms status..."):
                    try:
                        res = await prov.get_terms_text() if sub == "text" else await prov.check_terms_status()
                        console.print(Panel(json.dumps(res, indent=2), title="EVREN Terms Status"))
                    except Exception as e:
                        console.print(f"[red]Error checking terms: {e}[/red]")
        else:
            console.print("[yellow]Active provider is not an EVREN provider.[/yellow]")

    elif root == "/clear":
        await agent.clear_history()
        console.print("[yellow]Conversation history cleared.[/yellow]")

    else:
        console.print(f"[yellow]Unknown command: {root}. Type /help for options.[/yellow]")

    return True


async def run_repl(agent: Agent) -> None:
    await agent.initialize()
    print_banner(agent)

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You[/bold green]").strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                keep_going = await handle_slash_command(agent, user_input)
                if not keep_going:
                    console.print("[cyan]Goodbye![/cyan]")
                    break
                continue

            # Call agent run
            thought_buffer = []

            def on_thought(thought_text: str):
                thought_buffer.append(thought_text)
                console.print(Panel(thought_text, title="🧠 Evren Thinking", border_style="magenta", expand=False))

            def on_tool_start(tool_name: str, args: dict):
                console.print(f"🔧 [cyan]Calling tool:[/cyan] [bold]{tool_name}[/bold] [dim]({json.dumps(args)})[/dim]")

            def on_tool_end(tool_name: str, result: str):
                preview = result[:200] + ("..." if len(result) > 200 else "")
                console.print(f"✅ [green]Tool result [{tool_name}]:[/green] [dim]{preview}[/dim]")

            with console.status("[bold cyan]Evren is thinking...[/bold cyan]"):
                response = await agent.run(
                    prompt=user_input,
                    on_thought=on_thought,
                    on_tool_start=on_tool_start,
                    on_tool_end=on_tool_end,
                )

            console.print("\n[bold cyan]EvrenAgent:[/bold cyan]")
            console.print(Markdown(response))

        except (KeyboardInterrupt, EOFError):
            console.print("\n[cyan]Session terminated. Goodbye![/cyan]")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

    await agent.close()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        from evren_agent.api.cli import main as api_main
        raise SystemExit(api_main(sys.argv[2:]))
    parser = argparse.ArgumentParser(description="EVREN Agent CLI", epilog="Direct API commands: evren-agent api --help (or evren --help)")
    parser.add_argument("--prompt", "-p", type=str, help="Single-shot prompt to execute")
    parser.add_argument("--provider", type=str, help="Provider name (evren, llmtr, openai)")
    parser.add_argument("--model", "-m", type=str, help="Model ID")
    parser.add_argument("--config", "-c", type=str, help="Path to config.yaml")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    agent = Agent(config_path=args.config)

    if args.provider:
        agent.providers.set_active(args.provider)
    if args.model:
        agent.providers.get_active().set_model(args.model)

    if args.prompt:
        # Single-shot execution
        async def run_single():
            await agent.initialize()
            response = await agent.run(args.prompt)
            print(response)
            await agent.close()

        asyncio.run(run_single())
    else:
        # Interactive REPL
        asyncio.run(run_repl(agent))


if __name__ == "__main__":
    main()
