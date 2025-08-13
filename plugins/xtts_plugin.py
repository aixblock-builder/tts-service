from __future__ import annotations
from typing import Any
from tts_plugin_base import BaseTTSPlugin, register_plugin

try:
    from RealtimeTTS import CoquiEngine
except Exception as e:  # pragma: no cover
    raise ImportError("Cần RealtimeTTS với CoquiEngine cho XTTS") from e

@register_plugin
class XTTSPlugin(BaseTTSPlugin):
    @classmethod
    def key(cls) -> str:
        return "xtts"

    def build_engine(self) -> Any:
        kwargs = dict(model="xtts", **self.engine_kwargs)
        return CoquiEngine(**kwargs)