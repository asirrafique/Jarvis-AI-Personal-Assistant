import jarvis.agent as agent
import jarvis.tool_registry as registry


def test_execute_plan_rejects_non_list():
    assert agent.execute_plan(None) == []
    assert agent.execute_plan({"tool": "get_time"}) == []


def test_execute_plan_skips_bad_step_and_continues(monkeypatch):
    calls = []

    def fake_execute(tool, arguments):
        calls.append(tool)
        return {"success": True, "message": "ok"}

    monkeypatch.setattr(agent, "execute_tool", fake_execute)

    results = agent.execute_plan([
        "bad-step",
        {"tool": "get_time", "arguments": {}},
    ])

    assert results[0]["result"]["success"] is False
    assert results[1]["result"]["success"] is True
    assert calls == ["get_time"]


def test_execute_plan_tool_failure_does_not_stop_next_tool(monkeypatch):
    calls = []

    def fake_execute(tool, arguments):
        calls.append(tool)
        if tool == "first":
            raise RuntimeError("simulated failure")
        return {"success": True, "message": "second completed"}

    monkeypatch.setattr(agent, "execute_tool", fake_execute)

    results = agent.execute_plan([
        {"tool": "first", "arguments": {}},
        {"tool": "second", "arguments": {}},
    ])

    assert results[0]["result"]["success"] is False
    assert "simulated failure" in results[0]["result"]["error"]
    assert results[1]["result"]["success"] is True
    assert calls == ["first", "second"]


def test_execute_tool_unknown_tool_is_safe():
    result = registry.execute_tool("does_not_exist", {})
    assert result["success"] is False
    assert "does not exist" in result["error"]


def test_execute_tool_rejects_unknown_argument():
    result = registry.execute_tool("get_time", {"unexpected": 1})
    assert result["success"] is False
    assert "Unknown argument" in result["error"]


def test_execute_tool_converts_tool_exception_to_failure(monkeypatch):
    def broken_tool():
        raise RuntimeError("boom")

    monkeypatch.setitem(registry.TOOLS, "broken_test_tool", {
        "function": broken_tool,
        "description": "test tool",
        "arguments": {},
    })

    try:
        result = registry.execute_tool("broken_test_tool", {})
        assert result["success"] is False
        assert "boom" in result["error"]
    finally:
        registry.TOOLS.pop("broken_test_tool", None)


def test_planner_exception_fails_closed(monkeypatch):
    def broken_planner(command):
        raise RuntimeError("planner down")

    monkeypatch.setattr(agent, "plan_command", broken_planner)
    monkeypatch.setattr(agent, "resolve_command", lambda command: command)
    monkeypatch.setattr(agent, "_memory_text_for", lambda command: agent.NO_MEMORY_TEXT)

    result = agent.run_agent("Do something unusual")

    assert isinstance(result, str)
    assert result


def test_final_response_exception_uses_fallback(monkeypatch):
    monkeypatch.setattr(agent, "resolve_command", lambda command: command)
    monkeypatch.setattr(agent, "_memory_text_for", lambda command: agent.NO_MEMORY_TEXT)
    monkeypatch.setattr(agent, "plan_command", lambda command: [
        {"tool": "get_time", "arguments": {}}
    ])
    monkeypatch.setattr(agent, "execute_plan", lambda plan: [{
        "tool": "get_time",
        "arguments": {},
        "result": {"success": True, "time": "10:00 PM"},
    }])
    monkeypatch.setattr(
        agent,
        "generate_final_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("formatter down")),
    )

    result = agent.run_agent("What time is it?")

    assert result == "The current time is 10:00 PM."