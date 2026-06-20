# ============================================================
#         StudyBuddyV3BOT — Utils Package Init
#         Exposes all utility functions and classes
#         at package level for clean imports
# ============================================================

from utils.logger import (
    setup_logger,
    get_logger,
)

from utils.helpers import (
    edit_or_send,
    answer_callback,
    split_long_message,
    sanitize_input,
    format_datetime,
    humanize_number,
)

from utils.validators import (
    validate_user_id,
    validate_language_code,
    validate_note_content,
    validate_translation_text,
    validate_calc_expression,
    validate_broadcast_text,
)

__all__ = [
    # ── Logger ──
    "setup_logger",           # Initialize logging system
    "get_logger",             # Get named logger instance

    # ── Helpers ──
    "edit_or_send",           # Edit existing or send new message
    "answer_callback",        # Answer callback query safely
    "split_long_message",     # Split messages over 4096 chars
    "sanitize_input",         # Clean user input text
    "format_datetime",        # Format datetime for display
    "humanize_number",        # Format numbers (1000 → 1K)

    # ── Validators ──
    "validate_user_id",         # Validate Telegram user ID
    "validate_language_code",   # Validate language code
    "validate_note_content",    # Validate note text
    "validate_translation_text",# Validate translation input
    "validate_calc_expression", # Validate calculator expression
    "validate_broadcast_text",  # Validate broadcast message
]