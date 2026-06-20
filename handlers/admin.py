# ============================================================
#         StudyBuddyV3BOT — Admin Handler
#         Full interactive admin panel via inline buttons
#         Secure, fast, clean UI — admin IDs only
# ============================================================

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from config.settings import settings
from config.constants import BotState, AdminAction, EmojiConstants
from database.repositories import user_repo, admin_repo, notes_repo
from keyboards.admin_kb import AdminKeyboard
from services.broadcast_service import BroadcastService
from locales.translator import get_text
from utils.logger import get_logger
from utils.helpers import (
    answer_callback,
    edit_or_send,
    format_datetime,
    humanize_number,
)

logger = get_logger(__name__)


# ============================================================
#   ADMIN HANDLER
# ============================================================

class AdminHandler:
    """
    Handles all admin panel interactions.

    Features:
    - Secure access (admin IDs only)
    - Full inline button navigation
    - User stats dashboard
    - Ban / Unban users
    - Broadcast messages with media
    - Maintenance mode toggle
    - API usage stats
    - Error log viewer
    """

    def __init__(self) -> None:
        self.broadcast_service = BroadcastService()

    # ================================================================
    #   ACCESS CONTROL
    # ================================================================

    def _is_admin(self, user_id: int) -> bool:
        """Check if user is an authorized admin."""
        return settings.is_admin(user_id)

    async def _deny_access(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Send access denied message to non-admins."""
        if update.callback_query:
            await answer_callback(
                update.callback_query,
                text="🔐 Admin access required.",
                show_alert=True,
            )
        elif update.message:
            await update.message.reply_text(
                f"{EmojiConstants.LOCK} *Access Denied*\n\n"
                f"This panel is restricted to bot administrators only.",
                parse_mode="Markdown",
            )

    # ================================================================
    #   COMMAND HANDLER
    # ================================================================

    async def handle_admin_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Handle /admin command.
        Opens the admin panel if user is authorized.
        """
        user_id = update.effective_user.id

        if not self._is_admin(user_id):
            await self._deny_access(update, context)
            logger.warning(
                f"⚠️  Unauthorized admin access attempt | "
                f"User: {user_id}"
            )
            return

        logger.info(f"👑 Admin panel opened by {user_id}")
        await self._show_main_panel(update, context)

    # ================================================================
    #   CALLBACK ROUTER
    # ================================================================

    async def handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Route all admin: callback queries to correct handler.
        Pattern: admin:action:optional_param
        """
        query   = update.callback_query
        user_id = update.effective_user.id

        # Security check on every callback
        if not self._is_admin(user_id):
            await self._deny_access(update, context)
            return

        await query.answer()

        # Parse callback data
        parts  = query.data.split(":")
        action = parts[1] if len(parts) > 1 else ""
        param  = parts[2] if len(parts) > 2 else ""

        logger.debug(
            f"Admin callback | User: {user_id} | "
            f"Action: {action} | Param: {param}"
        )

        # ── Route to correct handler ──
        handlers = {
            AdminAction.BACK_TO_PANEL:     self._show_main_panel,
            AdminAction.TOTAL_USERS:       self._show_user_stats,
            AdminAction.ACTIVE_USERS:      self._show_active_users,
            AdminAction.BAN_USER:          self._prompt_ban_user,
            AdminAction.UNBAN_USER:        self._prompt_unban_user,
            AdminAction.LIST_BANNED:       self._show_banned_users,
            AdminAction.BROADCAST:         self._prompt_broadcast,
            AdminAction.BROADCAST_CONFIRM: self._confirm_broadcast,
            AdminAction.BROADCAST_CANCEL:  self._cancel_broadcast,
            AdminAction.MAINTENANCE_ON:    self._enable_maintenance,
            AdminAction.MAINTENANCE_OFF:   self._disable_maintenance,
            AdminAction.VIEW_LOGS:         self._show_logs,
            AdminAction.CLEAR_LOGS:        self._clear_logs,
            AdminAction.API_STATS:         self._show_api_stats,
            AdminAction.REFRESH:           self._show_main_panel,
        }

        handler_func = handlers.get(action)
        if handler_func:
            await handler_func(update, context)
        else:
            logger.warning(f"Unknown admin action: {action}")
            await self._show_main_panel(update, context)

    # ================================================================
    #   MAIN PANEL
    # ================================================================

    async def _show_main_panel(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Display the main admin panel dashboard.
        Shows quick stats and navigation buttons.
        """
        # Fetch quick stats
        user_stats = await user_repo.get_stats_summary()
        api_stats  = await admin_repo.get_dashboard_summary()

        maintenance_status = (
            "🟢 Online" if not settings.MAINTENANCE_MODE
            else "🔴 Maintenance"
        )

        text = (
            f"{EmojiConstants.ADMIN} *Admin Panel — StudyBuddyV3BOT*\n"
            f"{'─' * 35}\n\n"
            f"📊 *Quick Stats*\n"
            f"👥 Total Users:     `{humanize_number(user_stats['total'])}`\n"
            f"🟢 Active (24h):    `{humanize_number(user_stats['active_24h'])}`\n"
            f"🟡 Active (7d):     `{humanize_number(user_stats['active_7d'])}`\n"
            f"🔨 Banned:          `{humanize_number(user_stats['banned'])}`\n"
            f"✨ New Today:       `{humanize_number(user_stats['new_today'])}`\n\n"
            f"🤖 *AI Usage Today*\n"
            f"📨 Requests:        `{humanize_number(api_stats['api_requests_today'])}`\n"
            f"🔤 Tokens:          `{humanize_number(api_stats['api_tokens_today'])}`\n"
            f"💰 Est. Cost:       `${api_stats['api_cost_today']:.4f}`\n\n"
            f"🔧 *System Status*\n"
            f"📡 Bot Status:      {maintenance_status}\n"
            f"📋 Total Logs:      `{humanize_number(api_stats['total_logs'])}`\n\n"
            f"_Select an option below:_"
        )

        keyboard = AdminKeyboard.main_panel(
            maintenance_on=settings.MAINTENANCE_MODE
        )

        await edit_or_send(update, context, text, keyboard)

    # ================================================================
    #   USER STATISTICS
    # ================================================================

    async def _show_user_stats(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Display detailed user statistics."""
        stats       = await user_repo.get_stats_summary()
        notes_stats = await notes_repo.get_notes_stats()
        top_users   = await user_repo.get_top_active_users(limit=5)

        # Build top users list
        top_users_text = ""
        for i, u in enumerate(top_users, 1):
            name = u.get("full_name") or u.get("username") or f"User#{u['user_id']}"
            top_users_text += (
                f"  {i}. {name[:20]} — "
                f"`{u.get('message_count', 0)}` msgs\n"
            )

        if not top_users_text:
            top_users_text = "  _No data yet_\n"

        text = (
            f"{EmojiConstants.STATS} *User Statistics*\n"
            f"{'─' * 35}\n\n"
            f"👥 *Registration*\n"
            f"  Total Users:    `{humanize_number(stats['total'])}`\n"
            f"  New Today:      `{humanize_number(stats['new_today'])}`\n"
            f"  New This Week:  `{humanize_number(stats['new_week'])}`\n\n"
            f"📊 *Activity*\n"
            f"  Active (24h):   `{humanize_number(stats['active_24h'])}`\n"
            f"  Active (7d):    `{humanize_number(stats['active_7d'])}`\n\n"
            f"🔒 *Access Control*\n"
            f"  Banned Users:   `{humanize_number(stats['banned'])}`\n\n"
            f"📚 *Notes*\n"
            f"  Active Notes:   `{humanize_number(notes_stats['total_active'])}`\n"
            f"  Deleted Notes:  `{humanize_number(notes_stats['total_deleted'])}`\n\n"
            f"🏆 *Top Active Users*\n"
            f"{top_users_text}"
        )

        keyboard = AdminKeyboard.back_button()
        await edit_or_send(update, context, text, keyboard)

    async def _show_active_users(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Display recently active users list."""
        active_users = await user_repo.get_active_users(hours=24)

        if not active_users:
            text = (
                f"{EmojiConstants.STATS} *Active Users (24h)*\n"
                f"{'─' * 35}\n\n"
                f"_No active users in the last 24 hours._"
            )
        else:
            lines = []
            for i, user in enumerate(active_users[:20], 1):
                name = user.display_name[:20]
                last = format_datetime(user.last_active)
                lines.append(f"  {i}. {name} — _{last}_")

            text = (
                f"{EmojiConstants.STATS} *Active Users (Last 24h)*\n"
                f"{'─' * 35}\n\n"
                f"Total: `{len(active_users)}` users\n\n"
                + "\n".join(lines)
            )

        keyboard = AdminKeyboard.back_button()
        await edit_or_send(update, context, text, keyboard)

    # ================================================================
    #   BAN / UNBAN
    # ================================================================

    async def _prompt_ban_user(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Ask admin for the user ID to ban."""
        context.user_data["state"] = BotState.AWAITING_BAN_ID

        text = (
            f"{EmojiConstants.BAN} *Ban User*\n"
            f"{'─' * 35}\n\n"
            f"Please send the *Telegram User ID* of the user you want to ban.\n\n"
            f"_Example: `123456789`_\n\n"
            f"⚠️ The user will be immediately blocked from using the bot."
        )

        keyboard = AdminKeyboard.cancel_action()
        await edit_or_send(update, context, text, keyboard)

    async def handle_ban_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Process ban user ID input from admin.
        Called from main.py text router when state = AWAITING_BAN_ID.
        """
        user_id  = update.effective_user.id
        text_in  = update.message.text.strip()

        # Reset state
        context.user_data["state"] = BotState.IDLE

        # Validate input
        if not text_in.isdigit():
            await update.message.reply_text(
                f"{EmojiConstants.ERROR} Invalid user ID. "
                f"Please enter a numeric Telegram user ID."
            )
            return

        target_id = int(text_in)

        # Prevent self-ban
        if target_id == user_id:
            await update.message.reply_text(
                f"{EmojiConstants.ERROR} You cannot ban yourself!"
            )
            return

        # Prevent banning other admins
        if settings.is_admin(target_id):
            await update.message.reply_text(
                f"{EmojiConstants.ERROR} Cannot ban another admin!"
            )
            return

        # Check if user exists
        target_user = await user_repo.get_by_id(target_id)
        if not target_user:
            await update.message.reply_text(
                f"{EmojiConstants.ERROR} User `{target_id}` not found in database.\n"
                f"_They may not have started the bot yet._",
                parse_mode="Markdown",
            )
            return

        # Perform ban
        success = await user_repo.ban(
            user_id=  target_id,
            admin_id= user_id,
            reason=   "Banned by admin",
        )

        if success:
            # Log the action
            await admin_repo.log_action(
                admin_id=  user_id,
                action=    AdminAction.BAN_USER,
                target_id= target_id,
                details=   {"target_name": target_user.display_name},
            )

            await update.message.reply_text(
                f"{EmojiConstants.SUCCESS} *User Banned Successfully*\n\n"
                f"👤 User: `{target_user.display_name}`\n"
                f"🆔 ID: `{target_id}`\n\n"
                f"_They can no longer use the bot._",
                parse_mode="Markdown",
            )
            logger.info(
                f"🔨 Admin {user_id} banned user {target_id}"
            )
        else:
            await update.message.reply_text(
                f"{EmojiConstants.ERROR} Failed to ban user `{target_id}`.",
                parse_mode="Markdown",
            )

    async def _prompt_unban_user(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Ask admin for the user ID to unban."""
        context.user_data["state"] = BotState.AWAITING_UNBAN_ID

        text = (
            f"{EmojiConstants.UNBAN} *Unban User*\n"
            f"{'─' * 35}\n\n"
            f"Please send the *Telegram User ID* of the user you want to unban.\n\n"
            f"_Example: `123456789`_"
        )

        keyboard = AdminKeyboard.cancel_action()
        await edit_or_send(update, context, text, keyboard)

    async def handle_unban_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Process unban user ID input from admin.
        Called from main.py text router when state = AWAITING_UNBAN_ID.
        """
        user_id = update.effective_user.id
        text_in = update.message.text.strip()

        context.user_data["state"] = BotState.IDLE

        if not text_in.isdigit():
            await update.message.reply_text(
                f"{EmojiConstants.ERROR} Invalid user ID."
            )
            return

        target_id = int(text_in)

        success = await user_repo.unban(
            user_id=  target_id,
            admin_id= user_id,
        )

        if success:
            await admin_repo.log_action(
                admin_id=  user_id,
                action=    AdminAction.UNBAN_USER,
                target_id= target_id,
            )

            await update.message.reply_text(
                f"{EmojiConstants.SUCCESS} *User Unbanned Successfully*\n\n"
                f"🆔 ID: `{target_id}`\n\n"
                f"_They can now use the bot again._",
                parse_mode="Markdown",
            )
            logger.info(
                f"🔓 Admin {user_id} unbanned user {target_id}"
            )
        else:
            await update.message.reply_text(
                f"{EmojiConstants.ERROR} Could not unban `{target_id}`.\n"
                f"_User may not be banned or doesn't exist._",
                parse_mode="Markdown",
            )

    async def _show_banned_users(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Display list of banned users."""
        banned = await user_repo.get_banned_users(limit=20)
        count  = await user_repo.count_banned()

        if not banned:
            text = (
                f"{EmojiConstants.BAN} *Banned Users*\n"
                f"{'─' * 35}\n\n"
                f"✅ No banned users found."
            )
        else:
            lines = []
            for u in banned:
                banned_at = format_datetime(u.banned_at) if u.banned_at else "Unknown"
                lines.append(
                    f"• `{u.user_id}` — {u.display_name[:20]}\n"
                    f"  _{u.ban_reason or 'No reason'} • {banned_at}_"
                )

            text = (
                f"{EmojiConstants.BAN} *Banned Users* ({count} total)\n"
                f"{'─' * 35}\n\n"
                + "\n\n".join(lines)
            )

        keyboard = AdminKeyboard.back_button()
        await edit_or_send(update, context, text, keyboard)

    # ================================================================
    #   BROADCAST
    # ================================================================

    async def _prompt_broadcast(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Ask admin for broadcast message content."""
        context.user_data["state"] = BotState.AWAITING_BROADCAST

        # Get recipient count
        recipients = await user_repo.get_broadcast_recipients()
        count      = len(recipients)

        text = (
            f"{EmojiConstants.BROADCAST} *Send Broadcast*\n"
            f"{'─' * 35}\n\n"
            f"👥 Recipients: `{humanize_number(count)}` users\n\n"
            f"📝 Send your broadcast message now.\n"
            f"You can send:\n"
            f"  • Text message\n"
            f"  • Photo with caption\n"
            f"  • Document with caption\n\n"
            f"⚠️ _Message will be sent to all non-banned users._"
        )

        keyboard = AdminKeyboard.cancel_action()
        await edit_or_send(update, context, text, keyboard)

    async def handle_broadcast_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Process broadcast message input from admin.
        Asks for confirmation before sending.
        Called from main.py router when state = AWAITING_BROADCAST.
        """
        context.user_data["state"] = BotState.IDLE

        message = update.message
        user_id = update.effective_user.id

        # Store broadcast data in context
        context.user_data["broadcast_text"]      = message.text or message.caption or ""
        context.user_data["broadcast_has_media"] = bool(
            message.photo or message.document
        )
        context.user_data["broadcast_media_type"] = (
            "photo"    if message.photo    else
            "document" if message.document else
            None
        )
        context.user_data["broadcast_file_id"] = (
            message.photo[-1].file_id if message.photo else
            message.document.file_id  if message.document else
            None
        )

        # Get recipient count for confirmation
        recipients = await user_repo.get_broadcast_recipients()
        count      = len(recipients)

        preview    = context.user_data["broadcast_text"][:200]
        media_note = (
            f"\n📎 Media: {context.user_data['broadcast_media_type']}"
            if context.user_data["broadcast_has_media"]
            else ""
        )

        confirm_text = (
            f"{EmojiConstants.BROADCAST} *Confirm Broadcast*\n"
            f"{'─' * 35}\n\n"
            f"👥 Recipients: `{humanize_number(count)}` users\n"
            f"{media_note}\n\n"
            f"📝 *Preview:*\n"
            f"_{preview}_\n\n"
            f"⚠️ Are you sure you want to send this broadcast?"
        )

        keyboard = AdminKeyboard.broadcast_confirm()
        await message.reply_text(
            confirm_text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    async def _confirm_broadcast(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Execute the broadcast after admin confirmation."""
        query   = update.callback_query
        user_id = update.effective_user.id

        broadcast_text = context.user_data.get("broadcast_text", "")
        has_media      = context.user_data.get("broadcast_has_media", False)
        media_type     = context.user_data.get("broadcast_media_type")
        file_id        = context.user_data.get("broadcast_file_id")

        if not broadcast_text and not has_media:
            await query.edit_message_text(
                f"{EmojiConstants.ERROR} No broadcast content found. Please try again."
            )
            return

        # Show sending status
        await query.edit_message_text(
            f"{EmojiConstants.LOADING} *Sending broadcast...*\n\n"
            f"_Please wait. This may take a while._",
            parse_mode="Markdown",
        )

        # Get recipients
        recipients = await user_repo.get_broadcast_recipients()

        # Create broadcast record
        broadcast = await admin_repo.create_broadcast(
            admin_id=     user_id,
            message_text= broadcast_text,
            total_users=  len(recipients),
            has_media=    has_media,
            media_type=   media_type,
        )

        # Send broadcast
        sent, failed = await self.broadcast_service.send_broadcast(
            bot=        context.bot,
            recipients= recipients,
            text=       broadcast_text,
            file_id=    file_id,
            media_type= media_type,
        )

        # Update broadcast record
        if broadcast:
            await admin_repo.update_broadcast_stats(
                broadcast_id= broadcast.broadcast_id,
                sent_count=   sent,
                failed_count= failed,
                status=       "done",
            )

        # Log action
        await admin_repo.log_action(
            admin_id= user_id,
            action=   AdminAction.BROADCAST,
            details={
                "total":  len(recipients),
                "sent":   sent,
                "failed": failed,
            },
        )

        # Clean up context
        for key in [
            "broadcast_text", "broadcast_has_media",
            "broadcast_media_type", "broadcast_file_id"
        ]:
            context.user_data.pop(key, None)

        success_rate = (
            round((sent / len(recipients)) * 100, 1)
            if recipients else 0
        )

        await query.edit_message_text(
            f"{EmojiConstants.SUCCESS} *Broadcast Complete*\n"
            f"{'─' * 35}\n\n"
            f"👥 Total Targets:  `{humanize_number(len(recipients))}`\n"
            f"✅ Sent:           `{humanize_number(sent)}`\n"
            f"❌ Failed:         `{humanize_number(failed)}`\n"
            f"📊 Success Rate:   `{success_rate}%`",
            parse_mode="Markdown",
            reply_markup=AdminKeyboard.back_button(),
        )

        logger.info(
            f"📢 Broadcast complete | "
            f"Admin: {user_id} | "
            f"Sent: {sent} | Failed: {failed}"
        )

    async def _cancel_broadcast(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Cancel a pending broadcast."""
        context.user_data["state"] = BotState.IDLE
        for key in [
            "broadcast_text", "broadcast_has_media",
            "broadcast_media_type", "broadcast_file_id"
        ]:
            context.user_data.pop(key, None)

        await self._show_main_panel(update, context)

    async def handle_media_broadcast(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Handle photo/document messages when admin is in broadcast mode.
        Routes to handle_broadcast_input if state is correct.
        """
        user_id = update.effective_user.id

        if not self._is_admin(user_id):
            return

        state = context.user_data.get("state")
        if state == BotState.AWAITING_BROADCAST:
            await self.handle_broadcast_input(update, context)

    # ================================================================
    #   MAINTENANCE MODE
    # ================================================================

    async def _enable_maintenance(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Enable maintenance mode."""
        user_id = update.effective_user.id

        settings.MAINTENANCE_MODE = True

        await admin_repo.log_action(
            admin_id= user_id,
            action=   AdminAction.MAINTENANCE_ON,
        )

        logger.info(f"🔧 Maintenance mode ENABLED by admin {user_id}")
        await self._show_main_panel(update, context)

    async def _disable_maintenance(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Disable maintenance mode."""
        user_id = update.effective_user.id

        settings.MAINTENANCE_MODE = False

        await admin_repo.log_action(
            admin_id= user_id,
            action=   AdminAction.MAINTENANCE_OFF,
        )

        logger.info(f"✅ Maintenance mode DISABLED by admin {user_id}")
        await self._show_main_panel(update, context)

    # ================================================================
    #   LOGS VIEWER
    # ================================================================

    async def _show_logs(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Display recent admin action logs."""
        logs = await admin_repo.get_recent_logs(limit=15)

        if not logs:
            text = (
                f"{EmojiConstants.LOGS} *Admin Logs*\n"
                f"{'─' * 35}\n\n"
                f"_No logs found._"
            )
        else:
            lines = []
            for log in logs:
                icon = "✅" if log.result == "success" else "❌"
                date = format_datetime(log.created_at)
                lines.append(
                    f"{icon} `{log.action}` by `{log.admin_id}`\n"
                    f"   _{date}_"
                )

            text = (
                f"{EmojiConstants.LOGS} *Recent Admin Logs* "
                f"(last {len(logs)})\n"
                f"{'─' * 35}\n\n"
                + "\n\n".join(lines)
            )

        keyboard = AdminKeyboard.logs_panel()
        await edit_or_send(update, context, text, keyboard)

    async def _clear_logs(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Clear old admin logs (older than 30 days)."""
        user_id = update.effective_user.id
        count   = await admin_repo.clear_old_logs(days=30)

        await admin_repo.log_action(
            admin_id= user_id,
            action=   AdminAction.CLEAR_LOGS,
            details=  {"deleted_count": count},
        )

        text = (
            f"{EmojiConstants.SUCCESS} *Logs Cleared*\n\n"
            f"Deleted `{count}` log entries older than 30 days."
        )

        keyboard = AdminKeyboard.back_button()
        await edit_or_send(update, context, text, keyboard)

    # ================================================================
    #   API STATS
    # ================================================================

    async def _show_api_stats(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Display OpenAI API usage statistics."""
        today   = await admin_repo.get_api_stats_today()
        total   = await admin_repo.get_api_stats_total()
        weekly  = await admin_repo.get_api_stats_range(days=7)
        top_users = await admin_repo.get_top_api_users(limit=5)

        # Build weekly breakdown
        weekly_text = ""
        for day in weekly[:5]:
            weekly_text += (
                f"  `{day['date']}` — "
                f"{day['total_requests']} reqs, "
                f"{day['total_tokens']} tokens\n"
            )
        if not weekly_text:
            weekly_text = "  _No data yet_\n"

        # Build top users
        top_text = ""
        for i, u in enumerate(top_users, 1):
            top_text += (
                f"  {i}. `{u['user_id']}` — "
                f"{u['total_requests']} reqs\n"
            )
        if not top_text:
            top_text = "  _No data yet_\n"

        text = (
            f"{EmojiConstants.STATS} *OpenAI API Statistics*\n"
            f"{'─' * 35}\n\n"
            f"📅 *Today*\n"
            f"  Requests:     `{humanize_number(today['total_requests'])}`\n"
            f"  Tokens:       `{humanize_number(today['total_tokens'])}`\n"
            f"  Cost (est.):  `${today['total_cost_usd']:.4f}`\n"
            f"  Unique Users: `{humanize_number(today['unique_users'])}`\n\n"
            f"📊 *All Time*\n"
            f"  Requests:     `{humanize_number(total['total_requests'])}`\n"
            f"  Tokens:       `{humanize_number(total['total_tokens'])}`\n"
            f"  Cost (est.):  `${total['total_cost_usd']:.4f}`\n"
            f"  Unique Users: `{humanize_number(total['unique_users'])}`\n\n"
            f"📆 *Last 5 Days*\n"
            f"{weekly_text}\n"
            f"🏆 *Top Users (7d)*\n"
            f"{top_text}"
        )

        keyboard = AdminKeyboard.back_button()
        await edit_or_send(update, context, text, keyboard)
