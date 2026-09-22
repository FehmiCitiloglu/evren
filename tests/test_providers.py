from __future__ import annotations
import pytest
from evren_agent.core.types import Message
from evren_agent.providers.evren import EvrenProvider, DEFAULT_EVREN_DIRECT_URL, DEFAULT_LLMTR_GATEWAY_URL
from evren_agent.providers.registry import ProviderRegistry


def test_evren_direct_provider_init():
    prov = EvrenProvider(
        api_key="test_key_123",
        base_url=DEFAULT_EVREN_DIRECT_URL,
        default_model="glm-5.3",
    )
    assert prov.name == "evren"
    assert prov.is_gateway is False
    assert prov.current_model == "glm-5.3"
    headers = prov._get_headers()
    assert headers["Authorization"] == "Bearer test_key_123"
    assert headers["X-API-Key"] == "test_key_123"


def test_evren_gateway_provider_init():
    prov = EvrenProvider(
        api_key="llmtr_key_456",
        base_url=DEFAULT_LLMTR_GATEWAY_URL,
    )
    assert prov.is_gateway is True
    assert prov.current_model == "evren/glm-5.3-fp8"
    headers = prov._get_headers()
    assert headers["Authorization"] == "Bearer llmtr_key_456"
    assert "X-API-Key" not in headers


def test_evren_payload_formatting():
    prov = EvrenProvider(api_key="key", default_model="glm-5.3")
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello Evren!"),
    ]
    tools = [
        {
            "type": "function",
            "function": {"name": "test_func", "parameters": {}},
        }
    ]

    payload = prov._prepare_payload(messages=messages, tools=tools, stream=True)
    assert payload["model"] == "glm-5.3"
    assert len(payload["messages"]) == 2
    assert payload["tools"] == tools
    assert payload["tool_choice"] == "auto"
    assert payload["stream"] is True


@pytest.mark.asyncio
async def test_evren_known_models():
    prov = EvrenProvider(api_key="key", base_url=DEFAULT_EVREN_DIRECT_URL)
    models = await prov.list_models()
    model_ids = [m.id for m in models]
    assert "glm-5.3" in model_ids
    assert "deepseek-v4-flash" in model_ids


def test_provider_registry():
    registry = ProviderRegistry()
    prov1 = EvrenProvider(name="evren", default_model="glm-5.3")
    prov2 = EvrenProvider(name="llmtr", base_url=DEFAULT_LLMTR_GATEWAY_URL)

    registry.register("evren", prov1)
    registry.register("llmtr", prov2)

    assert registry.active_name == "evren"
    assert registry.get_active() == prov1

    registry.set_active("llmtr")
    assert registry.active_name == "llmtr"
    assert registry.get_active() == prov2
