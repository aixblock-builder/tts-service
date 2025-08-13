from __future__ import annotations
from typing import Any
from realtimetts_plugins import get_registry, get_plugin_class

class TTSFactory:
    @staticmethod
    def engines():
        return list(get_registry().keys())

    @staticmethod
    def create(engine_name: str, **engine_kwargs: Any):
        cls = get_plugin_class(engine_name)
        if not cls:
            raise KeyError(f"Engine '{engine_name}' không tồn tại. Engines: {TTSFactory.engines()}")
        return cls(**engine_kwargs)