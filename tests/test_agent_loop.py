from __future__ import annotations
from typing import Any, AsyncIterator, Dict, List, Optional
import pytest

from evren_agent.core.agent import Agent
from evren_agent.core.types import (
    Message,
    ModelInfo,
    StreamChunk,
    ToolCall,
    ToolCallFunction,
)
from evren_agent.providers.base import BaseProvider


class MockAgentProvider(BaseProvider):
    """Deterministic mock provider that simulates multi-turn tool calling."""

    def __init__(self):
        super().__init__(name="mock", base_url="http://mock.local")
        self.call_count = 0

    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Message:
        self.call_count += 1

        # Check last message
        last_msg = messages[-1]

        if last_msg.role == "user":
            # Model decides to call calculate tool
            return Message(
                role="assistant",
                content=None,
                reasoning="Let me calculate this expression first.",
                tool_calls=[
                    ToolCall(
                        id="call_mock_1",
                        type="function",
                        function=ToolCallFunction(
                            name="calculate",
                            arguments='{"expression": "42 * 2"}',
                        ),
                    )
                ],
            )
        elif last_msg.role == "tool":
            # Model received tool result, yields final answer
            return Message(
                role="assistant",
                content=f"The calculated result is {last_msg.content}. Done!",
            )

        return Message(role="assistant", content="Finished.")

    async def chat_stream(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(delta_content="Stream not implemented in mock")

    async def list_models(self) -> List[ModelInfo]:
        return [ModelInfo(id="mock-v1", name="Mock Model V1")]


@pytest.mark.asyncio
async def test_agent_autonomous_loop():
    agent = Agent()
    mock_prov = MockAgentProvider()
    agent.providers.register("mock", mock_prov, set_active=True)

    await agent.initialize()

    thoughts_captured = []
    tools_called = []

    def on_thought(t):
        thoughts_captured.append(t)

    def on_tool_start(name, args):
        tools_called.append((name, args))

    response = await agent.run(
        prompt="What is 42 * 2?",
        on_thought=on_thought,
        on_tool_start=on_tool_start,
    )

    assert "The calculated result is 84" in response
    assert len(thoughts_captured) == 1
    assert "calculate" in thoughts_captured[0]
    assert len(tools_called) == 1
    assert tools_called[0][0] == "calculate"
    assert mock_prov.call_count == 2
    assert len(agent.messages) >= 3  # user, assistant tool_call, tool result, assistant final answer

    await agent.close()


@pytest.mark.asyncio
async def test_agent_meta_tools():
    agent = Agent()
    mock_prov = MockAgentProvider()
    agent.providers.register("mock", mock_prov, set_active=True)
    await agent.initialize()

    # 1. Test add_skill meta-tool
    res = agent.add_skill(
        name="test_meta_skill",
        description="Testing meta tool",
        instructions="Always write concise bullet points.",
    )
    assert "created and activated" in res
    assert "test_meta_skill" in [s["name"] for s in agent.list_skills()]

    # 2. Test file read/write meta-tools
    w_res = agent.write_file("test_scratch.txt", "Hello Evren Agent!")
    assert "Successfully wrote" in w_res
    r_res = agent.read_file("test_scratch.txt")
    assert r_res == "Hello Evren Agent!"

    # Clean up
    import os
    if os.path.exists("test_scratch.txt"):
        os.remove("test_scratch.txt")

    await agent.close()
