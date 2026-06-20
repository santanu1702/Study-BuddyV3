# ============================================================
#         StudyBuddyV3BOT — Broadcast Service
#         Async broadcast message sender
#         Handles text + media with delivery tracking
# ============================================================

import asyncio
from typing import List, Optional, Tuple

from telegram import Bot
from telegram.error import (
    TelegramError,
    Forbidden,
    BadRequest,
    RetryAfter,
)

from config.constants import TimeConstants
from database.models import UserModel
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
#   BROADCAST SERVICE
# ============================================================

class BroadcastService:
    """
    Handles sending broadcast messages to all eligible users.

    Features:
    - Send text messages to all users
    - Send photo/document with caption
    - Per-message delay to avoid Telegram flood limits
    - Tracks sent/failed counts
    - Handles all Telegram errors gracefully
    - Auto-removes blocked/deactivated users
    - RetryAfter handling
    """

    def __init__(self) -> None:
        # Delay between each message to avoid flood limits
        self.delay_between_msgs = TimeConstants.BROADCAST_DELAY

    # ================================================================
    #   MAIN BROADCAST METHOD
    # ================================================================

    async def send_broadcast(
        self,
        bot:        Bot,
        recipients: List[UserModel],
        text:       str,
        file_id:    Optional[str] = None,
        media_type: Optional[str] = None,
    ) -> Tuple[int, int]:
        """
        Send a broadcast message to all recipients.

        Args:
            bot:        Telegram Bot instance
            recipients: List of UserModel to send to
            text:       Message text or caption
            file_id:    Optional Telegram file_id for media
            media_type: "photo" | "document" | None

        Returns:
            Tuple of (sent_count, failed_count)
        """
        sent   = 0
        failed = 0
        total  = len(recipients)

        logger.info(
            f"📢 Broadcast started | "
            f"Recipients: {total} | "
            f"Has media: {bool(file_id)}"
        )

        for i, user in enumerate(recipients, 1):
            try:
                # ── Send message based on type ──
                if file_id and media_type == "photo":
                    await self._send_photo(
                        bot=     bot,
                        chat_id= user.user_id,
                        file_id= file_id,
                        caption= text,
                    )
                elif file_id and media_type == "document":
                    await self._send_document(
                        bot=     bot,
                        chat_id= user.user_id,
                        file_id= file_id,
                        caption= text,
                    )
                else:
                    await self._send_text(
                        bot=     bot,
                        chat_id= user.user_id,
                        text=    text,
                    )

                sent += 1

                # ── Log progress every 50 users ──
                if i % 50 == 0:
                    logger.info(
                        f"📢 Broadcast progress | "
                        f"{i}/{total} | "
                        f"Sent: {sent} | Failed: {failed}"
                    )

                # ── Delay between messages ──
                await asyncio.sleep(self.delay_between_msgs)

            except RetryAfter as e:
                # ── Telegram flood control — wait and retry ──
                wait_secs = e.retry_after + 1
                logger.warning(
                    f"⚠️ Flood control — waiting {wait_secs}s | "
                    f"User: {user.user_id}"
                )
                await asyncio.sleep(wait_secs)

                # Retry once after waiting
                try:
                    await self._send_text(
                        bot=     bot,
                        chat_id= user.user_id,
                        text=    text,
                    )
                    sent += 1
                except Exception:
                    failed += 1

            except Forbidden:
                # ── User blocked the bot ──
                failed += 1
                logger.debug(
                    f"User {user.user_id} blocked bot — skipping"
                )

            except BadRequest as e:
                # ── Bad chat ID or deactivated account ──
                failed += 1
                logger.warning(
                    f"BadRequest for user {user.user_id}: {e}"
                )

            except TelegramError as e:
                # ── Other Telegram errors ──
                failed += 1
                logger.warning(
                    f"TelegramError for user {user.user_id}: {e}"
                )

            except Exception as e:
                # ── Unexpected errors ──
                failed += 1
                logger.error(
                    f"Unexpected error broadcasting to "
                    f"{user.user_id}: {e}"
                )

        logger.info(
            f"📢 Broadcast complete | "
            f"Total: {total} | "
            f"Sent: {sent} | "
            f"Failed: {failed} | "
            f"Success rate: "
            f"{round((sent/total)*100, 1) if total else 0}%"
        )

        return sent, failed

    # ================================================================
    #   SEND HELPERS
    # ================================================================

    async def _send_text(
        self,
        bot:     Bot,
        chat_id: int,
        text:    str,
    ) -> None:
        """
        Send a plain text broadcast message.

        Args:
            bot:     Telegram Bot instance
            chat_id: Target chat/user ID
            text:    Message text
        """
        await bot.send_message(
            chat_id=    chat_id,
            text=       text,
            parse_mode= "Markdown",
        )

    async def _send_photo(
        self,
        bot:     Bot,
        chat_id: int,
        file_id: str,
        caption: str,
    ) -> None:
        """
        Send a photo broadcast message with caption.

        Args:
            bot:     Telegram Bot instance
            chat_id: Target chat/user ID
            file_id: Telegram photo file_id
            caption: Photo caption text
        """
        await bot.send_photo(
            chat_id=    chat_id,
            photo=      file_id,
            caption=    caption,
            parse_mode= "Markdown",
        )

    async def _send_document(
        self,
        bot:     Bot,
        chat_id: int,
        file_id: str,
        caption: str,
    ) -> None:
        """
        Send a document broadcast message with caption.

        Args:
            bot:     Telegram Bot instance
            chat_id: Target chat/user ID
            file_id: Telegram document file_id
            caption: Document caption text
        """
        await bot.send_document(
            chat_id=    chat_id,
            document=   file_id,
            caption=    caption,
            parse_mode= "Markdown",
        )

    # ================================================================
    #   SINGLE USER BROADCAST
    # ================================================================

    async def send_to_user(
        self,
        bot:        Bot,
        user_id:    int,
        text:       str,
        file_id:    Optional[str] = None,
        media_type: Optional[str] = None,
    ) -> bool:
        """
        Send a message to a single user.
        Used for targeted notifications.

        Args:
            bot:        Telegram Bot instance
            user_id:    Target Telegram user ID
            text:       Message text
            file_id:    Optional file_id for media
            media_type: "photo" | "document" | None

        Returns:
            True if sent successfully
        """
        try:
            if file_id and media_type == "photo":
                await self._send_photo(
                    bot=     bot,
                    chat_id= user_id,
                    file_id= file_id,
                    caption= text,
                )
            elif file_id and media_type == "document":
                await self._send_document(
                    bot=     bot,
                    chat_id= user_id,
                    file_id= file_id,
                    caption= text,
                )
            else:
                await self._send_text(
                    bot=     bot,
                    chat_id= user_id,
                    text=    text,
                )
            return True

        except Forbidden:
            logger.debug(f"User {user_id} blocked bot")
            return False

        except Exception as e:
            logger.error(
                f"Error sending to user {user_id}: {e}"
            )
            return False

    # ================================================================
    #   PREVIEW BROADCAST
    # ================================================================

    async def send_preview(
        self,
        bot:        Bot,
        admin_id:   int,
        text:       str,
        file_id:    Optional[str] = None,
        media_type: Optional[str] = None,
    ) -> bool:
        """
        Send a preview of the broadcast to the admin only.
        Called before confirmation to let admin verify.

        Args:
            bot:        Telegram Bot instance
            admin_id:   Admin's Telegram user ID
            text:       Broadcast message text
            file_id:    Optional file_id
            media_type: Media type

        Returns:
            True if preview sent successfully
        """
        return await self.send_to_user(
            bot=        bot,
            user_id=    admin_id,
            text=       f"📋 *Broadcast Preview:*\n\n{text}",
            file_id=    file_id,
            media_type= media_type,
        )