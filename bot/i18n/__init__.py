"""Internationalisation package. Main entry point: t(key, lang, **kwargs)."""
from .translator import t, SUPPORTED_LANGS, detect_lang

__all__ = ["t", "SUPPORTED_LANGS", "detect_lang"]
