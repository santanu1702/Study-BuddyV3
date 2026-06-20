# ============================================================
#         StudyBuddyV3BOT — Config Package Init
#         Exposes settings and constants at package level
# ============================================================

from config.settings import settings
from config.constants import (
    BotState,
    UserRole,
    NoteStatus,
    Language,
    AdminAction,
    CallbackPrefix,
    TimeConstants,
    LimitConstants,
    EmojiConstants,
)

__all__ = [
    # Settings singleton — use everywhere as: from config import settings
    "settings",

    # Enums & Constants
    "BotState",
    "UserRole",
    "NoteStatus",
    "Language",
    "AdminAction",
    "CallbackPrefix",
    "TimeConstants",
    "LimitConstants",
    "EmojiConstants",
]