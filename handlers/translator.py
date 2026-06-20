# ============================================================
#         StudyBuddyV3BOT — Translator Handler
#         Handles text translation feature
#         Powered by deep-translator (Google Translate)
# ============================================================

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import settings
from config.constants import BotState, EmojiConstants, LimitConstants
from keyboards.translator_kb import TranslatorKeyboard
from services.translation_service import TranslationService
from utils.logger import get_logger
from utils.helpers import (
    edit_or_send,
    answer_callback,
    sanitize_input,
)

logger = get_logger(__name__)


# ============================================================
#   TRANSLATOR HANDLER
# ============================================================

class TranslatorHandler:
    """
    Handles all text translation interactions.

    Features:
    - Translate text to any language
    - Quick language buttons (most common)
    - Custom language input
    - Auto-detect source language
    - Shows detected source language
    - Rate limiting via parent middleware
    """

    def __init__(self) -> None:
        self.translation_service = TranslationService()

    # ================================================================
    #   CALLBACK ROUTER
    # ================================================================

    async def handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Route all trans: callback queries.
        Pattern: trans:action:value

        Actions:
        - open:      Open translator menu
        - start:     Prompt for text input
        - lang:      Translate to specific language
        - custom:    Prompt for custom language
        - again:     Translate same text to different language
        - clear:     Clear and start over
        - back:      Return to main menu
        """
        query   = update.callback_query
        user_id = update.effective_user.id
        await query.answer()

        parts  = query.data.split(":")
        action = parts[1] if len(parts) > 1 else ""
        value  = parts[2] if len(parts) > 2 else ""

        logger.debug(
            f"Translator callback | User: {user_id} | "
            f"Action: {action} | Value: {value}"
        )

        if action == "open":
            await self._show_translator_menu(update, context)
        elif action == "start":
            await self._prompt_text_input(update, context)
        elif action == "lang":
            await self._translate_to(update, context, value)
        elif action == "custom":
            await self._prompt_custom_language(update, context)
        elif action == "again":
            await self._show_language_picker(update, context)
        elif action == "clear":
            context.user_data.pop("translation_text", None)
            context.user_data.pop("translation_result", None)
            context.user_data["state"] = BotState.IDLE
            await self._show_translator_menu(update, context)
        elif action == "back":
            await self._go_back(update, context)
        else:
            await self._show_translator_menu(update, context)

    # ================================================================
    #   TRANSLATOR MENU
    # ================================================================

    async def _show_translator_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Display the main translator menu."""
        text = (
            f"{EmojiConstants.TRANSLATOR} *Text Translator*\n"
            f"{'─' * 35}\n\n"
            f"Translate any text to 100+ languages\n"
            f"powered by Google Translate.\n\n"
            f"*How to use:*\n"
            f"  1️⃣ Tap *Translate Text*\n"
            f"  2️⃣ Send the text you want to translate\n"
            f"  3️⃣ Choose target language\n"
            f"  4️⃣ Get instant translation!\n\n"
            f"*Supported:*\n"
            f"  • Auto-detects source language\n"
            f"  • 100+ target languages\n"
            f"  • Up to "
            f"`{LimitConstants.MAX_TRANSLATION_LENGTH}` characters\n\n"
            f"_Tap below to get started!_"
        )

        keyboard = TranslatorKeyboard.translator_menu()
        await edit_or_send(update, context, text, keyboard)

    # ================================================================
    #   TEXT INPUT
    # ================================================================

    async def _prompt_text_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Prompt user to send text for translation."""
        context.user_data["state"] = BotState.AWAITING_TRANSLATION
        context.user_data.pop("translation_text",   None)
        context.user_data.pop("translation_result", None)

        text = (
            f"{EmojiConstants.TRANSLATOR} *Translate Text*\n"
            f"{'─' * 35}\n\n"
            f"📝 Send the text you want to translate.\n\n"
            f"_Examples:_\n"
            f"• _Hello, how are you?_\n"
            f"• _The mitochondria is the powerhouse of the cell_\n"
            f"• _Einstein's theory of relativity_\n\n"
            f"📏 Max: `{LimitConstants.MAX_TRANSLATION_LENGTH}` characters"
        )

        keyboard = TranslatorKeyboard.cancel_button()
        await edit_or_send(update, context, text, keyboard)

    async def handle_translation_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Process text input for translation.
        Called from main.py router when state = AWAITING_TRANSLATION.
        Shows language picker after receiving text.
        """
        user_id = update.effective_user.id
        text_in = update.message.text.strip()

        # Reset state
        context.user_data["state"] = BotState.IDLE

        # Validate
        if not text_in:
            await update.message.reply_text(
                f"{EmojiConstants.ERROR} Please send some text to translate."
            )
            return

        if len(text_in) > LimitConstants.MAX_TRANSLATION_LENGTH:
            await update.message.reply_text(
                f"{EmojiConstants.WARNING} Text too long.\n"
                f"Max `{LimitConstants.MAX_TRANSLATION_LENGTH}` "
                f"characters.\n"
                f"Your text: `{len(text_in)}` characters.",
                parse_mode="Markdown",
            )
            return

        # Sanitize and store
        text_in = sanitize_input(text_in)
        context.user_data["translation_text"] = text_in

        # Preview (first 100 chars)
        preview = text_in[:100] + ("..." if len(text_in) > 100 else "")

        prompt_text = (
            f"{EmojiConstants.TRANSLATOR} *Choose Target Language*\n"
            f"{'─' * 35}\n\n"
            f"📝 *Your text:*\n"
            f"_{preview}_\n\n"
            f"🌍 Select the language to translate to:"
        )

        keyboard = TranslatorKeyboard.language_picker()
        await update.message.reply_text(
            prompt_text,
            parse_mode=   "Markdown",
            reply_markup= keyboard,
        )

        logger.debug(
            f"Translation text received | "
            f"User: {user_id} | "
            f"Length: {len(text_in)}"
        )

    # ================================================================
    #   TRANSLATE
    # ================================================================

    async def _translate_to(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        target_lang: str,
    ) -> None:
        """
        Translate stored text to target language.

        Args:
            target_lang: Language code (e.g. 'hi', 'es', 'fr')
        """
        user_id   = update.effective_user.id
        text      = context.user_data.get("translation_text", "")

        if not text:
            await answer_callback(
                update.callback_query,
                text="⚠️ No text to translate. Please start over.",
                show_alert=True,
            )
            await self._show_translator_menu(update, context)
            return

        # Show processing message
        await update.callback_query.edit_message_text(
            f"{EmojiConstants.LOADING} _Translating..._",
            parse_mode="Markdown",
        )

        try:
            # Perform translation
            result = await self.translation_service.translate(
                text=        text,
                target_lang= target_lang,
            )

            if not result:
                raise ValueError("Empty translation result")

            # Store result
            context.user_data["translation_result"] = result.translated_text
            context.user_data["translation_lang"]   = target_lang

            # Get language display name
            lang_name = self.translation_service.get_language_name(
                target_lang
            )

            # Source language info
            source_info = ""
            if result.source_lang and result.source_lang != "auto":
                source_name = self.translation_service.get_language_name(
                    result.source_lang
                )
                source_info = f"🔍 Detected: _{source_name}_\n"

            # Original text preview
            original_preview = text[:150] + (
                "..." if len(text) > 150 else ""
            )

            response_text = (
                f"{EmojiConstants.TRANSLATOR} *Translation Result*\n"
                f"{'─' * 35}\n\n"
                f"📝 *Original:*\n"
                f"_{original_preview}_\n\n"
                f"🌍 *Translated to {lang_name}:*\n"
                f"{result.translated_text}\n\n"
                f"{'─' * 35}\n"
                f"{source_info}"
                f"📊 Characters: `{len(result.translated_text)}`"
            )

            keyboard = TranslatorKeyboard.after_translation()

            await update.callback_query.edit_message_text(
                response_text,
                parse_mode=   "Markdown",
                reply_markup= keyboard,
            )

            logger.info(
                f"✅ Translation done | "
                f"User: {user_id} | "
                f"Target: {target_lang} | "
                f"Length: {len(result.translated_text)}"
            )

        except Exception as e:
            logger.error(
                f"Translation error for user {user_id}: {e}"
            )

            error_text = (
                f"{EmojiConstants.ERROR} *Translation Failed*\n\n"
                f"Could not translate to `{target_lang}`.\n"
                f"Please try again or choose a different language."
            )

            keyboard = TranslatorKeyboard.retry_button()

            await update.callback_query.edit_message_text(
                error_text,
                parse_mode=   "Markdown",
                reply_markup= keyboard,
            )

    async def _show_language_picker(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Show language picker again (for translating same text
        to a different language).
        """
        text = context.user_data.get("translation_text", "")

        if not text:
            await self._show_translator_menu(update, context)
            return

        preview = text[:100] + ("..." if len(text) > 100 else "")

        prompt_text = (
            f"{EmojiConstants.TRANSLATOR} *Choose Another Language*\n"
            f"{'─' * 35}\n\n"
            f"📝 *Your text:*\n"
            f"_{preview}_\n\n"
            f"🌍 Select target language:"
        )

        keyboard = TranslatorKeyboard.language_picker()
        await edit_or_send(update, context, prompt_text, keyboard)

    async def _prompt_custom_language(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Prompt user to enter a custom language code.
        For languages not shown in quick buttons.
        """
        context.user_data["state"] = BotState.AWAITING_TARGET_LANG

        text = (
            f"{EmojiConstants.TRANSLATOR} *Custom Language*\n"
            f"{'─' * 35}\n\n"
            f"Enter the language name or code:\n\n"
            f"*Examples:*\n"
            f"  • `spanish` or `es`\n"
            f"  • `japanese` or `ja`\n"
            f"  • `portuguese` or `pt`\n"
            f"  • `russian` or `ru`\n"
            f"  • `chinese` or `zh-CN`\n"
            f"  • `korean` or `ko`\n\n"
            f"_Send the language name below:_"
        )

        keyboard = TranslatorKeyboard.cancel_button()
        await edit_or_send(update, context, text, keyboard)

    # ================================================================
    #   NAVIGATION
    # ================================================================

    async def _go_back(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Return to main menu."""
        context.user_data["state"] = BotState.IDLE
        context.user_data.pop("translation_text",   None)
        context.user_data.pop("translation_result", None)
        context.user_data.pop("translation_lang",   None)

        from handlers.start import StartHandler
        start_handler = StartHandler()
        await start_handler.handle_menu(update, context)