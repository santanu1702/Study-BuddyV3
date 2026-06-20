# ============================================================
#         StudyBuddyV3BOT — Services Package Init
#         Exposes all service classes at package level
#         for clean imports across the project
# ============================================================

from services.ai_service          import AIService
from services.translation_service import TranslationService
from services.calculator_service  import CalculatorService
from services.broadcast_service   import BroadcastService
from services.rate_limiter        import RateLimiter

__all__ = [
    # ── Service Classes ──
    "AIService",            # OpenAI GPT wrapper + context memory
    "TranslationService",   # deep-translator Google Translate wrapper
    "CalculatorService",    # Safe math expression evaluator
    "BroadcastService",     # Admin broadcast message sender
    "RateLimiter",          # Per-user AI request rate limiter
]