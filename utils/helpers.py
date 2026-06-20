# ============================================================
#         StudyBuddyV3BOT — Helper Utilities
#         Shared utility functions used across all handlers
#         Telegram UI helpers + formatting functions
# ============================================================

import re
import html
from datetime import datetime, timezone
from typing import Optional, List

from telegram import Update, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes
from telegram.error import TelegramError, BadRequest

from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
#   TELEGRAM UI HELPERS
# ============================================================

async def edit_or_send(
    update:   Update,
    context:  ContextTypes.DEFAULT_TYPE,
    text:     str,
    keyboard: Optional[InlineKeyboardMarkup] = None,
) -> None:
    """
    Edit existing message if from callback query,
    otherwise send a new message.

    This is the primary navigation function used across
    all handlers — keeps the UI clean by editing in-place
    instead of sending new messages.

    Args:
        update:   Telegram Update object
        context:  Handler context
        text:     Message text (Markdown supported)
        keyboard: Optional inline keyboard markup
    """
    try:
        if update.callback_query:
            # ── Edit existing message ──
            await update.callback_query.edit_message_text(
                text=         text,
                parse_mode=   "Markdown",
                reply_markup= keyboard,
            )
        elif update.message:
            # ── Send new message ──
            await update.message.reply_text(
                text=         text,
                parse_mode=   "Markdown",
                reply_markup= keyboard,
            )

    except BadRequest as e:
        error_msg = str(e).lower()

        # ── Message not modified — ignore ──
        if "message is not modified" in error_msg:
            return

        # ── Message too long — split and send ──
        if "message is too long" in error_msg:
            parts = split_long_message(text)
            for i, part in enumerate(parts):
                kb = keyboard if i == len(parts) - 1 else None
                try:
                    if update.callback_query:
                        await update.callback_query.message.reply_text(
                            text=         part,
                            parse_mode=   "Markdown",
                            reply_markup= kb,
                        )
                    elif update.message:
                        await update.message.reply_text(
                            text=         part,
                            parse_mode=   "Markdown",
                            reply_markup= kb,
                        )
                except Exception:
                    pass
            return

        logger.warning(f"edit_or_send BadRequest: {e}")

    except TelegramError as e:
        logger.warning(f"edit_or_send TelegramError: {e}")

    except Exception as e:
        logger.error(f"edit_or_send unexpected error: {e}")


async def answer_callback(
    callback_query,
    text:       str  = "",
    show_alert: bool = False,
) -> None:
    """
    Safely answer a callback query.
    Handles already-answered callbacks gracefully.

    Args:
        callback_query: Telegram CallbackQuery object
        text:           Optional popup text
        show_alert:     True for alert popup, False for toast
    """
    try:
        await callback_query.answer(
            text=       text,
            show_alert= show_alert,
        )
    except BadRequest as e:
        if "query is too old" in str(e).lower():
            pass  # Callback expired — ignore
        else:
            logger.warning(f"answer_callback error: {e}")
    except Exception as e:
        logger.warning(f"answer_callback unexpected: {e}")


# ============================================================
#   MESSAGE SPLITTING
# ============================================================

def split_long_message(
    text:      str,
    max_length: int = 4000,
) -> List[str]:
    """
    Split a long message into chunks under max_length.
    Tries to split at natural break points (newlines).

    Args:
        text:       Full message text
        max_length: Max chars per chunk (default: 4000)

    Returns:
        List of message chunks

    Usage:
        parts = split_long_message(long_response)
        for part in parts:
            await message.reply_text(part)
    """
    if len(text) <= max_length:
        return [text]

    parts  = []
    current = ""

    # Split by lines first
    lines = text.split("\n")

    for line in lines:
        # Single line exceeds limit — force split
        if len(line) > max_length:
            if current:
                parts.append(current.strip())
                current = ""
            # Split the long line by words
            words = line.split(" ")
            for word in words:
                if len(current) + len(word) + 1 > max_length:
                    if current:
                        parts.append(current.strip())
                    current = word + " "
                else:
                    current += word + " "
            continue

        # Adding this line would exceed limit
        if len(current) + len(line) + 1 > max_length:
            if current:
                parts.append(current.strip())
            current = line + "\n"
        else:
            current += line + "\n"

    # Add remaining content
    if current.strip():
        parts.append(current.strip())

    return parts if parts else [text]


# ============================================================
#   INPUT SANITIZATION
# ============================================================

def sanitize_input(text: str) -> str:
    """
    Sanitize user input text.
    Removes potentially dangerous content while
    preserving legitimate study content.

    Operations:
    - Strip leading/trailing whitespace
    - Normalize multiple spaces
    - Remove null bytes
    - Limit consecutive newlines to 3

    Args:
        text: Raw user input text

    Returns:
        Sanitized text string
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace("\x00", "")

    # Strip leading/trailing whitespace
    text = text.strip()

    # Normalize multiple consecutive spaces
    text = re.sub(r" {3,}", "  ", text)

    # Limit consecutive newlines to 3
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    # Remove invisible unicode characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

    return text


def escape_markdown(text: str) -> str:
    """
    Escape special Markdown characters in text.
    Used when inserting user content into Markdown messages.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for Markdown
    """
    # Characters that need escaping in Telegram Markdown
    special_chars = [
        "_", "*", "[", "]", "(", ")",
        "~", "`", ">", "#", "+", "-",
        "=", "|", "{", "}", ".", "!",
    ]

    for char in special_chars:
        text = text.replace(char, f"\\{char}")

    return text


def truncate_text(
    text:       str,
    max_length: int,
    suffix:     str = "...",
) -> str:
    """
    Truncate text to max_length with suffix.

    Args:
        text:       Text to truncate
        max_length: Maximum character length
        suffix:     Appended when truncated (default: "...")

    Returns:
        Truncated text

    Usage:
        short = truncate_text("Very long text here", max_length=10)
        # → "Very long..."
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


# ============================================================
#   DATE & TIME FORMATTING
# ============================================================

def format_datetime(
    dt:     Optional[datetime],
    format: str = "%d %b %Y, %H:%M",
) -> str:
    """
    Format a datetime object for display in messages.

    Args:
        dt:     Datetime to format (None returns "Unknown")
        format: strftime format string

    Returns:
        Formatted datetime string

    Usage:
        formatted = format_datetime(user.last_active)
        # → "15 Jan 2024, 14:30"
    """
    if dt is None:
        return "Unknown"

    try:
        # Handle timezone-aware datetimes
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt.strftime(format)
    except Exception:
        return "Unknown"


def format_date(dt: Optional[datetime]) -> str:
    """
    Format a datetime as date only.

    Args:
        dt: Datetime to format

    Returns:
        Date string e.g. "15 Jan 2024"
    """
    return format_datetime(dt, format="%d %b %Y")


def format_time_ago(dt: Optional[datetime]) -> str:
    """
    Format a datetime as relative time (e.g. "2 hours ago").

    Args:
        dt: Past datetime to format

    Returns:
        Human-readable relative time string
    """
    if dt is None:
        return "Unknown"

    try:
        now     = datetime.utcnow()
        diff    = now - dt
        seconds = int(diff.total_seconds())

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            mins = seconds // 60
            return f"{mins} minute{'s' if mins != 1 else ''} ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 604800:
            days = seconds // 86400
            return f"{days} day{'s' if days != 1 else ''} ago"
        elif seconds < 2592000:
            weeks = seconds // 604800
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        else:
            return format_date(dt)

    except Exception:
        return "Unknown"


# ============================================================
#   NUMBER FORMATTING
# ============================================================

def humanize_number(n: int) -> str:
    """
    Format large numbers in human-readable form.

    Args:
        n: Integer to format

    Returns:
        Human-readable string

    Examples:
        humanize_number(1000)      → "1,000"
        humanize_number(1500000)   → "1.5M"
        humanize_number(2000000000)→ "2B"
    """
    if n is None:
        return "0"

    try:
        n = int(n)

        if n < 1000:
            return str(n)
        elif n < 1_000_000:
            if n % 1000 == 0:
                return f"{n // 1000}K"
            return f"{n / 1000:.1f}K"
        elif n < 1_000_000_000:
            if n % 1_000_000 == 0:
                return f"{n // 1_000_000}M"
            return f"{n / 1_000_000:.1f}M"
        else:
            if n % 1_000_000_000 == 0:
                return f"{n // 1_000_000_000}B"
            return f"{n / 1_000_000_000:.1f}B"

    except Exception:
        return str(n)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable form.

    Args:
        size_bytes: File size in bytes

    Returns:
        Human-readable size string

    Examples:
        format_file_size(1024)        → "1.0 KB"
        format_file_size(1048576)     → "1.0 MB"
    """
    try:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 ** 3:
            return f"{size_bytes / (1024 ** 2):.1f} MB"
        else:
            return f"{size_bytes / (1024 ** 3):.1f} GB"
    except Exception:
        return "Unknown"


# ============================================================
#   MISC UTILITIES
# ============================================================

def is_valid_user_id(user_id: any) -> bool:
    """
    Check if a value is a valid Telegram user ID.

    Args:
        user_id: Value to check

    Returns:
        True if valid Telegram user ID
    """
    try:
        uid = int(user_id)
        return uid > 0
    except (TypeError, ValueError):
        return False


def extract_user_id(text: str) -> Optional[int]:
    """
    Extract a Telegram user ID from text input.
    Handles plain numbers and @username mentions.

    Args:
        text: Input text (e.g. "123456789" or "@username")

    Returns:
        Integer user ID or None if not found
    """
    if not text:
        return None

    text = text.strip()

    # Plain numeric ID
    if text.isdigit():
        uid = int(text)
        return uid if uid > 0 else None

    # Remove @ prefix
    if text.startswith("@"):
        return None  # Username — needs DB lookup

    return None


def chunk_list(lst: list, chunk_size: int) -> List[list]:
    """
    Split a list into chunks of specified size.

    Args:
        lst:        List to split
        chunk_size: Max items per chunk

    Returns:
        List of list chunks

    Usage:
        chunks = chunk_list([1,2,3,4,5], 2)
        # → [[1,2], [3,4], [5]]
    """
    return [
        lst[i:i + chunk_size]
        for i in range(0, len(lst), chunk_size)
    ]


def bold(text: str) -> str:
    """Wrap text in Markdown bold."""
    return f"*{text}*"


def italic(text: str) -> str:
    """Wrap text in Markdown italic."""
    return f"_{text}_"


def code(text: str) -> str:
    """Wrap text in Markdown code."""
    return f"`{text}`"


def code_block(text: str) -> str:
    """Wrap text in Markdown code block."""
    return f"```\n{text}\n```"