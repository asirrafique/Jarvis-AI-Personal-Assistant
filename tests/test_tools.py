from jarvis.tool_registry import (
    execute_tool,
    get_tool_descriptions,
    validate_registry,
)


def test_registry_is_valid():
    result = validate_registry()

    assert result["success"] is True
    assert result["tool_count"] == 11

    expected_tools = {
    "open_website",
    "play_music",
    "open_app",
    "open_folder",
    "open_file",
    "get_news",
    "get_weather",
    "get_time",
    "get_date",
    "search_web",
    "open_url",
}

    assert set(result["tools"]) == expected_tools


def test_tool_descriptions():
    tools = get_tool_descriptions()

    names = {
        tool["tool"]
        for tool in tools
    }

    assert "open_website" in names
    assert "play_music" in names
    assert "get_news" in names
    assert "get_weather" in names
    assert "get_time" in names
    assert "get_date" in names


def test_weather_today():
    result = execute_tool(
        "get_weather",
        {
            "city": "Delhi",
            "days": 0,
        },
    )

    assert result["success"] is True
    assert result["city"] == "Delhi"
    assert result["days"] == 0


def test_weather_tomorrow():
    result = execute_tool(
        "get_weather",
        {
            "city": "Delhi",
            "days": 1,
        },
    )

    assert result["success"] is True
    assert result["city"] == "Delhi"
    assert result["days"] == 1


def test_weather_day_after_tomorrow():
    result = execute_tool(
        "get_weather",
        {
            "city": "Delhi",
            "days": 2,
        },
    )

    assert result["success"] is True
    assert result["city"] == "Delhi"
    assert result["days"] == 2


def test_time():
    result = execute_tool(
        "get_time",
        {},
    )

    assert result["success"] is True
    assert "time" in result


def test_date():
    result = execute_tool(
        "get_date",
        {},
    )

    assert result["success"] is True
    assert "date" in result


def test_unknown_tool():
    result = execute_tool(
        "does_not_exist",
        {},
    )

    assert result["success"] is False


def test_invalid_weather_arguments():
    result = execute_tool(
        "get_weather",
        {
            "city": "Delhi",
            "days": -1,
        },
    )

    assert result["success"] is False


def test_unknown_argument_rejected():
    result = execute_tool(
        "get_time",
        {
            "something": "wrong",
        },
    )

    assert result["success"] is False