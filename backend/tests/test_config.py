import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_accept_app_env_configuration_name() -> None:
    settings = Settings(_env_file=None, APP_ENV="test")

    assert settings.environment == "test"


def test_production_settings_require_explicit_host_and_origin() -> None:
    with pytest.raises(ValidationError, match="HTTPS production"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            SECRET_KEY="secure-test-secret-key-value-1234567890",
            allowed_hosts=["applymate.example.com"],
            cors_origins=["http://localhost:5173"],
        )


def test_production_settings_accept_deployment_configuration() -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="production",
        SECRET_KEY="secure-test-secret-key-value-1234567890",
        allowed_hosts=["applymate.example.com"],
        cors_origins=["https://applymate.example.com"],
    )

    assert settings.allowed_hosts == ["applymate.example.com"]
    assert settings.cors_origins == ["https://applymate.example.com"]
