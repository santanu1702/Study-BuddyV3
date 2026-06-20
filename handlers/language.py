# ============================================================
#         StudyBuddyV3BOT — Language Handler
#         Handles language detection & manual switching
#         Stores preference in MongoDB per user
# ============================================================

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import settings
from config.constants import Language, EmojiConstants
from database.repositories import user_repo
from keyboards.language_kb import LanguageKeyboard
from locales.translator import get_text, set_user_language
from utils.logger import get_logger
from utils.helpers import edit_or_send, answer_callback

logger = get_logger(__name__)


# ============================================================
#   LANGUAGE HANDLER
# ============================================================

class LanguageHandler:
    """
    Handles all language selection and switching interactions.

    Features:
    - Auto-detect language from Telegram user settings
    - Manual language switch via inline buttons
    - Persist language preference in MongoDB
    - Update context.user_data for session
    - Supports: English, Hindi, Bengali, Arabic
    """

    # ================================================================
    #   CALLBACK ROUTER
    # ================================================================

    async def handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Route all lang: callback queries.
        Pattern: lang:action:value

        Actions:
        - open:   Show language selection menu
        - set:    Set language to specified code
        - back:   Return to main menu
        """
        query   = update.callback_query
        user_id = update.effective_user.id
        await query.answer()

        parts  = query.data.split(":")
        action = parts[1] if len(parts) > 1 else ""
        value  = parts[2] if len(parts) > 2 else ""

        logger.debug(
            f"Language callback | User: {user_id} | "
            f"Action: {action} | Value: {value}"
        )

        if action == "open":
            await self._show_language_menu(update, context)
        elif action == "set":
            await self._set_language(update, context, value)
        elif action == "back":
            await self._go_back(update, context)
        else:
            await self._show_language_menu(update, context)

    # ================================================================
    #   LANGUAGE MENU
    # ================================================================

    async def _show_language_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Display the language selection menu.
        Highlights the currently active language.
        """
        user_id      = update.effective_user.id
        current_lang = context.user_data.get(
            "language", settings.DEFAULT_LANGUAGE
        )

        # Get display name for current language
        lang_names    = Language.display_names()
        current_name  = lang_names.get(current_lang, "🇬🇧 English")

        text = (
            f"{EmojiConstants.LANGUAGE} *Language Settings*\n"
            f"{'─' * 35}\n\n"
            f"🌍 Current Language: {current_name}\n\n"
            f"Select your preferred language below.\n"
            f"The bot interface will switch immediately.\n\n"
            f"_Supported languages:_\n"
            f"  🇬🇧 English\n"
            f"  🇮🇳 हिंदी (Hindi)\n"
            f"  🇧🇩 বাংলা (Bengali)\n"
            f"  🇸🇦 العربية (Arabic)"
        )

        keyboard = LanguageKeyboard.language_selection(
            current_lang=current_lang
        )

        await edit_or_send(update, context, text, keyboard)

    # ================================================================
    #   SET LANGUAGE
    # ================================================================

    async def _set_language(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        lang_code: str,
    ) -> None:
        """
        Set user's language preference.

        Steps:
        1. Validate language code
        2. Update context.user_data (session)
        3. Save to MongoDB (persistent)
        4. Show confirmation message in new language
        """
        user_id = update.effective_user.id

        # Validate language code
        valid_codes = Language.choices()
        if lang_code not in valid_codes:
            await answer_callback(
                update.callback_query,
                text=f"⚠️ Unsupported language: {lang_code}",
                show_alert=True,
            )
            return

        # Check if already set to this language
        current_lang = context.user_data.get(
            "language", settings.DEFAULT_LANGUAGE
        )
        if current_lang == lang_code:
            await answer_callback(
                update.callback_query,
                text="✅ Already set to this language!",
                show_alert=False,
            )
            return

        # ── Update session ──
        context.user_data["language"] = lang_code

        # ── Persist to database ──
        success = await user_repo.update_language(
            user_id=  user_id,
            language= lang_code,
        )

        if not success:
            logger.warning(
                f"Failed to persist language {lang_code} "
                f"for user {user_id}"
            )

        # ── Get display info for new language ──
        lang_names   = Language.display_names()
        lang_display = lang_names.get(lang_code, lang_code)

        # ── Confirmation messages per language ──
        confirmations = {
            "en": (
                f"✅ *Language Changed!*\n\n"
                f"Language set to: {lang_display}\n\n"
                f"_The bot will now respond in English._"
            ),
            "hi": (
                f"✅ *भाषा बदली गई!*\n\n"
                f"भाषा सेट की गई: {lang_display}\n\n"
                f"_बॉट अब हिंदी में जवाब देगा।_"
            ),
            "bn": (
                f"✅ *ভাষা পরিবর্তন হয়েছে!*\n\n"
                f"ভাষা সেট করা হয়েছে: {lang_display}\n\n"
                f"_বট এখন বাংলায় উত্তর দেবে।_"
            ),
            "ar": (
                f"✅ *تم تغيير اللغة!*\n\n"
                f"تم ضبط اللغة على: {lang_display}\n\n"
                f"_سيرد البوت الآن باللغة العربية._"
            ),
        }

        confirmation_text = confirmations.get(
            lang_code, confirmations["en"]
        )

        keyboard = LanguageKeyboard.after_selection(lang_code)

        await edit_or_send(
            update, context, confirmation_text, keyboard
        )

        logger.info(
            f"🌍 Language changed | "
            f"User: {user_id} | "
            f"Language: {lang_code}"
        )

    # ================================================================
    #   AUTO-DETECT
    # ================================================================

    @staticmethod
    async def auto_detect_and_set(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> str:
        """
        Auto-detect and set language from Telegram user settings.
        Called during /start registration for new users.

        Returns:
            Detected language code (falls back to DEFAULT_LANGUAGE)
        """
        tg_user   = update.effective_user
        user_id   = tg_user.id
        tg_lang   = tg_user.language_code or ""

        # Map Telegram language code to supported language
        detected = Language.from_telegram_code(tg_lang).value

        # Set in session
        context.user_data["language"] = detected

        # Persist to DB (non-blocking — ignore failures)
        try:
            await user_repo.update_language(
                user_id=  user_id,
                language= detected,
            )
        except Exception as e:
            logger.warning(
                f"Could not auto-persist language for {user_id}: {e}"
            )

        logger.debug(
            f"🌍 Auto-detected language | "
            f"User: {user_id} | "
            f"TG code: {tg_lang!r} → {detected}"
        )

        return detected

    @staticmethod
    async def load_user_language(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> str:
        """
        Load user's saved language preference from DB into session.
        Called by auth middleware on every update.

        Returns:
            User's language code
        """
        user_id = update.effective_user.id

        # Already in session — use it
        if "language" in context.user_data:
            return context.user_data["language"]

        # Load from DB
        try:
            user = await user_repo.get_by_id(user_id)
            if user:
                lang = user.language_code or settings.DEFAULT_LANGUAGE
                context.user_data["language"] = lang
                return lang
        except Exception as e:
            logger.warning(
                f"Could not load language for user {user_id}: {e}"
            )

        # Fallback to default
        lang = settings.DEFAULT_LANGUAGE
        context.user_data["language"] = lang
        return lang

    # ================================================================
    #   NAVIGATION
    # ================================================================

    async def _go_back(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Return to the main menu."""
        from keyboards.main_menu import MainMenuKeyboard
        from handlers.start import StartHandler

        start_handler = StartHandler()
        await start_handler.handle_menu(update, context)