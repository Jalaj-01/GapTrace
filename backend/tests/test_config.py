"""Tests for application configuration and environment variables."""

from backend.app.core.config import Settings


def test_settings_defaults():
    """Verify settings defaults are sane."""
    settings = Settings()
    assert settings.PROJECT_NAME == "Scientific Paper Gap Finder"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.PORT == 8000
    assert isinstance(settings.CORS_ORIGINS, list)
    assert len(settings.CORS_ORIGINS) > 0


def test_cors_origins_parsing():
    """Verify CORS origins field validator converts strings or lists properly."""
    settings = Settings(CORS_ORIGINS="http://localhost:3000,http://example.com")
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    assert "http://example.com" in settings.CORS_ORIGINS
