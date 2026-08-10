from unittest.mock import patch

import jarvis.agent as agent
from jarvis.tool_registry import TOOLS, execute_tool


def test_system_tools_registered():
    assert "open_app" in TOOLS
    assert "open_folder" in TOOLS
    assert "open_file" in TOOLS


def test_open_app_plan():
    plan = agent.plan_command("Open VS Code")
    assert plan == [
        {
            "tool": "open_app",
            "arguments": {"name": "vs code"},
        }
    ]


def test_open_downloads_plan():
    plan = agent.plan_command("Open my Downloads folder")
    assert plan == [
        {
            "tool": "open_folder",
            "arguments": {"path": "downloads"},
        }
    ]


def test_open_project_folder_plan():
    plan = agent.plan_command("Open project folder")
    assert plan == [
        {
            "tool": "open_folder",
            "arguments": {"path": "project folder"},
        }
    ]


def test_open_file_plan():
    plan = agent.plan_command('Open "notes.txt"')
    assert plan == [
        {
            "tool": "open_file",
            "arguments": {"path": "notes.txt"},
        }
    ]


def test_system_tools_do_not_break_existing_plans():
    assert agent.plan_command("Open YouTube") == [
        {
            "tool": "open_website",
            "arguments": {"name": "youtube"},
        }
    ]

    assert agent.plan_command("Open YouTube and play Believer") == [
        {
            "tool": "open_website",
            "arguments": {"name": "youtube"},
        },
        {
            "tool": "play_music",
            "arguments": {"song": "Believer"},
        },
    ]


def test_open_app_validation_rejects_unknown_argument():
    result = execute_tool("open_app", {"name": "chrome", "bad": True})
    assert result["success"] is False


def test_open_folder_validation_rejects_unknown_argument():
    result = execute_tool("open_folder", {"path": "downloads", "bad": True})
    assert result["success"] is False