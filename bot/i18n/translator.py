"""Core translator — t(key, lang, **kwargs) returns formatted string."""
from loguru import logger

from . import ru, en

SUPPORTED_LANGS: tuple[str, ...] = ("ru", "en")
_DEFAULT_LANG = "ru"

_REGISTRY: dict[str, dict[str, str]] = {
    "ru": ru.TEXTS,
    "en": en.TEXTS,
}

# Telegram language_code → bot lang
_TG_LANG_MAP: dict[str, str] = {
    "ru": "ru",
    "be": "ru",  # Belarusian → Russian
    "uk": "ru",  # Ukrainian → Russian
    "kk": "ru",  # Kazakh → Russian
    "en": "en",
    "en-us": "en",
    "en-gb": "en",
}


def detect_lang(tg_language_code: str | None) -> str:
    """Map Telegram language_code to supported bot language."""
    if not tg_language_code:
        return _DEFAULT_LANG
    code = tg_language_code.lower()
    return _TG_LANG_MAP.get(code, "en")  # unknown → English


def t(key: str, lang: str = "ru", **kwargs: object) -> str:
    """
    Get translated string by key for given language.
    Falls back to Russian if key not found in target language.
    Formats with **kwargs if provided.
    """
    if lang not in _REGISTRY:
        lang = _DEFAULT_LANG

    texts = _REGISTRY[lang]
    text = texts.get(key)

    if text is None:
        # Fallback to Russian
        text = _REGISTRY[_DEFAULT_LANG].get(key)
        if text is None:
            logger.warning("Missing i18n key '{}' for lang='{}'", key, lang)
            return f"[{key}]"
        logger.debug("i18n fallback to 'ru' | key='{}' lang='{}'", key, lang)

    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError as e:
            logger.error("i18n format error | key='{}' missing={}", key, e)
            return text

    return text
