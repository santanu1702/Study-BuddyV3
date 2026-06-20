# ============================================================
#         StudyBuddyV3BOT — Translation Service
#         Google Translate wrapper via deep-translator
#         Async-compatible with caching support
# ============================================================

import asyncio
from dataclasses import dataclass
from typing import Optional, Dict
from functools import lru_cache

from deep_translator import GoogleTranslator
from deep_translator.exceptions import (
    LanguageNotSupportedException,
    TranslationNotFound,
    RequestError,
)

from config.constants import LimitConstants, TimeConstants
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
#   TRANSLATION RESULT
#   Clean dataclass for translation output
# ============================================================

@dataclass
class TranslationResult:
    """
    Represents a translation result.

    Attributes:
        original_text:   Source text before translation
        translated_text: Translated output text
        source_lang:     Detected or specified source language
        target_lang:     Target language code
        success:         Whether translation succeeded
    """
    original_text:   str
    translated_text: str
    source_lang:     str
    target_lang:     str
    success:         bool = True


# ============================================================
#   LANGUAGE CODE MAP
#   Maps common language names to deep-translator codes
# ============================================================

LANGUAGE_NAME_MAP: Dict[str, str] = {
    # ── South Asian ──
    "hindi":      "hi",
    "bengali":    "bn",
    "urdu":       "ur",
    "punjabi":    "pa",
    "gujarati":   "gu",
    "marathi":    "mr",
    "tamil":      "ta",
    "telugu":     "te",
    "kannada":    "kn",
    "malayalam":  "ml",
    "sinhala":    "si",
    "nepali":     "ne",

    # ── East Asian ──
    "chinese":    "zh-CN",
    "mandarin":   "zh-CN",
    "japanese":   "ja",
    "korean":     "ko",

    # ── Middle East ──
    "arabic":     "ar",
    "persian":    "fa",
    "farsi":      "fa",
    "turkish":    "tr",
    "hebrew":     "he",
    "kurdish":    "ku",

    # ── European ──
    "english":    "en",
    "french":     "fr",
    "german":     "de",
    "spanish":    "es",
    "italian":    "it",
    "portuguese": "pt",
    "russian":    "ru",
    "dutch":      "nl",
    "polish":     "pl",
    "ukrainian":  "uk",
    "greek":      "el",
    "czech":      "cs",
    "swedish":    "sv",
    "norwegian":  "no",
    "danish":     "da",
    "finnish":    "fi",
    "hungarian":  "hu",
    "romanian":   "ro",
    "bulgarian":  "bg",
    "croatian":   "hr",
    "serbian":    "sr",
    "slovak":     "sk",
    "slovenian":  "sl",
    "latvian":    "lv",
    "lithuanian": "lt",
    "estonian":   "et",

    # ── Southeast Asian ──
    "indonesian": "id",
    "malay":      "ms",
    "vietnamese": "vi",
    "thai":       "th",
    "filipino":   "tl",
    "tagalog":    "tl",
    "burmese":    "my",
    "khmer":      "km",

    # ── African ──
    "swahili":    "sw",
    "yoruba":     "yo",
    "igbo":       "ig",
    "zulu":       "zu",
    "afrikaans":  "af",
    "amharic":    "am",
    "somali":     "so",

    # ── Americas ──
    "haitian":    "ht",

    # ── Central Asian ──
    "kazakh":     "kk",
    "uzbek":      "uz",
    "azerbaijani": "az",
    "georgian":   "ka",
    "armenian":   "hy",
}

# ── Language display names for UI ──
LANGUAGE_DISPLAY_NAMES: Dict[str, str] = {
    "en":    "🇬🇧 English",
    "hi":    "🇮🇳 Hindi",
    "bn":    "🇧🇩 Bengali",
    "ur":    "🇵🇰 Urdu",
    "ar":    "🇸🇦 Arabic",
    "fa":    "🇮🇷 Persian",
    "tr":    "🇹🇷 Turkish",
    "zh-CN": "🇨🇳 Chinese",
    "ja":    "🇯🇵 Japanese",
    "ko":    "🇰🇷 Korean",
    "fr":    "🇫🇷 French",
    "de":    "🇩🇪 German",
    "es":    "🇪🇸 Spanish",
    "it":    "🇮🇹 Italian",
    "pt":    "🇵🇹 Portuguese",
    "ru":    "🇷🇺 Russian",
    "nl":    "🇳🇱 Dutch",
    "pl":    "🇵🇱 Polish",
    "uk":    "🇺🇦 Ukrainian",
    "vi":    "🇻🇳 Vietnamese",
    "th":    "🇹🇭 Thai",
    "id":    "🇮🇩 Indonesian",
    "sw":    "🇰🇪 Swahili",
    "yo":    "🇳🇬 Yoruba",
    "af":    "🇿🇦 Afrikaans",
}


# ============================================================
#   TRANSLATION SERVICE
# ============================================================

class TranslationService:
    """
    Google Translate wrapper using deep-translator.

    Features:
    - Async-compatible (runs sync translator in executor)
    - Auto-detect source language
    - Language name to code resolution
    - In-memory result caching
    - Comprehensive error handling
    - 100+ supported languages
    """

    def __init__(self) -> None:
        # Simple in-memory cache: {(text, target): TranslationResult}
        self._cache: Dict[tuple, TranslationResult] = {}
        self._cache_max_size = 500     # Max cached translations

    # ================================================================
    #   MAIN TRANSLATE METHOD
    # ================================================================

    async def translate(
        self,
        text:        str,
        target_lang: str,
        source_lang: str = "auto",
    ) -> Optional[TranslationResult]:
        """
        Translate text to target language.
        Runs synchronous deep-translator in async executor.

        Args:
            text:        Text to translate
            target_lang: Target language code (e.g. "hi", "fr")
            source_lang: Source language code or "auto" for detection

        Returns:
            TranslationResult or None on failure
        """
        # ── Validate input ──
        if not text or not text.strip():
            return None

        if len(text) > LimitConstants.MAX_TRANSLATION_LENGTH:
            raise ValueError(
                f"Text too long. Max {LimitConstants.MAX_TRANSLATION_LENGTH} chars."
            )

        # ── Resolve language code ──
        target_code = self._resolve_language_code(target_lang)
        if not target_code:
            raise ValueError(f"Unsupported language: {target_lang}")

        # ── Check cache ──
        cache_key = (text[:100], target_code)
        if cache_key in self._cache:
            logger.debug(
                f"Translation cache hit | "
                f"Target: {target_code}"
            )
            return self._cache[cache_key]

        # ── Perform translation in executor ──
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._do_translate,
                text,
                target_code,
                source_lang,
            )

            if result:
                # ── Cache the result ──
                self._cache_result(cache_key, result)

            return result

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Translation error: {e}")
            raise

    def _do_translate(
        self,
        text:        str,
        target_lang: str,
        source_lang: str = "auto",
    ) -> Optional[TranslationResult]:
        """
        Synchronous translation using deep-translator.
        Called via run_in_executor for async compatibility.

        Args:
            text:        Text to translate
            target_lang: Resolved target language code
            source_lang: Source language code or "auto"

        Returns:
            TranslationResult or None
        """
        try:
            translator = GoogleTranslator(
                source= source_lang,
                target= target_lang,
            )

            translated = translator.translate(text)

            if not translated:
                logger.warning(
                    f"Empty translation result | "
                    f"Target: {target_lang}"
                )
                return None

            # Try to get detected source language
            detected_source = source_lang
            if source_lang == "auto":
                try:
                    detected_source = (
                        GoogleTranslator(source="auto", target=target_lang)
                        .detect(text) or "auto"
                    )
                except Exception:
                    detected_source = "auto"

            result = TranslationResult(
                original_text=   text,
                translated_text= translated,
                source_lang=     detected_source,
                target_lang=     target_lang,
                success=         True,
            )

            logger.info(
                f"✅ Translation done | "
                f"Source: {detected_source} → "
                f"Target: {target_lang} | "
                f"Length: {len(translated)}"
            )

            return result

        except LanguageNotSupportedException as e:
            logger.warning(f"Language not supported: {e}")
            raise ValueError(f"Language not supported: {target_lang}")

        except TranslationNotFound as e:
            logger.warning(f"Translation not found: {e}")
            return None

        except RequestError as e:
            logger.error(f"Translation request error: {e}")
            raise ConnectionError("Translation service unavailable")

        except Exception as e:
            logger.error(f"Unexpected translation error: {e}")
            raise

    # ================================================================
    #   LANGUAGE CODE RESOLUTION
    # ================================================================

    def _resolve_language_code(self, lang_input: str) -> Optional[str]:
        """
        Resolve a language input to a valid deep-translator code.
        Handles: direct codes, full names, partial names.

        Args:
            lang_input: Language name or code from user

        Returns:
            Resolved language code or None if not found

        Examples:
            "hi"      → "hi"
            "hindi"   → "hi"
            "FRENCH"  → "fr"
            "zh-CN"   → "zh-CN"
        """
        if not lang_input:
            return None

        # Normalize input
        normalized = lang_input.lower().strip()

        # ── Direct code match ──
        # Try as-is (e.g. "hi", "fr", "zh-CN")
        try:
            GoogleTranslator(source="auto", target=normalized)
            return normalized
        except Exception:
            pass

        # ── Name map lookup ──
        if normalized in LANGUAGE_NAME_MAP:
            return LANGUAGE_NAME_MAP[normalized]

        # ── Partial name match ──
        for name, code in LANGUAGE_NAME_MAP.items():
            if normalized in name or name in normalized:
                return code

        logger.warning(
            f"Could not resolve language code: {lang_input!r}"
        )
        return None

    # ================================================================
    #   LANGUAGE INFO
    # ================================================================

    def get_language_name(self, lang_code: str) -> str:
        """
        Get display name for a language code.

        Args:
            lang_code: Language code (e.g. "hi", "fr")

        Returns:
            Display name with flag emoji
        """
        return LANGUAGE_DISPLAY_NAMES.get(
            lang_code,
            f"🌐 {lang_code.upper()}"
        )

    def is_supported(self, lang_input: str) -> bool:
        """
        Check if a language is supported.

        Args:
            lang_input: Language name or code

        Returns:
            True if supported
        """
        return self._resolve_language_code(lang_input) is not None

    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get all supported languages with display names.

        Returns:
            Dict of {code: display_name}
        """
        return LANGUAGE_DISPLAY_NAMES.copy()

    # ================================================================
    #   CACHE MANAGEMENT
    # ================================================================

    def _cache_result(
        self,
        key:    tuple,
        result: TranslationResult,
    ) -> None:
        """
        Cache a translation result.
        Evicts oldest entries when cache is full.

        Args:
            key:    Cache key tuple
            result: TranslationResult to cache
        """
        # Evict oldest entries if cache is full
        if len(self._cache) >= self._cache_max_size:
            # Remove first 50 entries
            keys_to_remove = list(self._cache.keys())[:50]
            for k in keys_to_remove:
                del self._cache[k]

        self._cache[key] = result

    def clear_cache(self) -> None:
        """Clear all cached translations."""
        self._cache.clear()
        logger.info("🧹 Translation cache cleared")

    def get_cache_size(self) -> int:
        """Return number of cached translations."""
        return len(self._cache)