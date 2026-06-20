# ============================================================
#         StudyBuddyV3BOT — Settings & Configuration
#         Loads, validates, and exposes all .env variables
#         Uses Pydantic v2 Settings for type-safe config
# ============================================================

import os
from pathlib import Path
from typing import List
from functools import lru_cache

from pydantic import (
    Field,
    field_validator,
    model_validator,
    SecretStr,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Project root directory — used for resolving relative paths
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent


# ============================================================
#   MAIN SETTINGS CLASS
# ============================================================

class Settings(BaseSettings):
    """
    Central configuration class for StudyBuddyV3BOT.

    Loads all environment variables from .env file,
    validates types, and provides defaults where safe.

    Usage anywhere in the project:
        from config.settings import settings
        print(settings.BOT_TOKEN)
    """

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",          # Load from .env at project root
        env_file_encoding="utf-8",           # UTF-8 encoding
        case_sensitive=False,                # BOT_TOKEN == bot_token
        extra="ignore",                      # Ignore unknown env vars
        validate_default=True,               # Validate even default values
    )

    # ================================================================
    #   🤖 TELEGRAM BOT
    # ================================================================

    BOT_TOKEN: SecretStr = Field(
        ...,                                 # Required — no default
        description="Telegram Bot API token from @BotFather",
    )

    # ================================================================
    #   🗄️ MONGODB DATABASE
    # ================================================================

    MONGO_URI: SecretStr = Field(
        ...,
        description="MongoDB Atlas connection URI",
    )

    DB_NAME: str = Field(
        default="studybuddy_db",
        description="MongoDB database name",
    )

    # ================================================================
    #   🧠 OPENAI
    # ================================================================

    OPENAI_API_KEY: SecretStr = Field(
        ...,
        description="OpenAI API key from platform.openai.com",
    )

    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use for AI responses",
    )

    OPENAI_MAX_TOKENS: int = Field(
        default=1000,
        ge=100,                              # Min 100 tokens
        le=4096,                             # Max 4096 tokens
        description="Maximum tokens per AI response",
    )

    OPENAI_TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,                              # Min 0.0 (deterministic)
        le=1.0,                              # Max 1.0 (creative)
        description="AI response creativity (0=focused, 1=creative)",
    )

    # ================================================================
    #   👑 ADMIN CONFIGURATION
    # ================================================================

    ADMIN_IDS: List[int] = Field(
        default=[],
        description="Comma-separated list of admin Telegram user IDs",
    )

    ADMIN_SECRET: str = Field(
        default="studybuddy_admin_2024",
        description="Secret passphrase for admin panel access",
    )

    # ================================================================
    #   🚦 RATE LIMITING
    # ================================================================

    RATE_LIMIT_MESSAGES: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Max messages per user per minute",
    )

    AI_RATE_LIMIT_PER_HOUR: int = Field(
        default=20,
        ge=1,
        le=200,
        description="Max AI requests per user per hour",
    )

    RATE_LIMIT_COOLDOWN: int = Field(
        default=60,
        ge=10,
        le=3600,
        description="Cooldown seconds after hitting rate limit",
    )

    # ================================================================
    #   🌍 LANGUAGE & LOCALIZATION
    # ================================================================

    DEFAULT_LANGUAGE: str = Field(
        default="en",
        description="Default bot language code (en, hi, bn, ar)",
    )

    # ================================================================
    #   ⚙️ BOT SETTINGS
    # ================================================================

    ENVIRONMENT: str = Field(
        default="production",
        description="Bot environment: development | production",
    )

    MAINTENANCE_MODE: bool = Field(
        default=False,
        description="Enable maintenance mode — blocks all non-admin users",
    )

    MAINTENANCE_MESSAGE: str = Field(
        default="🔧 Bot is under maintenance. Please try again later.",
        description="Message shown to users during maintenance",
    )

    MAX_NOTES_PER_USER: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum notes a single user can save",
    )

    MAX_NOTE_LENGTH: int = Field(
        default=2000,
        ge=100,
        le=5000,
        description="Maximum characters per note",
    )

    # ================================================================
    #   📝 LOGGING
    # ================================================================

    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG | INFO | WARNING | ERROR | CRITICAL",
    )

    LOG_FILE: str = Field(
        default="logs/studybuddy.log",
        description="Path to log file (relative to project root)",
    )

    LOG_MAX_SIZE_MB: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Max log file size in MB before rotation",
    )

    LOG_BACKUP_COUNT: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of backup log files to keep",
    )

    # ================================================================
    #   🔄 AI CONTEXT MEMORY
    # ================================================================

    AI_CONTEXT_MAX_MESSAGES: int = Field(
        default=20,
        ge=2,
        le=50,
        description="Max messages to keep in AI conversation context",
    )

    AI_CONTEXT_EXPIRY: int = Field(
        default=3600,
        ge=300,
        le=86400,
        description="Seconds before AI context expires (default: 1 hour)",
    )

    # ================================================================
    #   📡 POLLING SETTINGS
    # ================================================================

    POLL_INTERVAL: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Polling interval in seconds",
    )

    POLL_TIMEOUT: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Polling timeout in seconds",
    )

    DROP_PENDING_UPDATES: bool = Field(
        default=True,
        description="Drop stale updates on bot startup",
    )

    # ================================================================
    #   FIELD VALIDATORS
    # ================================================================

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, value) -> List[int]:
        """
        Parse ADMIN_IDS from various formats:
        - Already a list: [123, 456]
        - Comma-separated string: "123,456"
        - Single string: "123"
        """
        if isinstance(value, list):
            return [int(v) for v in value]

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            # Split by comma, strip spaces, convert to int
            try:
                return [
                    int(id_.strip())
                    for id_ in value.split(",")
                    if id_.strip()
                ]
            except ValueError as e:
                raise ValueError(
                    f"ADMIN_IDS must be comma-separated integers. Got: {value}"
                ) from e

        if isinstance(value, int):
            return [value]

        return []

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Ensure LOG_LEVEL is a valid Python logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper().strip()
        if upper not in valid_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_levels}. Got: {value}"
            )
        return upper

    @field_validator("DEFAULT_LANGUAGE", mode="before")
    @classmethod
    def validate_language(cls, value: str) -> str:
        """Ensure DEFAULT_LANGUAGE is a supported language code."""
        supported = {"en", "hi", "bn", "ar"}
        lower = value.lower().strip()
        if lower not in supported:
            raise ValueError(
                f"DEFAULT_LANGUAGE must be one of {supported}. Got: {value}"
            )
        return lower

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        """Ensure ENVIRONMENT is either 'development' or 'production'."""
        valid = {"development", "production", "staging"}
        lower = value.lower().strip()
        if lower not in valid:
            raise ValueError(
                f"ENVIRONMENT must be one of {valid}. Got: {value}"
            )
        return lower

    @field_validator("OPENAI_MODEL", mode="before")
    @classmethod
    def validate_openai_model(cls, value: str) -> str:
        """Validate that an OpenAI model string is provided."""
        if not value or not value.strip():
            raise ValueError("OPENAI_MODEL cannot be empty.")
        return value.strip()

    # ================================================================
    #   MODEL VALIDATORS (cross-field validation)
    # ================================================================

    @model_validator(mode="after")
    def validate_admin_ids_not_empty_in_production(self) -> "Settings":
        """
        Warn if no admin IDs are set in production.
        Not a hard error — but logs a warning.
        """
        if self.ENVIRONMENT == "production" and not self.ADMIN_IDS:
            import warnings
            warnings.warn(
                "⚠️  No ADMIN_IDS set in production! "
                "Admin panel will be inaccessible.",
                UserWarning,
                stacklevel=2,
            )
        return self

    # ================================================================
    #   COMPUTED PROPERTIES
    #   Derived values built from raw settings
    # ================================================================

    @property
    def bot_token(self) -> str:
        """Return BOT_TOKEN as plain string (unwrapped from SecretStr)."""
        return self.BOT_TOKEN.get_secret_value()

    @property
    def mongo_uri(self) -> str:
        """Return MONGO_URI as plain string."""
        return self.MONGO_URI.get_secret_value()

    @property
    def openai_api_key(self) -> str:
        """Return OPENAI_API_KEY as plain string."""
        return self.OPENAI_API_KEY.get_secret_value()

    @property
    def is_production(self) -> bool:
        """True if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """True if running in development environment."""
        return self.ENVIRONMENT == "development"

    @property
    def is_maintenance(self) -> bool:
        """True if maintenance mode is currently active."""
        return self.MAINTENANCE_MODE

    @property
    def log_file_path(self) -> Path:
        """Return absolute path to the log file."""
        path = Path(self.LOG_FILE)
        if not path.is_absolute():
            path = ROOT_DIR / path
        return path

    @property
    def log_max_bytes(self) -> int:
        """Return log max size in bytes (for RotatingFileHandler)."""
        return self.LOG_MAX_SIZE_MB * 1024 * 1024

    def is_admin(self, user_id: int) -> bool:
        """
        Check if a given Telegram user ID is an admin.

        Usage:
            if settings.is_admin(update.effective_user.id):
                ...
        """
        return user_id in self.ADMIN_IDS

    def mask_sensitive(self) -> dict:
        """
        Return settings as dict with sensitive values masked.
        Safe for logging — never logs raw API keys.
        """
        return {
            "BOT_TOKEN":          f"...{self.bot_token[-6:]}",
            "MONGO_URI":          "***masked***",
            "OPENAI_API_KEY":     f"sk-...{self.openai_api_key[-4:]}",
            "OPENAI_MODEL":       self.OPENAI_MODEL,
            "OPENAI_MAX_TOKENS":  self.OPENAI_MAX_TOKENS,
            "OPENAI_TEMPERATURE": self.OPENAI_TEMPERATURE,
            "ADMIN_IDS":          self.ADMIN_IDS,
            "ENVIRONMENT":        self.ENVIRONMENT,
            "MAINTENANCE_MODE":   self.MAINTENANCE_MODE,
            "DEFAULT_LANGUAGE":   self.DEFAULT_LANGUAGE,
            "LOG_LEVEL":          self.LOG_LEVEL,
            "DB_NAME":            self.DB_NAME,
            "RATE_LIMIT_MESSAGES": self.RATE_LIMIT_MESSAGES,
            "AI_RATE_LIMIT_PER_HOUR": self.AI_RATE_LIMIT_PER_HOUR,
            "POLL_INTERVAL":      self.POLL_INTERVAL,
            "DROP_PENDING_UPDATES": self.DROP_PENDING_UPDATES,
        }

    def __repr__(self) -> str:
        """Safe repr — never exposes secrets."""
        return (
            f"Settings("
            f"env={self.ENVIRONMENT}, "
            f"model={self.OPENAI_MODEL}, "
            f"admins={self.ADMIN_IDS}, "
            f"maintenance={self.MAINTENANCE_MODE}"
            f")"
        )


# ============================================================
#   SINGLETON INSTANCE
#   Import this everywhere: from config.settings import settings
# ============================================================

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached singleton Settings instance.
    .env is only read once — efficient for production.
    """
    return Settings()


# ---------------------------------------------------------------------------
# Module-level singleton — primary way to use settings
# ---------------------------------------------------------------------------
settings: Settings = get_settings()