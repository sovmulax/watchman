from __future__ import annotations

from apps.configuration.models import AppConfiguration


def get_config() -> AppConfiguration:
    return AppConfiguration.load()


def update_config(**fields: object) -> AppConfiguration:
    config = AppConfiguration.load()
    for key, value in fields.items():
        if hasattr(config, key):
            setattr(config, key, value)
    config.save()
    return config

