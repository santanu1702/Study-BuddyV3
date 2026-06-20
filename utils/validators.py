# ============================================================
#         StudyBuddyV3BOT — Input Validators
#         All input validation functions
#         Used across handlers before processing user input
# ============================================================

import re
from typing import Tuple, Optional

from config.constants import (
    Language,
    LimitConstants,
)
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
#   VALIDATION RESULT
#   Consistent return type for all validators
# ============================================================

def _result(
    valid:   bool,
    error:   str = "",
) -> Tuple[bool, str]:
    """
    Build a validation result tuple.

    Returns:
        Tuple of (is_valid, error_message)
        error_message is "" when valid
    """
    return valid, error


# ============================================================
#   USER ID VALIDATOR
# ============================================================

def validate_user_id(
    value: any,
) -> Tuple[bool, str]:
    """
    Validate a Telegram user ID.

    Rules:
    - Must be convertible to integer
    - Must be positive
    - Must be within valid Telegram ID range

    Args:
        value: Value to validate (string or int)

    Returns:
        Tuple of (is_valid, error_message)

    Usage:
        valid, error = validate_user_id("123456789")
        if not valid:
            await msg.reply(error)
    """
    if value is None:
        return _result(False, "User ID cannot be empty.")

    try:
        uid = int(str(value).strip())
    except (ValueError, TypeError):
        return _result(
            False,
            "⚠️ Invalid user ID. Please enter a numeric ID.\n"
            "_Example: `123456789`_"
        )

    if uid <= 0:
        return _result(
            False,
            "⚠️ User ID must be a positive number."
        )

    # Telegram user IDs are typically below 10 billion
    if uid > 10_000_000_000:
        return _result(
            False,
            "⚠️ Invalid user ID. Number is too large."
        )

    return _result(True)


# ============================================================
#   LANGUAGE CODE VALIDATOR
# ============================================================

def validate_language_code(
    lang_code: str,
) -> Tuple[bool, str]:
    """
    Validate a bot language code.

    Rules:
    - Must not be empty
    - Must be one of supported language codes

    Args:
        lang_code: Language code string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not lang_code or not lang_code.strip():
        return _result(False, "Language code cannot be empty.")

    normalized    = lang_code.lower().strip()
    valid_codes   = Language.choices()

    if normalized not in valid_codes:
        codes_str = ", ".join(f"`{c}`" for c in valid_codes)
        return _result(
            False,
            f"⚠️ Unsupported language: `{lang_code}`\n"
            f"Supported codes: {codes_str}"
        )

    return _result(True)


# ============================================================
#   NOTE CONTENT VALIDATOR
# ============================================================

def validate_note_content(
    content:   str,
    max_length: int = LimitConstants.MAX_NOTE_CONTENT_LENGTH,
) -> Tuple[bool, str]:
    """
    Validate note content before saving.

    Rules:
    - Must not be empty
    - Must not exceed max length
    - Must contain actual text (not just whitespace)
    - Must not be only special characters

    Args:
        content:    Note content string
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not content:
        return _result(False, "⚠️ Note content cannot be empty.")

    stripped = content.strip()

    if not stripped:
        return _result(
            False,
            "⚠️ Note content cannot be only whitespace."
        )

    if len(stripped) < 3:
        return _result(
            False,
            "⚠️ Note is too short. Please add more content."
        )

    if len(content) > max_length:
        return _result(
            False,
            f"⚠️ Note is too long.\n"
            f"Maximum: `{max_length}` characters\n"
            f"Your note: `{len(content)}` characters\n\n"
            f"Please shorten your note and try again."
        )

    return _result(True)


def validate_note_title(
    title:      str,
    max_length: int = LimitConstants.MAX_NOTE_TITLE_LENGTH,
) -> Tuple[bool, str]:
    """
    Validate a note title.

    Rules:
    - Can be empty (title is optional)
    - Must not exceed max length if provided

    Args:
        title:      Note title string
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not title:
        return _result(True)  # Title is optional

    if len(title.strip()) > max_length:
        return _result(
            False,
            f"⚠️ Title is too long.\n"
            f"Maximum: `{max_length}` characters."
        )

    return _result(True)


# ============================================================
#   TRANSLATION TEXT VALIDATOR
# ============================================================

def validate_translation_text(
    text:       str,
    max_length: int = LimitConstants.MAX_TRANSLATION_LENGTH,
) -> Tuple[bool, str]:
    """
    Validate text before translation.

    Rules:
    - Must not be empty
    - Must not exceed max length
    - Must contain actual text content

    Args:
        text:       Text to translate
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text:
        return _result(
            False,
            "⚠️ Please provide text to translate."
        )

    stripped = text.strip()

    if not stripped:
        return _result(
            False,
            "⚠️ Translation text cannot be only whitespace."
        )

    if len(stripped) < 1:
        return _result(
            False,
            "⚠️ Text is too short to translate."
        )

    if len(text) > max_length:
        return _result(
            False,
            f"⚠️ Text is too long for translation.\n"
            f"Maximum: `{max_length}` characters\n"
            f"Your text: `{len(text)}` characters\n\n"
            f"Please shorten and try again."
        )

    return _result(True)


def validate_target_language(
    lang_input: str,
) -> Tuple[bool, str]:
    """
    Validate a translation target language input.
    Accepts both codes and full names.

    Rules:
    - Must not be empty
    - Must be a non-empty string
    - Length check (language codes/names are short)

    Args:
        lang_input: Language code or name from user

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not lang_input or not lang_input.strip():
        return _result(
            False,
            "⚠️ Please provide a target language."
        )

    if len(lang_input.strip()) > 50:
        return _result(
            False,
            "⚠️ Language name is too long. "
            "Please use a valid language name or code."
        )

    # Check for obviously invalid input (numbers only)
    if lang_input.strip().isdigit():
        return _result(
            False,
            "⚠️ Invalid language. "
            "Please enter a language name like 'Hindi' or code like 'hi'."
        )

    return _result(True)


# ============================================================
#   CALCULATOR EXPRESSION VALIDATOR
# ============================================================

def validate_calc_expression(
    expression: str,
    max_length: int = LimitConstants.MAX_CALC_EXPRESSION_LEN,
) -> Tuple[bool, str]:
    """
    Validate a calculator expression before evaluation.

    Rules:
    - Must not be empty
    - Must not exceed max length
    - Must have balanced parentheses
    - Must not contain dangerous patterns

    Args:
        expression: Math expression string
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not expression or not expression.strip():
        return _result(False, "⚠️ Expression cannot be empty.")

    stripped = expression.strip()

    if len(stripped) > max_length:
        return _result(
            False,
            f"⚠️ Expression too long.\n"
            f"Maximum: `{max_length}` characters."
        )

    # ── Check balanced parentheses ──
    open_count  = stripped.count("(")
    close_count = stripped.count(")")

    if open_count != close_count:
        return _result(
            False,
            f"⚠️ Unbalanced parentheses.\n"
            f"Opening: `{open_count}` | "
            f"Closing: `{close_count}`"
        )

    # ── Check for dangerous patterns ──
    dangerous_patterns = [
        "__", "import", "exec", "eval",
        "open", "os.", "sys.", "subprocess",
        "globals", "locals", "builtins",
        "getattr", "setattr", "delattr",
        "compile", "memoryview",
    ]

    expr_lower = stripped.lower()
    for pattern in dangerous_patterns:
        if pattern in expr_lower:
            return _result(
                False,
                f"⚠️ Invalid expression. "
                f"Contains unsafe pattern: `{pattern}`"
            )

    # ── Must contain at least one digit or math constant ──
    has_number  = bool(re.search(r"\d", stripped))
    has_const   = any(
        c in stripped.lower()
        for c in ["pi", "e", "tau", "inf"]
    )

    if not has_number and not has_const:
        return _result(
            False,
            "⚠️ Expression must contain at least one number."
        )

    return _result(True)


# ============================================================
#   BROADCAST TEXT VALIDATOR
# ============================================================

def validate_broadcast_text(
    text:       str,
    max_length: int = LimitConstants.MAX_BROADCAST_LENGTH,
) -> Tuple[bool, str]:
    """
    Validate admin broadcast message text.

    Rules:
    - Must not be empty
    - Must not exceed max length
    - Must contain actual content

    Args:
        text:       Broadcast message text
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text:
        return _result(
            False,
            "⚠️ Broadcast message cannot be empty."
        )

    stripped = text.strip()

    if not stripped:
        return _result(
            False,
            "⚠️ Broadcast message cannot be only whitespace."
        )

    if len(stripped) < 5:
        return _result(
            False,
            "⚠️ Broadcast message is too short (minimum 5 characters)."
        )

    if len(text) > max_length:
        return _result(
            False,
            f"⚠️ Broadcast message is too long.\n"
            f"Maximum: `{max_length}` characters\n"
            f"Your message: `{len(text)}` characters"
        )

    return _result(True)


# ============================================================
#   AI QUESTION VALIDATOR
# ============================================================

def validate_ai_question(
    question:   str,
    max_length: int = LimitConstants.MAX_AI_QUESTION_LENGTH,
) -> Tuple[bool, str]:
    """
    Validate a user's AI question before processing.

    Rules:
    - Must not be empty
    - Must not exceed max length
    - Must contain actual question content

    Args:
        question:   User's question text
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not question:
        return _result(
            False,
            "⚠️ Question cannot be empty."
        )

    stripped = question.strip()

    if not stripped:
        return _result(
            False,
            "⚠️ Question cannot be only whitespace."
        )

    if len(stripped) < 2:
        return _result(
            False,
            "⚠️ Question is too short. Please ask a complete question."
        )

    if len(question) > max_length:
        return _result(
            False,
            f"⚠️ Question is too long.\n"
            f"Maximum: `{max_length}` characters\n"
            f"Your question: `{len(question)}` characters\n\n"
            f"Please shorten your question and try again."
        )

    return _result(True)


# ============================================================
#   GENERIC TEXT VALIDATOR
# ============================================================

def validate_text(
    text:       str,
    field_name: str = "Input",
    min_length: int = 1,
    max_length: int = 4096,
    required:   bool = True,
) -> Tuple[bool, str]:
    """
    Generic text validator for any text field.
    Use when specific validators don't apply.

    Args:
        text:       Text to validate
        field_name: Display name for error messages
        min_length: Minimum required length
        max_length: Maximum allowed length
        required:   Whether empty is allowed

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text or not text.strip():
        if required:
            return _result(
                False,
                f"⚠️ {field_name} cannot be empty."
            )
        return _result(True)

    stripped = text.strip()

    if len(stripped) < min_length:
        return _result(
            False,
            f"⚠️ {field_name} is too short.\n"
            f"Minimum: `{min_length}` characters."
        )

    if len(text) > max_length:
        return _result(
            False,
            f"⚠️ {field_name} is too long.\n"
            f"Maximum: `{max_length}` characters\n"
            f"Current: `{len(text)}` characters."
        )

    return _result(True)