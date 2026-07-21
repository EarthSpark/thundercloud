"""Runtime access to the configured metering provider."""


def configured_provider_url(default="", flask_app=None):
    """Return provider URL from the saved meter driver config."""
    try:
        from sparkmeter.config.provider_settings import get_enabled_provider

        if flask_app is not None:
            with flask_app.app_context():
                enabled_provider = get_enabled_provider()
                saved_url = ((enabled_provider or {}).get("base_url") or "").strip()
        else:
            enabled_provider = get_enabled_provider()
            saved_url = ((enabled_provider or {}).get("base_url") or "").strip()
        if saved_url:
            return saved_url
    except Exception:  # noqa: BLE001
        pass

    return default
