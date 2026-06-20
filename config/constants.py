# ============================================================
#         StudyBuddyV3BOT — App-Wide Constants & Enums
#         Single source of truth for all constant values
# ============================================================

from enum import Enum, auto


# ============================================================
#   BOT STATES
#   Tracks what a user is currently doing
#   Stored in context.user_data["state"]
# ============================================================

class BotState(str, Enum):
    """
    Represents the current conversational state of a user.
    Used by the text message router in main.py to decide
    which handler should process the incoming message.
    """

    # ── Default state ──
    IDLE                  = "idle"

    # ── AI Assistant states ──
    AWAITING_AI_QUESTION  = "awaiting_ai_question"

    # ── Translator states ──
    AWAITING_TRANSLATION  = "awaiting_translation"
    AWAITING_TARGET_LANG  = "awaiting_target_lang"

    # ── Notes states ──
    AWAITING_NOTE_TITLE   = "awaiting_note_title"
    AWAITING_NOTE_CONTENT = "awaiting_note_content"

    # ── Admin states ──
    AWAITING_BROADCAST    = "awaiting_broadcast"
    AWAITING_BAN_ID       = "awaiting_ban_id"
    AWAITING_UNBAN_ID     = "awaiting_unban_id"
    AWAITING_ADMIN_SECRET = "awaiting_admin_secret"


# ============================================================
#   USER ROLES
#   Permission levels for access control
# ============================================================

class UserRole(str, Enum):
    """
    Defines permission levels for users.
    Stored in the database per user document.
    """
    USER    = "user"      # Regular user — default
    ADMIN   = "admin"     # Bot administrator
    BANNED  = "banned"    # Banned — cannot use the bot


# ============================================================
#   NOTE STATUS
#   Lifecycle states for user notes
# ============================================================

class NoteStatus(str, Enum):
    """
    Represents the status of a saved note.
    Soft-delete pattern — notes are marked deleted, not removed.
    """
    ACTIVE  = "active"    # Note is visible and accessible
    DELETED = "deleted"   # Soft-deleted by the user


# ============================================================
#   SUPPORTED LANGUAGES
#   Language codes used throughout the bot
# ============================================================

class Language(str, Enum):
    """
    Supported bot interface languages.
    Maps to locale files in the locales/ directory.
    """
    ENGLISH  = "en"
    HINDI    = "hi"
    BENGALI  = "bn"
    ARABIC   = "ar"

    @classmethod
    def choices(cls) -> list[str]:
        """Return list of all supported language codes."""
        return [lang.value for lang in cls]

    @classmethod
    def display_names(cls) -> dict[str, str]:
        """Return mapping of code → display name."""
        return {
            cls.ENGLISH.value:  "🇬🇧 English",
            cls.HINDI.value:    "🇮🇳 हिंदी",
            cls.BENGALI.value:  "🇧🇩 বাংলা",
            cls.ARABIC.value:   "🇸🇦 العربية",
        }

    @classmethod
    def from_telegram_code(cls, code: str) -> "Language":
        """
        Map a Telegram language_code to our supported Language.
        Falls back to ENGLISH if not supported.
        """
        mapping = {
            "en":    cls.ENGLISH,
            "en-us": cls.ENGLISH,
            "en-gb": cls.ENGLISH,
            "hi":    cls.HINDI,
            "bn":    cls.BENGALI,
            "ar":    cls.ARABIC,
        }
        return mapping.get(code.lower() if code else "en", cls.ENGLISH)


# ============================================================
#   ADMIN ACTIONS
#   All admin panel action identifiers
# ============================================================

class AdminAction(str, Enum):
    """
    Identifiers for admin panel actions.
    Used in callback data for inline button routing.
    """
    # ── Stats ──
    TOTAL_USERS       = "total_users"
    ACTIVE_USERS      = "active_users"
    API_STATS         = "api_stats"

    # ── User Management ──
    BAN_USER          = "ban_user"
    UNBAN_USER        = "unban_user"
    LIST_BANNED       = "list_banned"

    # ── Broadcast ──
    BROADCAST         = "broadcast"
    BROADCAST_CONFIRM = "broadcast_confirm"
    BROADCAST_CANCEL  = "broadcast_cancel"

    # ── System ──
    MAINTENANCE_ON    = "maintenance_on"
    MAINTENANCE_OFF   = "maintenance_off"
    VIEW_LOGS         = "view_logs"
    CLEAR_LOGS        = "clear_logs"

    # ── Navigation ──
    BACK_TO_PANEL     = "back_to_panel"
    REFRESH           = "refresh"


# ============================================================
#   CALLBACK PREFIXES
#   Inline keyboard callback data prefixes
#   Must match patterns registered in main.py
# ============================================================

class CallbackPrefix:
    """
    Prefix constants for all inline keyboard callback data.
    Format: prefix:action:optional_param

    Example: "notes:delete:note_id_123"
    """

    # ── Navigation ──
    MENU        = "menu"

    # ── Features ──
    AI          = "ai"
    CALC        = "calc"
    TRANS       = "trans"
    NOTES       = "notes"
    LANG        = "lang"

    # ── Admin ──
    ADMIN       = "admin"

    # ── Separators ──
    SEP         = ":"           # Standard separator
    NULL        = "noop"        # No-operation button (decorative)

    @classmethod
    def build(cls, prefix: str, *args: str) -> str:
        """
        Build a callback data string from parts.

        Usage:
            CallbackPrefix.build("notes", "delete", note_id)
            → "notes:delete:note_id"
        """
        parts = [prefix] + [str(a) for a in args]
        return cls.SEP.join(parts)

    @classmethod
    def parse(cls, callback_data: str) -> list[str]:
        """
        Parse a callback data string into parts.

        Usage:
            CallbackPrefix.parse("notes:delete:abc123")
            → ["notes", "delete", "abc123"]
        """
        return callback_data.split(cls.SEP)


# ============================================================
#   TIME CONSTANTS
#   All time values in seconds for consistency
# ============================================================

class TimeConstants:
    """
    Centralized time constants used across the bot.
    All values in seconds unless specified.
    """

    # ── AI Context ──
    AI_CONTEXT_EXPIRY        = 3600        # 1 hour — context memory TTL
    AI_CONTEXT_MAX_MESSAGES  = 20          # Max messages in memory

    # ── Rate Limiting ──
    RATE_LIMIT_WINDOW        = 60          # 1 minute window
    AI_RATE_LIMIT_WINDOW     = 3600        # 1 hour window for AI calls
    RATE_LIMIT_COOLDOWN      = 60          # Cooldown after hitting limit

    # ── Session ──
    USER_SESSION_EXPIRY      = 86400       # 24 hours
    ADMIN_SESSION_EXPIRY     = 3600        # 1 hour

    # ── Active User Tracking ──
    ACTIVE_USER_WINDOW_DAY   = 86400       # 24 hours
    ACTIVE_USER_WINDOW_WEEK  = 604800      # 7 days

    # ── UI Feedback ──
    PROCESSING_DELETE_DELAY  = 2           # Seconds before deleting "processing..." msg
    TYPING_ACTION_INTERVAL   = 4           # Seconds between typing actions

    # ── Broadcast ──
    BROADCAST_DELAY          = 0.05        # Seconds between each broadcast message
    BROADCAST_CONFIRM_EXPIRY = 300         # 5 min to confirm broadcast

    # ── Cache ──
    TRANSLATION_CACHE_TTL    = 3600        # Cache translation results for 1 hour
    STATS_CACHE_TTL          = 300         # Cache admin stats for 5 minutes


# ============================================================
#   LIMIT CONSTANTS
#   App-wide numeric limits
# ============================================================

class LimitConstants:
    """
    All numeric limits used across the bot.
    Centralizing here makes tuning easy.
    """

    # ── Notes ──
    MAX_NOTES_PER_USER       = 50          # Max notes a user can save
    MAX_NOTE_TITLE_LENGTH    = 100         # Max note title characters
    MAX_NOTE_CONTENT_LENGTH  = 2000        # Max note body characters

    # ── Messages ──
    MAX_MESSAGE_LENGTH       = 4096        # Telegram max message length
    MAX_CAPTION_LENGTH       = 1024        # Telegram max caption length
    LONG_MESSAGE_THRESHOLD   = 3000        # Split messages above this

    # ── AI ──
    MAX_AI_QUESTION_LENGTH   = 1000        # Max user question length
    MAX_AI_RESPONSE_TOKENS   = 1000        # Max tokens in AI response
    AI_CONTEXT_MAX_MESSAGES  = 20          # Max messages in context window

    # ── Rate Limiting ──
    RATE_LIMIT_MESSAGES      = 10          # Max messages per minute
    AI_RATE_LIMIT_PER_HOUR   = 20          # Max AI requests per hour

    # ── Admin ──
    MAX_BROADCAST_LENGTH     = 4000        # Max broadcast message length
    MAX_BANNED_LIST_DISPLAY  = 20          # Max banned users shown at once
    MAX_LOG_LINES_DISPLAY    = 50          # Max log lines shown in panel

    # ── Translation ──
    MAX_TRANSLATION_LENGTH   = 1000        # Max text length for translation

    # ── Calculator ──
    MAX_CALC_EXPRESSION_LEN  = 200         # Max calculator expression length
    MAX_CALC_RESULT_VALUE    = 1e15        # Max result before overflow warning

    # ── Pagination ──
    NOTES_PER_PAGE           = 5          # Notes shown per page
    USERS_PER_PAGE           = 10         # Users shown per page in admin


# ============================================================
#   EMOJI CONSTANTS
#   Centralized emoji for consistent UI across all messages
# ============================================================

class EmojiConstants:
    """
    All emoji used in bot messages and keyboards.
    Changing here updates the entire UI consistently.
    """

    # ── Features ──
    AI           = "🤖"
    CALCULATOR   = "🧮"
    TRANSLATOR   = "🌐"
    NOTES        = "📚"
    LANGUAGE     = "🌍"
    ADMIN        = "👑"
    SETTINGS     = "⚙️"
    HELP         = "❓"

    # ── Status ──
    SUCCESS      = "✅"
    ERROR        = "❌"
    WARNING      = "⚠️"
    INFO         = "ℹ️"
    LOADING      = "⏳"
    PROCESSING   = "🔄"

    # ── Actions ──
    SAVE         = "💾"
    DELETE       = "🗑️"
    EDIT         = "✏️"
    VIEW         = "👁️"
    SEARCH       = "🔍"
    SEND         = "📤"
    BACK         = "◀️"
    NEXT         = "▶️"
    CLOSE        = "✖️"
    REFRESH      = "🔃"
    CONFIRM      = "✔️"
    CANCEL       = "🚫"

    # ── Admin ──
    BAN          = "🔨"
    UNBAN        = "🔓"
    BROADCAST    = "📢"
    MAINTENANCE  = "🔧"
    STATS        = "📊"
    LOGS         = "📋"
    USERS        = "👥"

    # ── Misc UI ──
    STAR         = "⭐"
    FIRE         = "🔥"
    ROCKET       = "🚀"
    LOCK         = "🔐"
    KEY          = "🔑"
    BELL         = "🔔"
    CLOCK        = "🕐"
    SPARKLE      = "✨"
    WAVE         = "👋"
    THINK        = "🤔"
    STUDY        = "📖"
    MATH         = "➕"
    GLOBE        = "🌏"
    BOT          = "🤖"


# ============================================================
#   DATABASE COLLECTION NAMES
#   Centralized MongoDB collection name constants
# ============================================================

class Collections:
    """
    MongoDB collection name constants.
    Use these instead of hardcoded strings everywhere.
    """
    USERS        = "users"
    NOTES        = "notes"
    AI_CONTEXT   = "ai_context"
    ADMIN_LOGS   = "admin_logs"
    BROADCASTS   = "broadcasts"
    API_STATS    = "api_stats"
    RATE_LIMITS  = "rate_limits"


# ============================================================
#   ERROR CODES
#   Standardized error code constants for logging
# ============================================================

class ErrorCode:
    """
    Standardized error codes for consistent logging
    and error tracking across the bot.
    """

    # ── AI Errors ──
    AI_RATE_LIMIT        = "E001"
    AI_API_ERROR         = "E002"
    AI_CONTEXT_ERROR     = "E003"
    AI_TIMEOUT           = "E004"

    # ── Database Errors ──
    DB_CONNECTION        = "E010"
    DB_WRITE_ERROR       = "E011"
    DB_READ_ERROR        = "E012"
    DB_NOT_FOUND         = "E013"

    # ── User Errors ──
    USER_BANNED          = "E020"
    USER_NOT_FOUND       = "E021"
    USER_RATE_LIMITED    = "E022"

    # ── Translation Errors ──
    TRANS_API_ERROR      = "E030"
    TRANS_LANG_NOT_FOUND = "E031"

    # ── Admin Errors ──
    ADMIN_UNAUTHORIZED   = "E040"
    ADMIN_BROADCAST_FAIL = "E041"

    # ── System Errors ──
    MAINTENANCE_MODE     = "E050"
    UNKNOWN_ERROR        = "E999"