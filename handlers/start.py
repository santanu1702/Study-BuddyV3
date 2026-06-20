# ============================================================
#         StudyBuddyV3BOT — Start Handler
#         Handles /start, /help, /menu, /cancel commands
#         Onboarding flow + main menu navigation
# ============================================================

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import settings
from config.constants import BotState, EmojiConstants
from database.repositories import user_repo
from keyboards.main_menu import MainMenuKeyboard
from handlers.language import LanguageHandler
from utils.logger import get_logger
from utils.helpers import edit_or_send, split_long_message

logger = get_logger(__name__)


# ============================================================
#   START HANDLER
# ============================================================

class StartHandler:
    """
    Handles all entry-point interactions.

    Features:
    - /start command with onboarding for new users
    - /help command with feature overview
    - /menu command to open main menu
    - /cancel to reset state
    - Main menu inline button navigation
    - Auto language detection on first start
    """

    # ================================================================
    #   /start COMMAND
    # ================================================================

    async def handle_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Handle /start command.

        Flow:
        1. Register or fetch user from DB
        2. Auto-detect language for new users
        3. Show welcome message
        4. Show main menu
        """
        tg_user = update.effective_user
        user_id = tg_user.id

        # Reset any active state
        context.user_data["state"] = BotState.IDLE

        # Get or create user in DB
        user, is_new = await user_repo.get_or_create(tg_user)

        # Auto-detect language for new users
        if is_new:
            lang = await LanguageHandler.auto_detect_and_set(
                update, context
            )
            logger.info(
                f"👋 New user registered | "
                f"ID: {user_id} | "
                f"Name: {user.display_name} | "
                f"Lang: {lang}"
            )
        else:
            # Load saved language preference
            lang = await LanguageHandler.load_user_language(
                update, context
            )
            logger.info(
                f"👤 Returning user | "
                f"ID: {user_id} | "
                f"Name: {user.display_name}"
            )

        # Update last active
        await user_repo.update_last_active(user_id)

        # Show appropriate welcome message
        if is_new:
            await self._send_welcome_new(update, context, user)
        else:
            await self._send_welcome_back(update, context, user)

    # ================================================================
    #   WELCOME MESSAGES
    # ================================================================

    async def _send_welcome_new(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user,
    ) -> None:
        """Send onboarding welcome message for new users."""
        name = user.display_name

        welcome_text = (
            f"{EmojiConstants.WAVE} *Welcome to StudyBuddyV3BOT!*\n"
            f"{'─' * 35}\n\n"
            f"Hello {name}! 👋\n\n"
            f"I'm your personal AI-powered study assistant.\n"
            f"Here's what I can do for you:\n\n"
            f"{EmojiConstants.AI} *AI Study Assistant*\n"
            f"  Ask me anything — I'll explain it clearly\n\n"
            f"{EmojiConstants.CALCULATOR} *Smart Calculator*\n"
            f"  Inline button calculator with advanced math\n\n"
            f"{EmojiConstants.TRANSLATOR} *Text Translator*\n"
            f"  Translate text to any language instantly\n\n"
            f"{EmojiConstants.NOTES} *Study Notes*\n"
            f"  Save, organize & manage your study notes\n\n"
            f"{EmojiConstants.LANGUAGE} *Multi-Language*\n"
            f"  Use the bot in your preferred language\n\n"
            f"{'─' * 35}\n"
            f"_Tap a button below to get started!_ 🚀"
        )

        keyboard = MainMenuKeyboard.main_menu()

        await update.message.reply_text(
            welcome_text,
            parse_mode=   "Markdown",
            reply_markup= keyboard,
        )

    async def _send_welcome_back(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user,
    ) -> None:
        """Send brief welcome back message for returning users."""
        name = user.display_name

        welcome_text = (
            f"{EmojiConstants.WAVE} *Welcome back, {name}!*\n\n"
            f"Good to see you again! 😊\n"
            f"What would you like to do today?\n\n"
            f"_Use the menu below to get started._"
        )

        keyboard = MainMenuKeyboard.main_menu()

        await update.message.reply_text(
            welcome_text,
            parse_mode=   "Markdown",
            reply_markup= keyboard,
        )

    # ================================================================
    #   /help COMMAND
    # ================================================================

    async def handle_help(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Handle /help command.
        Shows comprehensive feature guide.
        """
        help_text = (
            f"{EmojiConstants.HELP} *StudyBuddyV3BOT — Help Guide*\n"
            f"{'─' * 35}\n\n"

            f"*🤖 AI Study Assistant*\n"
            f"Ask any study question and get smart,\n"
            f"educational answers powered by GPT-4o-mini.\n"
            f"• Remembers conversation context\n"
            f"• Educational focus\n"
            f"• Rate limited: "
            f"{settings.AI_RATE_LIMIT_PER_HOUR} requests/hour\n\n"

            f"*🧮 Calculator*\n"
            f"Full inline button calculator.\n"
            f"• Basic: + - × ÷\n"
            f"• Advanced: sin, cos, tan, sqrt, log\n"
            f"• Constants: π, e\n\n"

            f"*🌐 Translator*\n"
            f"Translate text to any language.\n"
            f"• Supports 100+ languages\n"
            f"• Powered by Google Translate\n\n"

            f"*📚 Study Notes*\n"
            f"Save and manage your study notes.\n"
            f"• Up to {settings.MAX_NOTES_PER_USER} notes\n"
            f"• Auto-title from first line\n"
            f"• Search by keyword\n\n"

            f"*🌍 Languages*\n"
            f"Switch bot language anytime.\n"
            f"• 🇬🇧 English\n"
            f"• 🇮🇳 Hindi\n"
            f"• 🇧🇩 Bengali\n"
            f"• 🇸🇦 Arabic\n\n"

            f"{'─' * 35}\n"
            f"*Commands:*\n"
            f"  /start — Launch bot\n"
            f"  /menu  — Open main menu\n"
            f"  /help  — This help guide\n"
            f"  /cancel — Cancel current action\n"
            f"  /admin — Admin panel (admins only)\n\n"
            f"_All features accessible via inline buttons!_"
        )

        keyboard = MainMenuKeyboard.help_menu()

        await update.message.reply_text(
            help_text,
            parse_mode=   "Markdown",
            reply_markup= keyboard,
        )

    # ================================================================
    #   /menu COMMAND
    # ================================================================

    async def handle_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Handle /menu command or menu button press.
        Shows the main menu keyboard.
        """
        user_id = update.effective_user.id

        # Reset state when returning to menu
        context.user_data["state"] = BotState.IDLE

        text = (
            f"{EmojiConstants.ROCKET} *Main Menu*\n\n"
            f"_Select a feature below:_"
        )

        keyboard = MainMenuKeyboard.main_menu()

        if update.message:
            await update.message.reply_text(
                text,
                parse_mode=   "Markdown",
                reply_markup= keyboard,
            )
        elif update.callback_query:
            await edit_or_send(update, context, text, keyboard)

    # ================================================================
    #   /cancel COMMAND
    # ================================================================

    async def handle_cancel(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Handle /cancel command.
        Resets user state and returns to main menu.
        """
        user_id       = update.effective_user.id
        current_state = context.user_data.get("state", BotState.IDLE)

        # Reset all state
        context.user_data["state"] = BotState.IDLE

        # Clear any pending data
        for key in [
            "note_title",
            "broadcast_text",
            "broadcast_has_media",
            "broadcast_media_type",
            "broadcast_file_id",
            "calc_expr",
            "calc_result",
            "calc_fresh",
            "translation_text",
        ]:
            context.user_data.pop(key, None)

        if current_state == BotState.IDLE:
            cancel_text = (
                f"{EmojiConstants.INFO} Nothing to cancel.\n\n"
                f"_Use the menu below to get started._"
            )
        else:
            cancel_text = (
                f"{EmojiConstants.SUCCESS} *Action Cancelled*\n\n"
                f"_Returning to main menu..._"
            )

        keyboard = MainMenuKeyboard.main_menu()

        await update.message.reply_text(
            cancel_text,
            parse_mode=   "Markdown",
            reply_markup= keyboard,
        )

        logger.info(
            f"❌ Action cancelled | "
            f"User: {user_id} | "
            f"Previous state: {current_state}"
        )

    # ================================================================
    #   MENU CALLBACK HANDLER
    # ================================================================

    async def handle_menu_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Route all menu: callback queries.
        Pattern: menu:action

        Actions:
        - main:       Show main menu
        - home:       Return to main menu
        - help:       Show help
        - ai:         Open AI assistant
        - calc:       Open calculator
        - translator: Open translator
        - notes:      Open notes
        - language:   Open language settings
        """
        query   = update.callback_query
        user_id = update.effective_user.id
        await query.answer()

        parts  = query.data.split(":")
        action = parts[1] if len(parts) > 1 else "main"

        logger.debug(
            f"Menu callback | User: {user_id} | Action: {action}"
        )

        if action in ("main", "home", "back"):
            await self.handle_menu(update, context)

        elif action == "help":
            await self._show_help_inline(update, context)

        elif action == "ai":
            from handlers.ai_assistant import AIAssistantHandler
            handler = AIAssistantHandler()
            await handler._show_ai_menu(update, context)

        elif action == "calc":
            from handlers.calculator import CalculatorHandler
            handler = CalculatorHandler()
            await handler._open_calculator(update, context)

        elif action == "translator":
            from handlers.translator import TranslatorHandler
            handler = TranslatorHandler()
            await handler._show_translator_menu(update, context)

        elif action == "notes":
            from handlers.notes import NotesHandler
            handler = NotesHandler()
            await handler._show_notes_menu(update, context)

        elif action == "language":
            from handlers.language import LanguageHandler
            handler = LanguageHandler()
            await handler._show_language_menu(update, context)

        elif action == "cancel":
            context.user_data["state"] = BotState.IDLE
            await self.handle_menu(update, context)

        else:
            await self.handle_menu(update, context)

    # ================================================================
    #   HELP INLINE
    # ================================================================

    async def _show_help_inline(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Show help as an inline message (edits existing message)."""
        help_text = (
            f"{EmojiConstants.HELP} *Help Guide*\n"
            f"{'─' * 35}\n\n"
            f"{EmojiConstants.AI} *AI Assistant* — Ask study questions\n"
            f"{EmojiConstants.CALCULATOR} *Calculator* — Math operations\n"
            f"{EmojiConstants.TRANSLATOR} *Translator* — Translate text\n"
            f"{EmojiConstants.NOTES} *Notes* — Save study notes\n"
            f"{EmojiConstants.LANGUAGE} *Language* — Switch language\n\n"
            f"*Commands:*\n"
            f"  /start /menu /help /cancel\n\n"
            f"_Everything works via inline buttons!_"
        )

        keyboard = MainMenuKeyboard.help_menu()
        await edit_or_send(update, context, help_text, keyboard)
