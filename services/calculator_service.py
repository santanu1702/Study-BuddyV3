# ============================================================
#         StudyBuddyV3BOT — Calculator Service
#         Safe mathematical expression evaluator
#         Uses simpleeval — no dangerous eval()
# ============================================================

import math
from typing import Tuple, Optional, Union

from simpleeval import SimpleEval, EvalWithCompoundTypes, InvalidExpression
from config.constants import LimitConstants
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
#   SAFE MATH FUNCTIONS
#   Whitelisted functions available in calculator
# ============================================================

SAFE_FUNCTIONS = {
    # ── Trigonometry ──
    "sin":   math.sin,
    "cos":   math.cos,
    "tan":   math.tan,
    "asin":  math.asin,
    "acos":  math.acos,
    "atan":  math.atan,
    "atan2": math.atan2,

    # ── Logarithms ──
    "log":   math.log,
    "log10": math.log10,
    "log2":  math.log2,
    "ln":    math.log,      # Alias for natural log

    # ── Powers & Roots ──
    "sqrt":  math.sqrt,
    "pow":   math.pow,
    "exp":   math.exp,
    "cbrt":  lambda x: x ** (1/3),  # Cube root

    # ── Rounding ──
    "floor": math.floor,
    "ceil":  math.ceil,
    "round": round,
    "abs":   abs,
    "fabs":  math.fabs,

    # ── Combinatorics ──
    "factorial": math.factorial,
    "gcd":       math.gcd,

    # ── Hyperbolic ──
    "sinh":  math.sinh,
    "cosh":  math.cosh,
    "tanh":  math.tanh,

    # ── Conversion ──
    "degrees": math.degrees,
    "radians": math.radians,
}

# ── Safe Constants ──
SAFE_NAMES = {
    "pi":  math.pi,
    "e":   math.e,
    "tau": math.tau,
    "inf": math.inf,
    "PI":  math.pi,
    "E":   math.e,
}


# ============================================================
#   CALCULATOR SERVICE
# ============================================================

class CalculatorService:
    """
    Safe mathematical expression evaluator.

    Uses simpleeval library — completely safe,
    no access to Python builtins or dangerous functions.

    Supported operations:
    - Basic: +, -, *, /, //, %, **
    - Trigonometry: sin, cos, tan, asin, acos, atan
    - Logarithms: log, log10, log2, ln
    - Powers: sqrt, pow, exp, cbrt
    - Rounding: floor, ceil, round, abs
    - Constants: pi, e, tau
    - Combinatorics: factorial, gcd
    - Hyperbolic: sinh, cosh, tanh
    - Conversion: degrees, radians
    """

    def __init__(self) -> None:
        self._evaluator = self._build_evaluator()

    def _build_evaluator(self) -> SimpleEval:
        """
        Build and configure the safe evaluator.
        Whitelists only safe math functions and constants.
        """
        evaluator          = SimpleEval()
        evaluator.functions = SAFE_FUNCTIONS
        evaluator.names     = SAFE_NAMES
        return evaluator

    # ================================================================
    #   MAIN EVALUATE METHOD
    # ================================================================

    def evaluate(
        self,
        expression: str,
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Safely evaluate a mathematical expression.

        Args:
            expression: Math expression string
                        e.g. "2 + 2", "sqrt(16)", "sin(pi/2)"

        Returns:
            Tuple of (result, error_message)
            - On success: (float_result, None)
            - On failure: (None, error_string)

        Usage:
            result, error = calc_service.evaluate("2 + 2")
            if error:
                print(f"Error: {error}")
            else:
                print(f"Result: {result}")
        """
        if not expression or not expression.strip():
            return None, "Empty expression"

        # ── Validate length ──
        if len(expression) > LimitConstants.MAX_CALC_EXPRESSION_LEN:
            return None, "Expression too long"

        # ── Pre-process expression ──
        processed = self._preprocess(expression)

        try:
            # ── Evaluate safely ──
            result = self._evaluator.eval(processed)

            # ── Validate result ──
            if result is None:
                return None, "No result"

            # Convert to float for consistency
            result = float(result)

            # ── Check for overflow ──
            if abs(result) > LimitConstants.MAX_CALC_RESULT_VALUE:
                return None, "Result too large"

            # ── Check for NaN ──
            if math.isnan(result):
                return None, "Result is not a number"

            # ── Check for infinity ──
            if math.isinf(result):
                return None, "Result is infinity"

            logger.debug(
                f"Calc evaluated | "
                f"Expr: {expression!r} | "
                f"Result: {result}"
            )

            return result, None

        except ZeroDivisionError:
            return None, "Division by zero"

        except InvalidExpression as e:
            return None, f"Invalid expression: {str(e)[:50]}"

        except ValueError as e:
            error_msg = str(e)
            if "math domain" in error_msg:
                return None, "Math domain error (e.g. sqrt of negative)"
            if "factorial" in error_msg:
                return None, "Factorial requires non-negative integer"
            return None, f"Value error: {error_msg[:50]}"

        except OverflowError:
            return None, "Result overflow — number too large"

        except Exception as e:
            logger.warning(
                f"Calculator error for expr {expression!r}: {e}"
            )
            return None, "Calculation error"

    # ================================================================
    #   PREPROCESSING
    # ================================================================

    def _preprocess(self, expression: str) -> str:
        """
        Pre-process expression before evaluation.
        Handles common user input patterns and fixes syntax.

        Transformations:
        - Strip whitespace
        - Replace × with *
        - Replace ÷ with /
        - Replace ^ with **
        - Replace π with pi
        - Handle implicit multiplication (2π → 2*pi)
        - Normalize log10/ln notation

        Args:
            expression: Raw expression string

        Returns:
            Processed expression ready for evaluation
        """
        expr = expression.strip()

        # ── Symbol replacements ──
        replacements = {
            "×":  "*",
            "÷":  "/",
            "^":  "**",
            "π":  "pi",
            "√":  "sqrt",
            "∞":  "inf",

            # Common text variations
            "Log":  "log10",
            "LOG":  "log10",
            "Ln":   "log",
            "LN":   "log",
            "Sin":  "sin",
            "SIN":  "sin",
            "Cos":  "cos",
            "COS":  "cos",
            "Tan":  "tan",
            "TAN":  "tan",
            "Sqrt": "sqrt",
            "SQRT": "sqrt",
            "Abs":  "abs",
            "ABS":  "abs",
        }

        for old, new in replacements.items():
            expr = expr.replace(old, new)

        # ── Fix implicit multiplication ──
        # e.g. "2pi" → "2*pi", "2e" → "2*e", "2sqrt" → "2*sqrt"
        import re

        # Number followed by function/constant
        expr = re.sub(r"(\d)(pi|e|tau|sqrt|sin|cos|tan|log|abs)", r"\1*\2", expr)

        # Closing bracket followed by number or opening bracket
        expr = re.sub(r"\)(\d)", r")*\1", expr)
        expr = re.sub(r"\)\(", r")*(", expr)

        # Number followed by opening bracket
        expr = re.sub(r"(\d)\(", r"\1*(", expr)

        return expr

    # ================================================================
    #   VALIDATION
    # ================================================================

    def validate_expression(self, expression: str) -> Tuple[bool, str]:
        """
        Validate an expression without evaluating it.
        Checks syntax and safety.

        Args:
            expression: Expression to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not expression or not expression.strip():
            return False, "Empty expression"

        if len(expression) > LimitConstants.MAX_CALC_EXPRESSION_LEN:
            return False, f"Expression too long (max {LimitConstants.MAX_CALC_EXPRESSION_LEN} chars)"

        # ── Check for balanced brackets ──
        open_count  = expression.count("(")
        close_count = expression.count(")")
        if open_count != close_count:
            return False, "Unbalanced parentheses"

        # ── Check for dangerous patterns ──
        dangerous = [
            "__", "import", "exec", "eval",
            "open", "os.", "sys.", "subprocess",
            "globals", "locals", "builtins",
        ]
        expr_lower = expression.lower()
        for pattern in dangerous:
            if pattern in expr_lower:
                return False, f"Unsafe pattern detected: {pattern}"

        return True, ""

    # ================================================================
    #   UTILITY METHODS
    # ================================================================

    def format_result(self, result: float) -> str:
        """
        Format a calculation result for display.

        Rules:
        - Integers shown without decimal point
        - Floats shown with up to 10 significant digits
        - Very large/small numbers in scientific notation

        Args:
            result: Float result to format

        Returns:
            Formatted string
        """
        if result is None:
            return "Error"

        try:
            # Integer result
            if isinstance(result, float) and result.is_integer():
                int_result = int(result)
                if abs(int_result) > 1e15:
                    return f"{result:.6e}"
                return str(int_result)

            # Scientific notation for very large/small
            if abs(result) > 1e12 or (
                abs(result) < 1e-6 and result != 0
            ):
                return f"{result:.6e}"

            # Normal float — up to 10 significant digits
            formatted = f"{result:.10g}"
            return formatted

        except Exception:
            return str(result)

    def get_available_functions(self) -> list:
        """
        Return list of all available calculator functions.
        Used for help text or documentation.

        Returns:
            Sorted list of function names
        """
        return sorted(SAFE_FUNCTIONS.keys())

    def get_available_constants(self) -> dict:
        """
        Return dict of available constants and their values.

        Returns:
            Dict of {name: value}
        """
        return {
            k: v for k, v in SAFE_NAMES.items()
            if not k.isupper()  # Skip uppercase duplicates
        }