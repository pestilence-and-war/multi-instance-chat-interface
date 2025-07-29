# my_tools/evaluate_expression.py

import math
import json
import traceback


ALLOWED_GLOBALS = {
    "math": math,
    "abs": abs,
    # You could add other safe built-ins if needed, e.g. 'min', 'max'
    # "__builtins__": {} # More restrictive: Disallows ALL built-ins unless explicitly added back
    "__builtins__": {"True": True, "False": False, "None": None} # Even more restrictive
}
# Generally keep locals empty unless you have a specific, safe reason.
ALLOWED_LOCALS = {}

def evaluate_expression(expression: str) -> str:
    """
    Evaluates a Python mathematical expression string using eval().

    Supports standard Python operators (+, -, *, /, **, %) and functions/constants
    available through the 'math' module (e.g., math.sqrt, math.sin, math.pi).

    @param expression (string): The mathematical expression to evaluate, using Python syntax (e.g., "math.sqrt(16) + 5", "(2+3)*math.pi", "2**8"). Required.
    """
    print(f"--- Tool: evaluate_expression called ---")
    print(f"Expression: {expression}")
    print(f"WARNING: Executing using potentially dangerous eval().") # Add runtime warning

    if not isinstance(expression, str) or not expression.strip():
        return json.dumps({"error": "Invalid or empty expression string provided.", "status": "error_invalid_input"})

    try:
        # *** EXECUTION USING EVAL() ***
        # Pass the restricted global and local dictionaries.
        result = eval(expression, ALLOWED_GLOBALS, ALLOWED_LOCALS)

        # --- Format result nicely (optional) ---
        formatted_result = result
        if isinstance(result, float):
            if result.is_integer():
                # Prevent potential overflow turning large floats back to int
                try:
                    formatted_result = int(result)
                except OverflowError:
                    formatted_result = result # Keep as float if too large for int
            elif math.isnan(result):
                formatted_result = "NaN" # JSON doesn't support NaN directly
            elif math.isinf(result):
                formatted_result = "Infinity" if result > 0 else "-Infinity" # JSON doesn't support Infinity

        # Handle other non-JSON serializable types if necessary (though unlikely for math)

        print(f"Success: Expression Result: {result}") # Log original result
        return json.dumps({
            "expression": expression,
            "result": formatted_result, # Return JSON-friendly result
            "status": "success"
        })

    # --- Error Handling ---
    except NameError as ne:
        # Trying to use disallowed names/functions
        print(f"Error evaluating expression: NameError - {ne}")
        return json.dumps({
            "expression": expression,
            "error": f"Error: Disallowed name or function used: {ne}. Only functions/constants explicitly allowed (like 'math.*', 'abs()') are permitted.",
            "status": "error_disallowed_name"
        })
    except SyntaxError as se:
        print(f"Error evaluating expression: SyntaxError - {se}")
        return json.dumps({
            "expression": expression,
            "error": f"Invalid expression syntax: {se}",
            "status": "error_syntax"
        })
    except ZeroDivisionError as zde:
         print(f"Error evaluating expression: ZeroDivisionError - {zde}")
         return json.dumps({
            "expression": expression,
            "error": f"Error: Division by zero.",
            "status": "error_division_by_zero"
        })
    except (ValueError, OverflowError) as math_err:
         # Catch math domain errors (ValueError) or overflow errors
        print(f"Error evaluating expression: {type(math_err).__name__} - {math_err}")
        return json.dumps({
            "expression": expression,
            "error": f"Mathematical error: {math_err}",
            "status": "error_math"
        })
    except Exception as e:
        # Catch any other unexpected errors during evaluation
        print(f"Error evaluating expression: {type(e).__name__} - {e}")
        # Uncomment for full traceback in server logs during debugging
        # print(traceback.format_exc())
        return json.dumps({
            "expression": expression,
            "error": f"An unexpected error occurred during evaluation: {e}",
            "status": "error_evaluation"
        })

# --- Example Test Cases ---
if __name__ == '__main__':
    print("--- Testing evaluate_expression ---")

    # Standard cases
    print(evaluate_expression("1 + 2"))
    print(evaluate_expression("100 - 55"))
    print(evaluate_expression("25 / 4"))
    print(evaluate_expression("5 * (3 + 1)"))
    print(evaluate_expression("2 ** 10"))
    print(evaluate_expression("17 % 5"))
    print(evaluate_expression("abs(-10)")) # Using allowed built-in

    # Math module cases
    print(evaluate_expression("math.sqrt(16) + 5"))
    print(evaluate_expression("(2 + 3) * math.pi"))
    print(evaluate_expression("math.sin(math.pi / 2)"))
    print(evaluate_expression("math.log(math.e)"))
    print(evaluate_expression("math.factorial(6)"))
    print(evaluate_expression("math.pow(2, 8)"))
    print(evaluate_expression("math.gcd(54, 24)"))
    print(evaluate_expression("math.sqrt(2)")) # Float result
    print(evaluate_expression("math.inf")) # Infinity
    print(evaluate_expression("math.nan")) # NaN

    print("\n--- Error Cases ---")
    print(evaluate_expression("sqrt(16)")) # NameError (needs math.sqrt)
    print(evaluate_expression("pi"))       # NameError (needs math.pi)
    # Security tests (should fail if environment is restricted)
    # Using restrictive __builtins__ should block these:
    print(evaluate_expression("print('hello')")) # NameError: name 'print' is not defined
    print(evaluate_expression("eval('1+1')"))    # NameError: name 'eval' is not defined
    # These might work if __builtins__ is less restricted, demonstrating the danger:
    # print(evaluate_expression("__import__('os').system('echo DANGEROUS')"))
    # print(evaluate_expression("open('test.txt', 'w').write('dangerous')"))

    # Math/Syntax errors
    print(evaluate_expression("math.sqrt(-1)")) # ValueError (math domain)
    print(evaluate_expression("(2 + 3"))       # SyntaxError
    print(evaluate_expression("10 / 0"))       # ZeroDivisionError
    print(evaluate_expression("math.factorial(-5)")) # ValueError (math domain)
    print(evaluate_expression("math.exp(1000)")) # OverflowError
    print(evaluate_expression("")) # Empty string error
    print(evaluate_expression("1 +")) # SyntaxError
    print(evaluate_expression("math.nonexistent(5)")) # AttributeError (caught by general Exception) -> NameError 'math.nonexistent'
    print(evaluate_expression("import os")) # SyntaxError (import not allowed in eval by default)