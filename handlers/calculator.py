# ============================================================
#         StudyBuddyV3BOT — Calculator Handler
#         Inline button-based calculator
#         Safe expression evaluation — no eval()
# ============================================================

from telegram import Update
from telegram.ext import ContextTypes

from config.constants import BotState, EmojiConstants
from keyboards.calculator_kb import CalculatorKeyboard
from services.calculator_service import CalculatorService
from utils.logger import get_logger
from utils.helpers import edit_or_send, answer_callback

logger = get_logger(__name__)

# Max display length for calculator expression
MAX_DISPLAY_LENGTH = 20


# ============================================================
#   CALCULATOR HANDLER
# ============================================================

class CalculatorHandler:
    """
    Handles the inline button calculator feature.

    Features:
    - Full inline keyboard UI (no typing needed)
    - Safe expression evaluation via simpleeval
    - Supports basic + advanced math operations
    - Real-time display updates
    - Error handling for invalid expressions
    - History of last result
    """

    def __init__(self) -> None:
        self.calc_service = CalculatorService()

    # ================================================================
    #   CALLBACK ROUTER
    # ================================================================

    async def handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Route all calc: callback queries.
        Pattern: calc:action:value

        Actions:
        - open:      Open calculator
        - digit:     Number/operator button pressed
        - op:        Operation (sin, cos, sqrt, etc.)
        - equals:    Calculate result
        - clear:     Clear display (C)
        - clear_all: Clear everything (AC)
        - backspace: Delete last character
        - decimal:   Add decimal point
        - sign:      Toggle positive/negative
        - back:      Return to main menu
        """
        query   = update.callback_query
        user_id = update.effective_user.id
        await query.answer()

        parts  = query.data.split(":")
        action = parts[1] if len(parts) > 1 else ""
        value  = parts[2] if len(parts) > 2 else ""

        logger.debug(
            f"Calc callback | User: {user_id} | "
            f"Action: {action} | Value: {value}"
        )

        # Initialize calculator state if needed
        if "calc_expr"   not in context.user_data:
            context.user_data["calc_expr"]    = ""
        if "calc_result" not in context.user_data:
            context.user_data["calc_result"]  = ""
        if "calc_fresh"  not in context.user_data:
            context.user_data["calc_fresh"]   = False

        # ── Route action ──
        if action == "open":
            await self._open_calculator(update, context)
        elif action == "digit":
            await self._handle_digit(update, context, value)
        elif action == "op":
            await self._handle_operator(update, context, value)
        elif action == "equals":
            await self._calculate(update, context)
        elif action == "clear":
            await self._clear(update, context)
        elif action == "clear_all":
            await self._clear_all(update, context)
        elif action == "backspace":
            await self._backspace(update, context)
        elif action == "decimal":
            await self._add_decimal(update, context)
        elif action == "sign":
            await self._toggle_sign(update, context)
        elif action == "back":
            await self._close_calculator(update, context)
        elif action == "noop":
            pass  # Decorative button — do nothing
        else:
            await self._open_calculator(update, context)

    # ================================================================
    #   OPEN / CLOSE
    # ================================================================

    async def _open_calculator(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Open the calculator with a fresh state."""
        # Reset calculator state
        context.user_data["calc_expr"]   = ""
        context.user_data["calc_result"] = ""
        context.user_data["calc_fresh"]  = False

        await self._render(update, context)
        logger.info(
            f"🧮 Calculator opened by user "
            f"{update.effective_user.id}"
        )

    async def _close_calculator(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Close calculator and return to main menu."""
        # Clear state
        context.user_data.pop("calc_expr",   None)
        context.user_data.pop("calc_result", None)
        context.user_data.pop("calc_fresh",  None)

        from keyboards.main_menu import MainMenuKeyboard
        text = (
            f"{EmojiConstants.CALCULATOR} Calculator closed.\n\n"
            f"_Returning to main menu..._"
        )
        keyboard = MainMenuKeyboard.main_menu()
        await edit_or_send(update, context, text, keyboard)

    # ================================================================
    #   INPUT HANDLERS
    # ================================================================

    async def _handle_digit(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        digit: str,
    ) -> None:
        """
        Handle a digit or basic operator button press.
        Digits: 0-9
        Operators: +, -, *, /, (, ), %
        """
        expr  = context.user_data.get("calc_expr", "")
        fresh = context.user_data.get("calc_fresh", False)

        # If last action was = and user types a digit, start fresh
        if fresh and digit.isdigit():
            expr  = ""
            fresh = False

        # If last action was = and user types operator, continue with result
        if fresh and digit in "+-*/":
            result = context.user_data.get("calc_result", "")
            expr   = result
            fresh  = False

        # Prevent expression from getting too long
        if len(expr) >= MAX_DISPLAY_LENGTH:
            await answer_callback(
                update.callback_query,
                text="Expression too long!",
                show_alert=False,
            )
            return

        # Prevent double operators
        if digit in "+-*/" and expr and expr[-1] in "+-*/":
            expr = expr[:-1]

        # Prevent leading operators (except minus for negative)
        if not expr and digit in "+*/(":
            return

        expr += digit
        context.user_data["calc_expr"]  = expr
        context.user_data["calc_fresh"] = False

        await self._render(update, context)

    async def _handle_operator(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        operator: str,
    ) -> None:
        """
        Handle advanced operator buttons.
        Operators: sqrt, sq, pi, e, sin, cos, tan, log, ln, inv, pow
        """
        expr  = context.user_data.get("calc_expr", "")
        fresh = context.user_data.get("calc_fresh", False)

        # If fresh after result, use result as base
        if fresh:
            result = context.user_data.get("calc_result", "0")
            expr   = result
            fresh  = False

        # Map button labels to expression strings
        op_map = {
            "sqrt":  "sqrt(",
            "sq":    "**2",
            "pi":    "3.14159265",
            "e":     "2.71828182",
            "sin":   "sin(",
            "cos":   "cos(",
            "tan":   "tan(",
            "log":   "log10(",
            "ln":    "log(",
            "inv":   "1/(",
            "pow":   "**",
            "abs":   "abs(",
            "floor": "floor(",
            "ceil":  "ceil(",
            "mod":   "%",
        }

        op_str = op_map.get(operator, "")
        if not op_str:
            return

        # Prevent expression from getting too long
        if len(expr) + len(op_str) > MAX_DISPLAY_LENGTH + 10:
            await answer_callback(
                update.callback_query,
                text="Expression too long!",
                show_alert=False,
            )
            return

        expr += op_str
        context.user_data["calc_expr"]  = expr
        context.user_data["calc_fresh"] = False

        await self._render(update, context)

    async def _add_decimal(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Add a decimal point to the current number."""
        expr  = context.user_data.get("calc_expr", "")
        fresh = context.user_data.get("calc_fresh", False)

        if fresh:
            expr  = "0"
            fresh = False

        if not expr:
            expr = "0"

        # Check if current number already has a decimal
        # Find the last number in the expression
        import re
        last_num = re.split(r"[+\-*/%(]", expr)[-1]
        if "." in last_num:
            return  # Already has decimal

        expr += "."
        context.user_data["calc_expr"]  = expr
        context.user_data["calc_fresh"] = False

        await self._render(update, context)

    async def _toggle_sign(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Toggle positive/negative for the current expression."""
        expr  = context.user_data.get("calc_expr", "")
        fresh = context.user_data.get("calc_fresh", False)

        if fresh:
            result = context.user_data.get("calc_result", "0")
            expr   = result
            fresh  = False

        if not expr:
            expr = "-"
        elif expr.startswith("-"):
            expr = expr[1:]
        else:
            expr = "-" + expr

        context.user_data["calc_expr"]  = expr
        context.user_data["calc_fresh"] = False

        await self._render(update, context)

    # ================================================================
    #   CALCULATE
    # ================================================================

    async def _calculate(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Evaluate the current expression and display result.
        Uses CalculatorService for safe evaluation.
        """
        expr = context.user_data.get("calc_expr", "")

        if not expr:
            await answer_callback(
                update.callback_query,
                text="Nothing to calculate!",
                show_alert=False,
            )
            return

        # Evaluate safely
        result, error = self.calc_service.evaluate(expr)

        if error:
            # Show error briefly then reset
            context.user_data["calc_expr"]   = ""
            context.user_data["calc_result"] = "Error"
            context.user_data["calc_fresh"]  = True

            await answer_callback(
                update.callback_query,
                text=f"⚠️ {error}",
                show_alert=False,
            )
            await self._render(update, context)
            return

        # Store result
        result_str = self._format_result(result)
        context.user_data["calc_result"] = result_str
        context.user_data["calc_expr"]   = result_str
        context.user_data["calc_fresh"]  = True

        logger.debug(
            f"Calc result | User: {update.effective_user.id} | "
            f"Expr: {expr} | Result: {result_str}"
        )

        await self._render(update, context)

    # ================================================================
    #   CLEAR / BACKSPACE
    # ================================================================

    async def _clear(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Clear (C) — clear current entry but keep memory.
        If expression is empty, works like AC.
        """
        expr = context.user_data.get("calc_expr", "")

        if expr:
            context.user_data["calc_expr"]  = ""
            context.user_data["calc_fresh"] = False
        else:
            await self._clear_all(update, context)
            return

        await self._render(update, context)

    async def _clear_all(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """All Clear (AC) — reset everything."""
        context.user_data["calc_expr"]   = ""
        context.user_data["calc_result"] = ""
        context.user_data["calc_fresh"]  = False

        await self._render(update, context)

    async def _backspace(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Delete the last character from the expression."""
        expr  = context.user_data.get("calc_expr", "")
        fresh = context.user_data.get("calc_fresh", False)

        # If fresh after result, backspace clears result
        if fresh:
            context.user_data["calc_expr"]  = ""
            context.user_data["calc_fresh"] = False
            await self._render(update, context)
            return

        if expr:
            # Handle multi-char operators (e.g., "sqrt(")
            multi_char_ops = [
                "sqrt(", "sin(", "cos(", "tan(",
                "log10(", "log(", "abs(", "1/(",
                "floor(", "ceil(",
            ]
            removed = False
            for op in sorted(multi_char_ops, key=len, reverse=True):
                if expr.endswith(op):
                    expr    = expr[:-len(op)]
                    removed = True
                    break

            if not removed:
                expr = expr[:-1]

        context.user_data["calc_expr"]  = expr
        context.user_data["calc_fresh"] = False

        await self._render(update, context)

    # ================================================================
    #   RENDER
    # ================================================================

    async def _render(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Render the calculator display and keyboard.
        Updates the existing message in place.
        """
        expr   = context.user_data.get("calc_expr",   "")
        result = context.user_data.get("calc_result", "")
        fresh  = context.user_data.get("calc_fresh",  False)

        # Build display
        display = self._build_display(expr, result, fresh)

        # Build keyboard
        keyboard = CalculatorKeyboard.calculator(expr)

        try:
            await update.callback_query.edit_message_text(
                text=         display,
                parse_mode=   "Markdown",
                reply_markup= keyboard,
            )
        except Exception as e:
            # Message unchanged — ignore
            if "message is not modified" not in str(e).lower():
                logger.warning(f"Calc render error: {e}")

    def _build_display(
        self,
        expr:   str,
        result: str,
        fresh:  bool,
    ) -> str:
        """
        Build the calculator display text.
        Shows expression on top and result below.
        """
        # Display line — show expression or placeholder
        display_expr = expr if expr else "0"

        # Truncate if too long for display
        if len(display_expr) > MAX_DISPLAY_LENGTH:
            display_expr = "..." + display_expr[-(MAX_DISPLAY_LENGTH - 3):]

        # Result line
        if fresh and result:
            result_line = f"\n`= {result}`"
        else:
            result_line = ""

        return (
            f"{EmojiConstants.CALCULATOR} *Calculator*\n"
            f"{'─' * 30}\n\n"
            f"```\n{display_expr}\n```"
            f"{result_line}\n\n"
            f"_Tap buttons below:_"
        )

    # ================================================================
    #   UTILITIES
    # ================================================================

    def _format_result(self, result: float) -> str:
        """
        Format a calculation result for display.
        - Integers shown without decimal
        - Floats shown with up to 10 significant digits
        - Very large/small numbers in scientific notation
        """
        if result is None:
            return "Error"

        try:
            # Check if result is effectively an integer
            if isinstance(result, float) and result.is_integer():
                int_result = int(result)
                if abs(int_result) > 1e15:
                    return f"{result:.6e}"
                return str(int_result)

            # Float result
            if abs(result) > 1e12 or (abs(result) < 1e-6 and result != 0):
                return f"{result:.6e}"

            # Normal float — strip trailing zeros
            formatted = f"{result:.10g}"
            return formatted

        except Exception:
            return str(result)
