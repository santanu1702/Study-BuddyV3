# ============================================================
#         StudyBuddyV3BOT — Main Entry Point
#         Production-ready async Telegram bot startup
# ============================================================

import asyncio
import sys
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is in sys.path (important for Render.com deployment)
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.error import TelegramError

# ---------------------------------------------------------------------------
# Internal imports — config, database, handlers, middlewares, logger
# ---------------------------------------------------------------------------
from config.settings import settings
from config.constants import BotState

from database.connection import db_manager

from handlers.start import StartHandler
from handlers.ai_assistant import AIAssistantHandler
from handlers.calculator import CalculatorHandler
from handlers.translator import TranslatorHandler
from handlers.notes import NotesHandler
from handlers.language import LanguageHandler
from handlers.admin import AdminHandler

from middlewares.auth_middleware import AuthMiddleware
from middlewares.rate_limit_middleware import RateLimitMiddleware
from middlewares.maintenance_middleware import MaintenanceMiddleware

from utils.logger import setup_logger, get_logger

# ---------------------------------------------------------------------------
# Setup logger first — everything depends on it
# ---------------------------------------------------------------------------
setup_logger()
logger = get_logger(__name__)


# ============================================================
#   BOT APPLICATION BUILDER
# ============================================================

def build_application() -> Application:
    """
    Build and configure the Telegram Application instance.
    Sets up all handlers, middlewares, and bot settings.
    """
    logger.info("🔧 Building bot application...")

    # ------------------------------------------------------------------
    # Build the Application with job queue enabled (for reminders etc.)
    # ------------------------------------------------------------------
    app = (
        Application.builder()
        .token(settings.BOT_TOKEN)
        .concurrent_updates(True)           # Handle multiple updates simultaneously
        .connect_timeout(30)                # Connection timeout
        .read_timeout(30)                   # Read timeout
        .write_timeout(30)                  # Write timeout
        .pool_timeout(30)                   # Connection pool timeout
        .build()
    )

    # ------------------------------------------------------------------
    # Initialize handler instances
    # ------------------------------------------------------------------
    start_handler     = StartHandler()
    ai_handler        = AIAssistantHandler()
    calc_handler      = CalculatorHandler()
    translator_handler = TranslatorHandler()
    notes_handler     = NotesHandler()
    lang_handler      = LanguageHandler()
    admin_handler     = AdminHandler()

    # ------------------------------------------------------------------
    # Initialize middleware instances
    # ------------------------------------------------------------------
    auth_mw        = AuthMiddleware()
    rate_limit_mw  = RateLimitMiddleware()
    maintenance_mw = MaintenanceMiddleware()

    # ------------------------------------------------------------------
    # Register middlewares on the application
    # Order matters: maintenance → auth → rate_limit
    # ------------------------------------------------------------------
    app.add_handler(
        MessageHandler(filters.ALL, maintenance_mw.process), group=-3
    )
    app.add_handler(
        MessageHandler(filters.ALL, auth_mw.process), group=-2
    )
    app.add_handler(
        MessageHandler(filters.ALL, rate_limit_mw.process), group=-1
    )

    # ------------------------------------------------------------------
    # ── COMMAND HANDLERS ──
    # ------------------------------------------------------------------
    app.add_handler(CommandHandler("start",   start_handler.handle_start))
    app.add_handler(CommandHandler("help",    start_handler.handle_help))
    app.add_handler(CommandHandler("menu",    start_handler.handle_menu))
    app.add_handler(CommandHandler("cancel",  start_handler.handle_cancel))

    # Admin commands (restricted inside handler)
    app.add_handler(CommandHandler("admin",   admin_handler.handle_admin_command))

    # ------------------------------------------------------------------
    # ── CALLBACK QUERY HANDLERS (Inline Buttons) ──
    # Grouped by prefix for clean routing
    # ------------------------------------------------------------------

    # Main menu navigation
    app.add_handler(CallbackQueryHandler(
        start_handler.handle_menu_callback,
        pattern=r"^menu:"
    ))

    # AI Assistant callbacks
    app.add_handler(CallbackQueryHandler(
        ai_handler.handle_callback,
        pattern=r"^ai:"
    ))

    # Calculator callbacks
    app.add_handler(CallbackQueryHandler(
        calc_handler.handle_callback,
        pattern=r"^calc:"
    ))

    # Translator callbacks
    app.add_handler(CallbackQueryHandler(
        translator_handler.handle_callback,
        pattern=r"^trans:"
    ))

    # Notes callbacks
    app.add_handler(CallbackQueryHandler(
        notes_handler.handle_callback,
        pattern=r"^notes:"
    ))

    # Language switch callbacks
    app.add_handler(CallbackQueryHandler(
        lang_handler.handle_callback,
        pattern=r"^lang:"
    ))

    # Admin panel callbacks
    app.add_handler(CallbackQueryHandler(
        admin_handler.handle_callback,
        pattern=r"^admin:"
    ))

    # ------------------------------------------------------------------
    # ── MESSAGE HANDLERS ──
    # Text messages routed based on user state stored in context
    # ------------------------------------------------------------------
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        _route_text_message
    ))

    # Photo/document messages (for broadcast with media)
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL,
        admin_handler.handle_media_broadcast
    ))

    # ------------------------------------------------------------------
    # ── ERROR HANDLER ──
    # ------------------------------------------------------------------
    app.add_error_handler(_global_error_handler)

    logger.info("✅ All handlers registered successfully.")
    return app


# ============================================================
#   TEXT MESSAGE ROUTER
#   Routes incoming text to correct handler based on user state
# ============================================================

async def _route_text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Central router for all plain text messages.
    Checks user's current state from bot_data / user_data
    and delegates to the appropriate handler.
    """
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id

    # Retrieve current state for this user
    user_state = context.user_data.get("state", BotState.IDLE)

    logger.debug(
        f"Routing message from user {user_id} | state={user_state}"
    )

    # ── Route based on state ──
    if user_state == BotState.AWAITING_AI_QUESTION:
        handler = AIAssistantHandler()
        await handler.handle_question(update, context)

    elif user_state == BotState.AWAITING_TRANSLATION:
        handler = TranslatorHandler()
        await handler.handle_translation_input(update, context)

    elif user_state == BotState.AWAITING_NOTE_CONTENT:
        handler = NotesHandler()
        await handler.handle_note_input(update, context)

    elif user_state == BotState.AWAITING_BROADCAST:
        handler = AdminHandler()
        await handler.handle_broadcast_input(update, context)

    elif user_state == BotState.AWAITING_BAN_ID:
        handler = AdminHandler()
        await handler.handle_ban_input(update, context)

    elif user_state == BotState.AWAITING_UNBAN_ID:
        handler = AdminHandler()
        await handler.handle_unban_input(update, context)

    else:
        # Default: treat as AI question (friendly fallback)
        handler = AIAssistantHandler()
        await handler.handle_question(update, context)


# ============================================================
#   GLOBAL ERROR HANDLER
# ============================================================

async def _global_error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Catches ALL unhandled exceptions across the bot.
    Logs them and notifies admins if critical.
    """
    error = context.error

    # Log the full traceback
    logger.error(
        f"⚠️ Unhandled exception: {error}",
        exc_info=context.error
    )

    # Try to send a friendly error message to the user
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong. Please try again or use /start to reset."
            )
        except TelegramError:
            pass  # Silently ignore if we can't message the user

    # Notify admins about critical errors
    if not isinstance(error, TelegramError):
        await _notify_admins_of_error(context, error)


async def _notify_admins_of_error(
    context: ContextTypes.DEFAULT_TYPE,
    error: Exception
) -> None:
    """Send critical error notifications to all admin IDs."""
    error_msg = (
        f"🚨 *Critical Bot Error*\n\n"
        f"```\n{type(error).__name__}: {str(error)[:500]}\n```"
    )
    for admin_id in settings.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=error_msg,
                parse_mode="Markdown"
            )
        except TelegramError:
            pass  # Don't let admin notification failure crash anything


# ============================================================
#   LIFECYCLE HOOKS
# ============================================================

async def on_startup(app: Application) -> None:
    """
    Called once when the bot starts up.
    Initializes DB connection and logs startup info.
    """
    logger.info("=" * 60)
    logger.info("🚀 StudyBuddyV3BOT is starting up...")
    logger.info(f"   Environment : {settings.ENVIRONMENT}")
    logger.info(f"   Log Level   : {settings.LOG_LEVEL}")
    logger.info(f"   Admin IDs   : {settings.ADMIN_IDS}")
    logger.info(f"   Model       : {settings.OPENAI_MODEL}")
    logger.info("=" * 60)

    # Connect to MongoDB
    await db_manager.connect()
    logger.info("✅ MongoDB connected successfully.")

    # Notify admins that bot is online
    for admin_id in settings.ADMIN_IDS:
        try:
            await app.bot.send_message(
                chat_id=admin_id,
                text=(
                    "✅ *StudyBuddyV3BOT is Online*\n\n"
                    f"🌍 Environment: `{settings.ENVIRONMENT}`\n"
                    f"🗄️ Database: Connected\n"
                    f"🤖 AI Model: `{settings.OPENAI_MODEL}`\n\n"
                    "_Bot started successfully and is ready to serve users._"
                ),
                parse_mode="Markdown"
            )
        except TelegramError as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")


async def on_shutdown(app: Application) -> None:
    """
    Called once when the bot shuts down.
    Closes DB connections gracefully.
    """
    logger.info("🛑 StudyBuddyV3BOT is shutting down...")

    # Disconnect from MongoDB
    await db_manager.disconnect()
    logger.info("✅ MongoDB disconnected cleanly.")

    # Notify admins
    for admin_id in settings.ADMIN_IDS:
        try:
            await app.bot.send_message(
                chat_id=admin_id,
                text="🛑 *StudyBuddyV3BOT has gone Offline.*",
                parse_mode="Markdown"
            )
        except TelegramError:
            pass

    logger.info("👋 Shutdown complete. Goodbye!")


# ============================================================
#   MAIN ENTRY POINT
# ============================================================

async def main() -> None:
    """
    Main async entry point.
    Builds the app, registers lifecycle hooks, and starts polling.
    """
    # Create logs directory if it doesn't exist
    logs_dir = ROOT_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Build the application
    app = build_application()

    # Register lifecycle hooks
    app.post_init  = on_startup
    app.post_stop  = on_shutdown

    # ------------------------------------------------------------------
    # Start polling
    # Drop pending updates so stale messages don't flood on restart
    # ------------------------------------------------------------------
    logger.info("📡 Starting polling...")
    await app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=settings.DROP_PENDING_UPDATES,
        poll_interval=settings.POLL_INTERVAL,
        timeout=settings.POLL_TIMEOUT,
        close_loop=False,
    )


# ============================================================
#   SCRIPT ENTRY
# ============================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚡ Bot stopped manually via KeyboardInterrupt.")
    except Exception as e:
        logger.critical(f"💥 Fatal error during bot startup: {e}", exc_info=True)
        sys.exit(1)