# ============================================================
#         StudyBuddyV3BOT — AI Service
#         OpenAI GPT-4o-mini wrapper with context memory
#         Async, production-ready, error-handled
# ============================================================

import asyncio
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config.settings import settings
from config.constants import Collections, LimitConstants, TimeConstants
from database.connection import db_manager
from database.models import AIContextModel, AIContextMessage, utcnow_naive
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
#   SYSTEM PROMPT
#   Educational focus — defines AI behavior
# ============================================================

SYSTEM_PROMPT = """You are StudyBuddy, an expert AI study assistant.

Your role:
- Help students understand academic concepts clearly
- Provide accurate, educational explanations
- Break down complex topics into simple steps
- Give examples to illustrate concepts
- Encourage learning and curiosity
- Support all academic subjects (Math, Science, History, Literature, etc.)

Guidelines:
- Always be encouraging and supportive
- Use clear, simple language appropriate for students
- Provide step-by-step explanations when solving problems
- If asked about non-educational topics, gently redirect to study topics
- Format responses clearly with proper structure
- Keep responses concise but complete
- Use examples and analogies to explain difficult concepts

Remember: You are a study assistant, not a general chatbot.
Focus on helping students learn and understand."""


# ============================================================
#   AI SERVICE
# ============================================================

class AIService:
    """
    OpenAI GPT-4o-mini service with per-user context memory.

    Features:
    - Async OpenAI API calls
    - Per-user conversation history stored in MongoDB
    - Sliding window context (max 20 messages)
    - Auto-expiring context (TTL index)
    - Retry logic with exponential backoff
    - Token usage tracking
    - Educational system prompt
    """

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key= settings.openai_api_key,
        )

    # ================================================================
    #   MAIN RESPONSE METHOD
    # ================================================================

    async def get_response(
        self,
        user_id:  int,
        question: str,
        language: str = "en",
    ) -> Tuple[str, Optional[Dict[str, int]]]:
        """
        Get an AI response for a user's question.
        Loads conversation context, calls OpenAI, saves response.

        Args:
            user_id:  Telegram user ID
            question: User's question text
            language: User's language code for response language

        Returns:
            Tuple of (response_text, usage_dict)
            usage_dict: {prompt_tokens, completion_tokens, total_tokens}
        """
        try:
            # ── Load conversation context ──
            context = await self._load_context(user_id)

            # ── Build language instruction ──
            lang_instruction = self._get_language_instruction(language)

            # ── Build system prompt ──
            system_content = f"{SYSTEM_PROMPT}\n\n{lang_instruction}"

            # ── Add user message to context ──
            context.add_message(
                role=         "user",
                content=      question,
                max_messages= settings.AI_CONTEXT_MAX_MESSAGES,
            )

            # ── Build messages for API ──
            messages = [
                {"role": "system", "content": system_content},
                *context.get_openai_messages(),
            ]

            # ── Call OpenAI API ──
            response = await self._call_openai(messages)

            # ── Extract response text ──
            response_text = (
                response.choices[0].message.content or
                "I couldn't generate a response. Please try again."
            )

            # ── Extract usage stats ──
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens":     response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens":      response.usage.total_tokens,
                }

                # Update context token tracking
                context.total_tokens_used += response.usage.total_tokens
                context.total_requests    += 1

            # ── Add AI response to context ──
            context.add_message(
                role=         "assistant",
                content=      response_text,
                max_messages= settings.AI_CONTEXT_MAX_MESSAGES,
            )

            # ── Save updated context ──
            await self._save_context(user_id, context)

            logger.info(
                f"🤖 AI response | "
                f"User: {user_id} | "
                f"Tokens: {usage['total_tokens'] if usage else 0} | "
                f"Context: {context.message_count} msgs"
            )

            return response_text, usage

        except Exception as e:
            logger.error(
                f"AI service error for user {user_id}: {e}",
                exc_info=True,
            )
            raise

    # ================================================================
    #   OPENAI API CALL
    # ================================================================

    @retry(
        stop=               stop_after_attempt(3),
        wait=               wait_exponential(multiplier=1, min=2, max=10),
        retry=              retry_if_exception_type(Exception),
        reraise=            True,
    )
    async def _call_openai(
        self,
        messages: List[Dict[str, str]],
    ) -> ChatCompletion:
        """
        Call OpenAI Chat Completions API with retry logic.
        Retries up to 3 times with exponential backoff.

        Args:
            messages: List of message dicts for the API

        Returns:
            ChatCompletion response object
        """
        return await self._client.chat.completions.create(
            model=       settings.OPENAI_MODEL,
            messages=    messages,
            max_tokens=  settings.OPENAI_MAX_TOKENS,
            temperature= settings.OPENAI_TEMPERATURE,
        )

    # ================================================================
    #   CONTEXT MANAGEMENT
    # ================================================================

    async def _load_context(self, user_id: int) -> AIContextModel:
        """
        Load conversation context for a user from MongoDB.
        Returns empty context if none exists.

        Args:
            user_id: Telegram user ID

        Returns:
            AIContextModel with conversation history
        """
        try:
            collection = db_manager.get_collection(Collections.AI_CONTEXT)
            doc        = await collection.find_one({"user_id": user_id})

            if doc:
                context = AIContextModel.from_dict(doc)
                logger.debug(
                    f"Loaded AI context | "
                    f"User: {user_id} | "
                    f"Messages: {context.message_count}"
                )
                return context

            # Return fresh empty context
            return AIContextModel(user_id=user_id)

        except Exception as e:
            logger.error(
                f"Error loading AI context for {user_id}: {e}"
            )
            return AIContextModel(user_id=user_id)

    async def _save_context(
        self,
        user_id: int,
        context: AIContextModel,
    ) -> None:
        """
        Save or update conversation context in MongoDB.
        Uses upsert — creates or updates in one operation.

        Args:
            user_id: Telegram user ID
            context: Updated AIContextModel to save
        """
        try:
            collection = db_manager.get_collection(Collections.AI_CONTEXT)

            # Update the timestamp for TTL index
            context.updated_at = utcnow_naive()

            await collection.update_one(
                {"user_id": user_id},
                {"$set": context.to_dict()},
                upsert=True,
            )

        except Exception as e:
            logger.error(
                f"Error saving AI context for {user_id}: {e}"
            )

    async def clear_context(self, user_id: int) -> bool:
        """
        Clear conversation context for a user.
        Deletes the context document from MongoDB.

        Args:
            user_id: Telegram user ID

        Returns:
            True if context was cleared, False if none existed
        """
        try:
            collection = db_manager.get_collection(Collections.AI_CONTEXT)
            result     = await collection.delete_one({"user_id": user_id})

            if result.deleted_count > 0:
                logger.info(
                    f"🗑️ AI context cleared | User: {user_id}"
                )
                return True

            return False

        except Exception as e:
            logger.error(
                f"Error clearing AI context for {user_id}: {e}"
            )
            return False

    async def get_context_info(self, user_id: int) -> Dict[str, Any]:
        """
        Get context statistics for a user.
        Used for admin monitoring or user info display.

        Args:
            user_id: Telegram user ID

        Returns:
            Dict with context stats
        """
        try:
            context = await self._load_context(user_id)
            return {
                "user_id":           user_id,
                "message_count":     context.message_count,
                "total_tokens":      context.total_tokens_used,
                "total_requests":    context.total_requests,
                "last_updated":      context.updated_at,
                "has_context":       context.message_count > 0,
            }
        except Exception as e:
            logger.error(
                f"Error getting context info for {user_id}: {e}"
            )
            return {
                "user_id":        user_id,
                "message_count":  0,
                "total_tokens":   0,
                "total_requests": 0,
                "last_updated":   None,
                "has_context":    False,
            }

    # ================================================================
    #   LANGUAGE INSTRUCTION
    # ================================================================

    def _get_language_instruction(self, lang_code: str) -> str:
        """
        Build language instruction for the system prompt.
        Tells the AI to respond in the user's language.

        Args:
            lang_code: Language code (en, hi, bn, ar)

        Returns:
            Language instruction string
        """
        instructions = {
            "en": "Please respond in English.",
            "hi": "कृपया हिंदी में उत्तर दें। (Please respond in Hindi)",
            "bn": "অনুগ্রহ করে বাংলায় উত্তর দিন। (Please respond in Bengali)",
            "ar": "يرجى الرد باللغة العربية. (Please respond in Arabic)",
        }
        return instructions.get(lang_code, instructions["en"])

    # ================================================================
    #   QUICK ANSWER (No context)
    # ================================================================

    async def get_quick_answer(
        self,
        question: str,
        language: str = "en",
    ) -> str:
        """
        Get a quick AI answer without conversation context.
        Used for one-off questions that don't need memory.

        Args:
            question: Question text
            language: Response language code

        Returns:
            AI response text
        """
        try:
            lang_instruction = self._get_language_instruction(language)
            messages = [
                {
                    "role":    "system",
                    "content": f"{SYSTEM_PROMPT}\n\n{lang_instruction}",
                },
                {
                    "role":    "user",
                    "content": question,
                },
            ]

            response = await self._call_openai(messages)
            return (
                response.choices[0].message.content or
                "Could not generate a response."
            )

        except Exception as e:
            logger.error(f"Quick answer error: {e}")
            raise