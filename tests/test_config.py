from jarvis.config import (
    get_public_config,
    validate_config,
)


def test_config_validation_structure():

    result = validate_config()

    assert isinstance(
        result,
        dict,
    )

    assert "success" in result
    assert "environment" in result
    assert "model" in result
    assert "news_api_configured" in result
    assert "errors" in result


def test_public_config_hides_secret():

    config = get_public_config()

    assert "NEWS_API_KEY" not in config
    assert "news_api_key" not in config

    assert (
        "news_api_configured"
        in config
    )


def test_model_exists():

    config = get_public_config()

    assert config[
        "ollama_model"
    ]


def test_http_timeout_positive():

    config = get_public_config()

    assert (
        config["http_timeout"]
        > 0
    )