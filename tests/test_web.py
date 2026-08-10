from unittest.mock import Mock

import jarvis.agent as agent
from jarvis.tool_registry import execute_tool, validate_registry


# ============================================================
# REGISTRY
# ============================================================

def test_web_tools_are_registered():

    result = validate_registry()

    assert result["success"] is True

    assert "search_web" in result["tools"]
    assert "open_url" in result["tools"]


# ============================================================
# DETERMINISTIC PLANNING
# ============================================================

def test_search_web_plan():

    plan = agent.plan_command(
        "Search the web for React tutorials"
    )

    assert plan == [
        {
            "tool": "search_web",
            "arguments": {
                "query": "React tutorials",
                "max_results": 5,
            },
        }
    ]


def test_search_for_plan():

    plan = agent.plan_command(
        "Search for latest AI news"
    )

    assert plan == [
        {
            "tool": "search_web",
            "arguments": {
                "query": "latest AI news",
                "max_results": 5,
            },
        }
    ]


def test_open_url_plan():

    plan = agent.plan_command(
        "Open https://github.com"
    )

    assert plan == [
        {
            "tool": "open_url",
            "arguments": {
                "url": "https://github.com",
            },
        }
    ]


# ============================================================
# ARGUMENT VALIDATION
# ============================================================

def test_search_web_rejects_unknown_argument():

    result = execute_tool(
        "search_web",
        {
            "query": "Python",
            "bad_argument": True,
        },
    )

    assert result["success"] is False


def test_open_url_rejects_unknown_argument():

    result = execute_tool(
        "open_url",
        {
            "url": "https://github.com",
            "bad_argument": True,
        },
    )

    assert result["success"] is False


# ============================================================
# URL VALIDATION
# ============================================================

def test_open_url_rejects_invalid_scheme():

    result = execute_tool(
        "open_url",
        {
            "url": "javascript:alert(1)",
        },
    )

    assert result["success"] is False


def test_open_url_rejects_missing_domain():

    result = execute_tool(
        "open_url",
        {
            "url": "https://",
        },
    )

    assert result["success"] is False