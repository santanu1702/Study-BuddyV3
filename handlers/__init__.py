# ============================================================
#         StudyBuddyV3BOT — Handlers Package Init
#         Exposes all handler classes at package level
#         for clean imports in main.py
# ============================================================

from handlers.start       import StartHandler
from handlers.ai_assistant import AIAssistantHandler
from handlers.calculator  import CalculatorHandler
from handlers.translator  import TranslatorHandler
from handlers.notes       import NotesHandler
from handlers.language    import LanguageHandler
from handlers.admin       import AdminHandler

__all__ = [
    # ── Core Handlers ──
    "StartHandler",         # /start, /help, /menu, /cancel + main menu
    "AIAssistantHandler",   # AI study assistant + context memory
    "CalculatorHandler",    # Inline button calculator
    "TranslatorHandler",    # Text translation tool
    "NotesHandler",         # Save / view / delete notes
    "LanguageHandler",      # Language detection + manual switch
    "AdminHandler",         # Full admin panel (inline button UI)
]