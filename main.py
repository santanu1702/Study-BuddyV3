# ============================================================
#         StudyBuddyV3BOT — Main Entry Point
#         Production-ready async Telegram bot startup
#         ✅ Fixed: event loop conflict on Render.com
# ============================================================

import asyncio
import sys
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is in sys.path
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
# Setup logger first
# ---------------------------------------------------------------------------
setup_logger()
logger = get_logger(__name__)


# ============================================================
#   BOT APPLICATION BUILDER
# ============================================================

def build_application() -> Application:
    """Build and configure the Telegram Application instance."""
    logger.info("🔧 Building bot application...")

    app = (
        Application.builder()
        .token(settings.bot_token)
        .concurrent_updates(True)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    # ── Handler instances ──
    start_handler      = StartHandler()
    ai_handler         = AIAssistantHandler()
    calc_handler       = CalculatorHandler()
    translator_handler = TranslatorHandler()
    notes_handler      = NotesHandler()
    lang_handler       = LanguageHandler()
    admin_handler      = AdminHandler()

    # ── Middleware instances ──
    auth_mw        = AuthMiddleware()
    rate_limit_mw  = RateLimitMiddleware()
    maintenance_mw = MaintenanceMiddleware()

    # ── Register middlewares ──
    app.add_handler(
        MessageHandler(filters.ALL, maintenance_mw.process), group=-3
    )
    app.add_handler(
        MessageHandler(filters.ALL, auth_mw.process), group=-2
    )
    app.add_handler(
        MessageHandler(filters.ALL, rate_limit_mw.process), group=-1
    )

    # ── Command handlers ──
    app.add_handler(CommandHandler("start",  start_handler.handle_start))
    app.add_handler(CommandHandler("help",   start_handler.handle_help))
    app.add_handler(CommandHandler("menu",   start_handler.handle_menu))
    app.add_handler(CommandHandler("cancel", start_handler.handle_cancel))
    app.add_handler(CommandHandler("admin",  admin_handler.handle_admin_command))

    # ── Callback query handlers ──
    app.add_handler(CallbackQueryHandler(
        start_handler.handle_menu_callback,
        pattern=r"^menu:"
    ))
    app.add_handler(CallbackQueryHandler(
        ai_handler.handle_callback,
        pattern=r"^ai:"
    ))
    app.add_handler(CallbackQueryHandler(
        calc_handler.handle_callback,
        pattern=r"^calc:"
    ))
    app.add_handler(CallbackQueryHandler(
        translator_handler.handle_callback,
        pattern=r"^trans:"
    ))
    app.add_handler(CallbackQueryHandler(
        notes_handler.handle_callback,
        pattern=r"^notes:"
    ))
    app.add_handler(CallbackQueryHandler(
        lang_handler.handle_callback,
        pattern=r"^lang:"
    ))
    app.add_handler(CallbackQueryHandler(
        admin_handler.handle_callback,
        pattern=r"^admin:"
    ))

    # ── Text message handler ──
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        _route_text_message
    ))

    # ── Media handler ──
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL,
        admin_handler.handle_media_broadcast
    ))

    # ── Error handler ──
    app.add_error_handler(_global_error_handler)

    logger.info("✅ All handlers registered successfully.")
    return app


# ============================================================
#   TEXT MESSAGE ROUTER
# ============================================================

async def _route_text_message(
    update:  Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Route text messages based on user state."""
    if not update.message or not update.effective_user:
        return

    user_state = context.user_data.get("state", BotState.IDLE)

    if user_state == BotState.AWAITING_AI_QUESTION:
        await AIAssistantHandler().handle_question(update, context)
    elif user_state == BotState.AWAITING_TRANSLATION:
        await TranslatorHandler().handle_translation_input(update, context)
    elif user_state == BotState.AWAITING_NOTE_CONTENT:
        await NotesHandler().handle_note_input(update, context)
    elif user_state == BotState.AWAITING_BROADCAST:
        await AdminHandler().handle_broadcast_input(update, context)
    elif user_state == BotState.AWAITING_BAN_ID:
        await AdminHandler().handle_ban_input(update, context)
    elif user_state == BotState.AWAITING_UNBAN_ID:
        await AdminHandler().handle_unban_input(update, context)
    else:
        await AIAssistantHandler().handle_question(update, context)


# ============================================================
#   GLOBAL ERROR HANDLER
# ============================================================

async def _global_error_handler(
    update:  object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Catch all unhandled exceptions."""
    error = context.error
    logger.error(f"⚠️ Unhandled exception: {error}", exc_info=True)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong. Please try again or use /start."
            )
        except TelegramError:
            pass

    if not isinstance(error, TelegramError):
        await _notify_admins_of_error(context, error)


async def _notify_admins_of_error(
    context: ContextTypes.DEFAULT_TYPE,
    error:   Exception,
) -> None:
    """Notify admins of critical errors."""
    error_msg = (
        f"🚨 *Critical Bot Error*\n\n"
        f"```\n{type(error).__name__}: {str(error)[:500]}\n```"
    )
    for admin_id in settings.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=    admin_id,
                text=       error_msg,
                parse_mode= "Markdown",
            )
        except TelegramError:
            pass


# ============================================================
#   LIFECYCLE HOOKS
# ============================================================

async def on_startup(app: Application) -> None:
    """Called once on bot startup."""
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

    # Notify admins
    for admin_id in settings.ADMIN_IDS:
        try:
            await app.bot.send_message(
                chat_id=    admin_id,
                text=(
                    "✅ *StudyBuddyV3BOT is Online*\n\n"
                    f"🌍 Environment: `{settings.ENVIRONMENT}`\n"
                    f"🗄️ Database: Connected\n"
                    f"🤖 AI Model: `{settings.OPENAI_MODEL}`\n\n"
                    "_Bot started successfully!_"
                ),
                parse_mode= "Markdown",
            )
        except TelegramError as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")


async def on_shutdown(app: Application) -> None:
    """Called once on bot shutdown."""
    logger.info("🛑 StudyBuddyV3BOT is shutting down...")
    await db_manager.disconnect()
    logger.info("✅ MongoDB disconnected cleanly.")

    for admin_id in settings.ADMIN_IDS:
        try:
            await app.bot.send_message(
                chat_id=    admin_id,
                text=       "🛑 *StudyBuddyV3BOT has gone Offline.*",
                parse_mode= "Markdown",
            )
        except TelegramError:
            pass

    logger.info("👋 Shutdown complete.")


# ============================================================
#   MAIN ENTRY POINT
#   ✅ FIXED: Use app.run_polling() directly instead of
#   asyncio.run() to avoid event loop conflicts on Render
# ============================================================

def main() -> None:
    """
    Main entry point — synchronous wrapper.
    Uses PTB's built-in run_polling() which manages
    its own event loop internally — no asyncio.run() needed.
    """
    # Create logs directory
    logs_dir = ROOT_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Build application
    app = build_application()

    # Register lifecycle hooks
    app.post_init  = on_startup
    app.post_stop  = on_shutdown

    logger.info("📡 Starting polling...")

    # ✅ run_polling() manages its own event loop
    # Do NOT wrap in asyncio.run() — causes "loop already running"
    app.run_polling(
        allowed_updates=     Update.ALL_TYPES,
        drop_pending_updates=settings.DROP_PENDING_UPDATES,
        poll_interval=       settings.POLL_INTERVAL,
        timeout=             settings.POLL_TIMEOUT,
        close_loop=          True,
    )


# ============================================================
#   SCRIPT ENTRY
# ============================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("⚡ Bot stopped manually via KeyboardInterrupt.")
    except Exception as e:
        logger.critical(
            f"💥 Fatal error during bot startup: {e}",
            exc_info=True,
        )
        sys.exit(1)
