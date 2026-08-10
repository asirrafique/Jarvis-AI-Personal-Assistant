from jarvis.agent import plan_command


def test_weather_today():
    plan = plan_command(
        "What is the weather in Delhi?"
    )

    assert plan == [
        {
            "tool": "get_weather",
            "arguments": {
                "city": "Delhi",
                "days": 0,
            },
        }
    ]


def test_weather_tomorrow():
    plan = plan_command(
        "What is the weather in Delhi tomorrow?"
    )

    assert plan == [
        {
            "tool": "get_weather",
            "arguments": {
                "city": "Delhi",
                "days": 1,
            },
        }
    ]


def test_weather_day_after_tomorrow():
    plan = plan_command(
        "What is the weather in Delhi day after tomorrow?"
    )

    assert plan == [
        {
            "tool": "get_weather",
            "arguments": {
                "city": "Delhi",
                "days": 2,
            },
        }
    ]


def test_weather_multiple_days():
    plan = plan_command(
        "What is the weather in Kolkata tomorrow and the day after tomorrow?"
    )

    assert plan == [
        {
            "tool": "get_weather",
            "arguments": {
                "city": "Kolkata",
                "days": 1,
            },
        },
        {
            "tool": "get_weather",
            "arguments": {
                "city": "Kolkata",
                "days": 2,
            },
        },
    ]


def test_news():
    plan = plan_command(
        "Tell me the latest news"
    )

    assert plan == [
        {
            "tool": "get_news",
            "arguments": {},
        }
    ]


def test_weather_and_news():
    plan = plan_command(
        "Check the weather in Delhi and tell me the latest news"
    )

    assert plan == [
        {
            "tool": "get_weather",
            "arguments": {
                "city": "Delhi",
                "days": 0,
            },
        },
        {
            "tool": "get_news",
            "arguments": {},
        },
    ]


def test_time():
    plan = plan_command(
        "What time is it?"
    )

    assert plan == [
        {
            "tool": "get_time",
            "arguments": {},
        }
    ]


def test_date():
    plan = plan_command(
        "What is today's date?"
    )

    assert plan == [
        {
            "tool": "get_date",
            "arguments": {},
        }
    ]


def test_time_and_date():
    plan = plan_command(
        "What time is it and today's date?"
    )

    assert plan == [
        {
            "tool": "get_time",
            "arguments": {},
        },
        {
            "tool": "get_date",
            "arguments": {},
        },
    ]


def test_open_youtube():
    plan = plan_command(
        "Open YouTube"
    )

    assert plan == [
        {
            "tool": "open_website",
            "arguments": {
                "name": "youtube",
            },
        }
    ]


def test_play_music():
    plan = plan_command(
        "Play Believer"
    )

    assert plan == [
        {
            "tool": "play_music",
            "arguments": {
                "song": "Believer",
            },
        }
    ]


def test_open_youtube_and_play_music():
    plan = plan_command(
        "Open YouTube and play Believer"
    )

    assert plan == [
        {
            "tool": "open_website",
            "arguments": {
                "name": "youtube",
            },
        },
        {
            "tool": "play_music",
            "arguments": {
                "song": "Believer",
            },
        },
    ]


def test_play_music_and_open_youtube():
    plan = plan_command(
        "Play Believer and open YouTube"
    )

    assert plan == [
        {
            "tool": "open_website",
            "arguments": {
                "name": "youtube",
            },
        },
        {
            "tool": "play_music",
            "arguments": {
                "song": "Believer",
            },
        },
    ]


def test_memory_question_uses_no_tools():
    plan = plan_command(
        "What is my favorite programming language?"
    )

    assert plan == []