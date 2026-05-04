from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

MY_LANGUAGES = {"ms", "en"}


def detect_language(text: str) -> str:
    """Return 'en', 'ms', or 'bilingual'. Falls back to 'en' on error."""
    try:
        from langdetect import DetectorFactory, detect
        DetectorFactory.seed = 0
        lang = detect(text[:2000])
        if lang in MY_LANGUAGES:
            return lang
        return "en"
    except Exception:
        logger.warning("Language detection failed, defaulting to 'en'")
        return "en"


def detect_bilingual(text: str) -> str:
    """Sample multiple windows; if both EN and MS detected → 'bilingual'."""
    try:
        from langdetect import DetectorFactory, detect
        DetectorFactory.seed = 0
        window = len(text) // 3
        langs = set()
        for i in range(3):
            sample = text[i * window: (i + 1) * window]
            if sample.strip():
                langs.add(detect(sample[:1000]))
        if "ms" in langs and "en" in langs:
            return "bilingual"
        if "ms" in langs:
            return "ms"
        return "en"
    except Exception:
        return "en"
