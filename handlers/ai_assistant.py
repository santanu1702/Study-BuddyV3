# ============================================================
#         StudyBuddyV3BOT — AI Assistant Handler
#         Handles all AI study assistant interactions
#         OpenAI GPT integration with context memory
# ============================================================

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from config.settings import settings
from config.constants import BotState, EmojiConstants, LimitConstants
from database.repositories import user_repo, admin_repo
from keyboards.main_menu import MainMenuKeyboard
from services.ai_service import AIService
from services.rate_limiter import RateLimiter
from locales.translator import get_text
from utils.logger import get_logger
from utils.helpers import (
    edit_or_send,
    answer_callback,
    split_long_message,
    sanitize_input,
)

logger = get_logger(__name__)


# ============================================================
#   AI ASSISTANT HANDLER
# ============================================================

class AIAssistantHandler:
    """
    Handles all AI study assistant interactions.

    Features:
    - OpenAI GPT-4o-mini integration
    - Per-user conversation context memory
    - Educational focus system prompt
    - Rate limiting (per-hour AI requests)
    - Typing indicator while processing
    - Long response splitting
    - Context clear option
    """

    def __init__(self) -> None:
        self.ai_service   = AIService()
        self.rate_limiter = RateLimiter()

    # ================================================================
    #   CALLBACK HANDLER
    #   Handles ai: prefixed inline button callbacks
    # ================================================================

    async def handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Route all ai: callback queries.
        Pattern: ai:action:optional_param
        """
        query   = update.callback_query
        user_id = update.effective_user.id
        await query.answer()

        parts  = query.data.split(":")
        action = parts[1] if len(parts) > 1 else ""

        logger.debug(
            f"AI callback | User: {user_id} | Action: {action}"
        )

        if action == "start":
            await self._show_ai_menu(update, context)
        elif action == "ask":
            await self._prompt_question(update, context)
        elif action == "clear_context":
            await self._clear_context(update, context)
        elif action == "back":
            await self._show_ai_menu(update, context)
        else:
            await self._show_ai_menu(update, context)

    # ================================================================
    #   AI MENU
    # ================================================================

    async def _show_ai_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Display the AI assistant menu."""
        user_id = update.effective_user.id
        lang    = context.user_data.get("language", settings.DEFAULT_LANGUAGE)

        # Get user's AI usage stats
        user = await user_repo.get_by_id(user_id)
        ai_requests = user.ai_requests if user else 0

        # Check remaining rate limit
        remaining = await self.rate_limiter.get_remaining_ai_requests(user_id)

        text = (
            f"{EmojiConstants.AI} *AI Study Assistant*\n"
            f"{'─' * 35}\n\n"
            f"I'm your personal AI tutor powered by GPT-4o-mini.\n\n"
            f"📚 I can help you with:\n"
            f"  • Explaining concepts\n"
            f"  • Solving problems\n"
            f"  • Summarizing topics\n"
            f"  • Answering questions\n"
            f"  • Study tips & strategies\n\n"
            f"📊 *Your Stats*\n"
            f"  Total AI Requests: `{ai_requests}`\n"
            f"  Remaining (this hour): `{remaining}`\n\n"
            f"_Just type your question or tap Ask below!_"
        )

        from keyboards.main_menu import MainMenuKeyboard
        keyboard = MainMenuKeyboard.ai_menu()
        await edit_or_send(update, context, text, keyboard)

    async def _prompt_question(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Set state to await AI question from user."""
        context.user_data["state"] = BotState.AWAITING_AI_QUESTION

        text = (
            f"{EmojiConstants.AI} *Ask AI Study Assistant*\n"
            f"{'─' * 35}\n\n"
            f"📝 Type your question below and I'll answer it!\n\n"
            f"_Examples:_\n"
            f"• _What is photosynthesis?_\n"
            f"• _Explain Newton's laws of motion_\n"
            f"• _Summarize the French Revolution_\n"
            f"• _How do I solve quadratic equations?_"
        )

        from keyboards.main_menu import MainMenuKeyboard
        keyboard = MainMenuKeyboard.cancel_button("ai:back")
        await edit_or_send(update, context, text, keyboard)

    # ================================================================
    #   MAIN QUESTION HANDLER
    # ================================================================

    async def handle_question(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Process a user's question and generate an AI response.
        Called from main.py text router when state = AWAITING_AI_QUESTION
        or as the default text handler (IDLE state).

        Flow:
        1. Validate input
        2. Check rate limit
        3. Show typing indicator
        4. Get AI response with context
        5. Update DB stats
        6. Send response
        """
        user_id  = update.effective_user.id
        question = update.message.text.strip()

        # ── Reset state ──
        context.user_data["state"] = BotState.IDLE

        # ── Input validation ──
        if not question:
            return

        if len(question) > LimitConstants.MAX_AI_QUESTION_LENGTH:
            await update.message.reply_text(
                f"{EmojiConstants.WARNING} Your question is too long.\n"
                f"Please keep it under "
                f"`{LimitConstants.MAX_AI_QUESTION_LENGTH}` characters.",
                parse_mode="Markdown",
            )
            return

        # Sanitize input
        question = sanitize_input(question)

        # ── Rate limit check ──
        is_limited, wait_time = await self.rate_limiter.check_ai_rate_limit(
            user_id
        )
        if is_limited:
            await update.message.reply_text(
                f"{EmojiConstants.WARNING} *AI Rate Limit Reached*\n\n"
                f"You've used your hourly AI request limit.\n"
                f"⏳ Please wait `{wait_time}` seconds before asking again.\n\n"
                f"_Limit: {settings.AI_RATE_LIMIT_PER_HOUR} requests/hour_",
                parse_mode="Markdown",
            )
            return

        # ── Show typing indicator ──
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

        # ── Send processing message ──
        processing_msg = await update.message.reply_text(
            f"{EmojiConstants.LOADING} _Thinking..._",
            parse_mode="Markdown",
        )

        try:
            # ── Get AI response ──
            response, usage = await self.ai_service.get_response(
                user_id=  user_id,
                question= question,
                language= context.user_data.get(
                    "language", settings.DEFAULT_LANGUAGE
                ),
            )

            # ── Delete processing message ──
            try:
                await processing_msg.delete()
            except Exception:
                pass

            # ── Update DB stats ──
            await user_repo.increment_ai_requests(user_id)

            if usage:
                await admin_repo.record_api_usage(
                    user_id=           user_id,
                    prompt_tokens=     usage.get("prompt_tokens", 0),
                    completion_tokens= usage.get("completion_tokens", 0),
                )

            # ── Send response (split if too long) ──
            parts = split_long_message(response)

            for i, part in enumerate(parts):
                # Add action buttons only on last part
                if i == len(parts) - 1:
                    from keyboards.main_menu import MainMenuKeyboard
                    keyboard = MainMenuKeyboard.ai_response_buttons()
                    await update.message.reply_text(
                        part,
                        parse_mode="Markdown",
                        reply_markup=keyboard,
                    )
                else:
                    await update.message.reply_text(
                        part,
                        parse_mode="Markdown",
                    )

            logger.info(
                f"🤖 AI response sent | "
                f"User: {user_id} | "
                f"Tokens: {usage.get('total_tokens', 0) if usage else 0}"
            )

        except Exception as e:
            # ── Delete processing message on error ──
            try:
                await processing_msg.delete()
            except Exception:
                pass

            error_msg = str(e).lower()

            if "rate limit" in error_msg:
                await update.message.reply_text(
                    f"{EmojiConstants.WARNING} *OpenAI Rate Limit*\n\n"
                    f"The AI service is temporarily busy.\n"
                    f"Please try again in a moment.",
                    parse_mode="Markdown",
                )
            elif "quota" in error_msg or "billing" in error_msg:
                await update.message.reply_text(
                    f"{EmojiConstants.ERROR} *AI Service Unavailable*\n\n"
                    f"The AI service is temporarily unavailable.\n"
                    f"Please try again later.",
                    parse_mode="Markdown",
                )
            else:
                await update.message.reply_text(
                    f"{EmojiConstants.ERROR} *Something went wrong*\n\n"
                    f"Could not get an AI response. Please try again.\n"
                    f"Use /start to return to the main menu.",
                    parse_mode="Markdown",
                )

            logger.error(
                f"AI response error for user {user_id}: {e}",
                exc_info=True,
            )

    # ================================================================
    #   CONTEXT MANAGEMENT
    # ================================================================

    async def _clear_context(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Clear the user's AI conversation context/memory.
        Starts a fresh conversation with the AI.
        """
        user_id = update.effective_user.id

        # Clear context in database
        success = await self.ai_service.clear_context(user_id)

        if success:
            text = (
                f"{EmojiConstants.SUCCESS} *Conversation Cleared*\n\n"
                f"Your AI conversation history has been reset.\n"
                f"_Starting fresh — ask me anything!_"
            )
        else:
            text = (
                f"{EmojiConstants.INFO} *Nothing to Clear*\n\n"
                f"No conversation history found.\n"
                f"_Ask me a question to get started!_"
            )

        from keyboards.main_menu import MainMenuKeyboard
        keyboard = MainMenuKeyboard.ai_menu()
        await edit_or_send(update, context, text, keyboard)

        logger.info(f"🗑️ AI context cleared for user {user_id}")
