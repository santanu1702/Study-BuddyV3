# ============================================================
#         StudyBuddyV3BOT — Logging System
#         File + console logging with rotation
#         Color-coded console output
#         Production-ready configuration
# ============================================================

import logging
import logging.handlers
import sys
from pathlib import Path

import colorlog

from config.settings import settings


# ============================================================
#   LOG FORMAT STRINGS
# ============================================================

# ── Console format (colored) ──
CONSOLE_FORMAT = (
    "%(log_color)s%(asctime)s%(reset)s "
    "%(log_color)s[%(levelname)-8s]%(reset)s "
    "%(cyan)s%(name)s%(reset)s "
    "%(log_color)s%(message)s%(reset)s"
)

# ── File format (plain text) ──
FILE_FORMAT = (
    "%(asctime)s "
    "[%(levelname)-8s] "
    "%(name)s "
    "%(message)s"
)

# ── Date format ──
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ── Color mapping for console output ──
LOG_COLORS = {
    "DEBUG":    "white",
    "INFO":     "green",
    "WARNING":  "yellow",
    "ERROR":    "red",
    "CRITICAL": "bold_red",
}

# ── Secondary colors (for other fields) ──
SECONDARY_LOG_COLORS = {
    "message": {
        "DEBUG":    "white",
        "INFO":     "white",
        "WARNING":  "yellow",
        "ERROR":    "red",
        "CRITICAL": "bold_red",
    }
}


# ============================================================
#   SETUP LOGGER
# ============================================================

def setup_logger() -> None:
    """
    Initialize the logging system for StudyBuddyV3BOT.

    Sets up:
    - Colored console handler (stdout)
    - Rotating file handler (logs/studybuddy.log)
    - Log level from settings
    - Suppresses noisy third-party loggers

    Called once at startup in main.py before anything else.
    """
    # ── Get log level from settings ──
    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    # ── Create logs directory if needed ──
    log_file_path = settings.log_file_path
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Get root logger ──
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # ── Clear any existing handlers ──
    root_logger.handlers.clear()

    # ── Add console handler ──
    console_handler = _build_console_handler(log_level)
    root_logger.addHandler(console_handler)

    # ── Add file handler ──
    file_handler = _build_file_handler(log_file_path, log_level)
    root_logger.addHandler(file_handler)

    # ── Suppress noisy third-party loggers ──
    _suppress_noisy_loggers()

    # ── Log startup message ──
    startup_logger = logging.getLogger("studybuddy.startup")
    startup_logger.info(
        f"📝 Logging initialized | "
        f"Level: {settings.LOG_LEVEL} | "
        f"File: {log_file_path}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger instance.

    Prefixes the name with 'studybuddy.' for clean
    namespace separation in log output.

    Args:
        name: Module name (use __name__)

    Returns:
        Configured Logger instance

    Usage:
        logger = get_logger(__name__)
        logger.info("Handler initialized")
    """
    # Clean up the module name for display
    # e.g. "handlers.start" → "studybuddy.handlers.start"
    if name == "__main__":
        logger_name = "studybuddy.main"
    elif name.startswith("studybuddy."):
        logger_name = name
    else:
        logger_name = f"studybuddy.{name}"

    return logging.getLogger(logger_name)


# ============================================================
#   HANDLER BUILDERS
# ============================================================

def _build_console_handler(
    log_level: int,
) -> logging.StreamHandler:
    """
    Build a colored console (stdout) log handler.

    Args:
        log_level: Logging level integer

    Returns:
        Configured StreamHandler with color formatting
    """
    handler = colorlog.StreamHandler(stream=sys.stdout)
    handler.setLevel(log_level)

    formatter = colorlog.ColoredFormatter(
        fmt=                  CONSOLE_FORMAT,
        datefmt=              DATE_FORMAT,
        log_colors=           LOG_COLORS,
        secondary_log_colors= SECONDARY_LOG_COLORS,
        reset=                True,
        style=                "%",
    )

    handler.setFormatter(formatter)
    return handler


def _build_file_handler(
    log_file_path: Path,
    log_level:     int,
) -> logging.handlers.RotatingFileHandler:
    """
    Build a rotating file log handler.

    Rotates when file reaches LOG_MAX_SIZE_MB.
    Keeps LOG_BACKUP_COUNT backup files.

    Args:
        log_file_path: Path to log file
        log_level:     Logging level integer

    Returns:
        Configured RotatingFileHandler
    """
    handler = logging.handlers.RotatingFileHandler(
        filename=    str(log_file_path),
        maxBytes=    settings.log_max_bytes,
        backupCount= settings.LOG_BACKUP_COUNT,
        encoding=    "utf-8",
    )
    handler.setLevel(log_level)

    formatter = logging.Formatter(
        fmt=     FILE_FORMAT,
        datefmt= DATE_FORMAT,
        style=   "%",
    )

    handler.setFormatter(formatter)
    return handler


# ============================================================
#   SUPPRESS NOISY LOGGERS
# ============================================================

def _suppress_noisy_loggers() -> None:
    """
    Suppress overly verbose third-party library loggers.
    Sets them to WARNING level to reduce log noise.
    """
    noisy_loggers = [
        # Telegram
        "telegram",
        "telegram.ext",
        "telegram.bot",
        "httpx",
        "httpcore",

        # MongoDB
        "motor",
        "pymongo",

        # OpenAI
        "openai",
        "openai._base_client",

        # HTTP
        "aiohttp",
        "aiohttp.access",
        "urllib3",
        "urllib3.connectionpool",

        # Other
        "asyncio",
        "charset_normalizer",
    ]

    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


# ============================================================
#   LOG READER UTILITY
#   Used by admin panel to display recent logs
# ============================================================

def read_recent_logs(
    num_lines: int = 50,
    level_filter: str = "",
) -> str:
    """
    Read recent log entries from the log file.
    Used by the admin panel log viewer.

    Args:
        num_lines:    Number of recent lines to read
        level_filter: Optional level to filter by
                      ("ERROR", "WARNING", "INFO", etc.)

    Returns:
        String of recent log lines joined by newlines
    """
    try:
        log_file = settings.log_file_path

        if not log_file.exists():
            return "No log file found."

        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Filter by level if specified
        if level_filter:
            lines = [
                line for line in lines
                if f"[{level_filter}" in line or
                   f"[{level_filter.ljust(8)}]" in line
            ]

        # Get last N lines
        recent = lines[-num_lines:] if len(lines) > num_lines else lines

        if not recent:
            return "No log entries found."

        return "".join(recent)

    except PermissionError:
        return "Permission denied reading log file."
    except Exception as e:
        return f"Error reading logs: {e}"


def get_log_file_size() -> str:
    """
    Get the current log file size in human-readable form.

    Returns:
        File size string (e.g. "2.3 MB")
    """
    try:
        log_file = settings.log_file_path
        if not log_file.exists():
            return "0 B"

        size_bytes = log_file.stat().st_size

        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 ** 2):.1f} MB"

    except Exception:
        return "Unknown"


def clear_log_file() -> bool:
    """
    Clear the log file contents.
    Used by admin panel maintenance.

    Returns:
        True if cleared successfully
    """
    try:
        log_file = settings.log_file_path
        if log_file.exists():
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("")
            return True
        return False
    except Exception:
        return False