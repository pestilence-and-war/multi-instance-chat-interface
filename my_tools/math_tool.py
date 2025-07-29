# my_tools/math_tool.py

import math
import json
import traceback

# Functions known to REQUIRE two arguments
# We'll check for arg2's presence for these specifically
REQUIRES_TWO_ARGS = {'pow', 'gcd', 'atan2', 'ldexp'} # Add others like fmod, hypot if needed

# Functions known to REQUIRE integer arguments for arg1 (and arg2 if applicable)
REQUIRES_INT_ARGS = {'factorial', 'gcd', 'comb', 'perm'} # isqrt needs positive int

# Note: 'log' is handled specially below

def calculate_math(operation: str, arg1: float | int, arg2: float | int = None) -> str:
    """Performs mathematical calculations using Python's math module functions and constants.

    Handles common functions like sqrt, pow, log (natural and base), trig functions,
    factorial, gcd, as well as constants like pi and e.

    @param operation (string): The name of the math function or constant (e.g., 'sqrt', 'pow', 'log', 'log10', 'sin', 'cos', 'factorial', 'gcd', 'pi', 'e', 'tau'). Case-insensitive. Required.
    @param arg1 (number): The primary numeric argument. Required for functions, ignored for constants.
    @param arg2 (number): The secondary numeric argument (e.g., for 'pow(arg1, arg2)', 'log(arg1, arg2)' [log base arg2], 'gcd(arg1, arg2)'). Optional, used only if the operation requires it.
    """
    print(f"--- Tool: calculate_math called ---")
    print(f"Operation: {operation}, Arg1: {arg1}, Arg2: {arg2}")

    if not isinstance(operation, str) or not operation:
        return json.dumps({"error": "Invalid or empty operation name provided.", "status": "error_invalid_input"})

    operation = operation.lower().strip()

    # Check if the requested operation exists in the math module
    if not hasattr(math, operation):
        return json.dumps({
            "operation": operation,
            "error": f"Unsupported math operation or constant: '{operation}'. Check available math module functions.",
            "status": "error_unsupported_operation"
        })

    try:
        # Get the attribute (function or constant) from the math module
        func_or_const = getattr(math, operation)

        result = None
        args_used = [] # Keep track of arguments actually used in the calculation

        # --- Handle Constants ---
        if not callable(func_or_const):
            result = func_or_const
            if arg1 is not None or arg2 is not None:
                 print(f"Info: Arguments ({arg1=}, {arg2=}) provided for constant '{operation}' are ignored.")
            args_used = [] # Constants don't use arguments

        # --- Handle Functions ---
        else:
            math_func = func_or_const

            # Check for missing primary argument (shouldn't happen with type hints, but good practice)
            if arg1 is None:
                 return json.dumps({
                     "operation": operation,
                     "error": f"Missing required argument 'arg1' for function '{operation}'.",
                     "status": "error_missing_argument"
                 })

            current_arg1 = arg1
            current_arg2 = arg2

            # --- Integer Argument Validation ---
            if operation in REQUIRES_INT_ARGS:
                try:
                    # Validate arg1
                    if not isinstance(current_arg1, int) and (not isinstance(current_arg1, float) or not current_arg1.is_integer()):
                         raise ValueError(f"Argument 'arg1' ({arg1}) must be an integer for '{operation}'.")
                    int_arg1 = int(current_arg1)

                    # Validate arg2 if needed (only gcd in REQUIRES_INT_ARGS and REQUIRES_TWO_ARGS)
                    if operation == 'gcd':
                        if current_arg2 is None:
                             raise TypeError(f"Missing required argument 'arg2' for '{operation}'.")
                        if not isinstance(current_arg2, int) and (not isinstance(current_arg2, float) or not current_arg2.is_integer()):
                             raise ValueError(f"Argument 'arg2' ({arg2}) must be an integer for '{operation}'.")
                        int_arg2 = int(current_arg2)
                        result = math_func(int_arg1, int_arg2)
                        args_used = [int_arg1, int_arg2]
                    else: # factorial, comb, perm etc. (single int arg)
                        if current_arg2 is not None:
                             print(f"Info: Argument 'arg2' ({arg2}) provided but ignored for single-argument function '{operation}'.")
                        result = math_func(int_arg1)
                        args_used = [int_arg1]

                except (ValueError, TypeError) as e: # Catch validation errors
                     return json.dumps({
                         "operation": operation,
                         "arguments": [arg1, arg2],
                         "error": str(e),
                         "status": "error_invalid_argument_type"
                     })

            # --- Specific Function Arity/Logic Handling ---
            elif operation == 'log':
                if current_arg2 is not None: # log(x, base)
                    result = math_func(current_arg1, current_arg2)
                    args_used = [current_arg1, current_arg2]
                else: # log(x) - natural logarithm
                    result = math_func(current_arg1)
                    args_used = [current_arg1]

            elif operation in REQUIRES_TWO_ARGS:
                if current_arg2 is None:
                    return json.dumps({
                        "operation": operation,
                        "arguments": [current_arg1],
                        "error": f"Missing required argument 'arg2' for function '{operation}'.",
                        "status": "error_missing_argument"
                    })
                # We already handled integer checks for 'gcd'
                result = math_func(current_arg1, current_arg2)
                args_used = [current_arg1, current_arg2]

            # --- Default: Assume Single Argument Function ---
            else:
                if current_arg2 is not None:
                    # Check if this function *might* optionally take two args (like `remainder`)
                    # For simplicity now, we'll just warn and use one.
                    # A more complex setup could inspect the signature, but that's usually overkill.
                    print(f"Info: Argument 'arg2' ({arg2}) provided but ignored for assumed single-argument function '{operation}'.")
                try:
                    result = math_func(current_arg1)
                    args_used = [current_arg1]
                except TypeError as te:
                    # If it fails here, it might be an unexpected two-arg function or type mismatch
                    return json.dumps({
                         "operation": operation,
                         "arguments": [current_arg1],
                         "error": f"Failed to execute '{operation}' with one argument. It might require two arguments or different types. Detail: {te}",
                         "status": "error_execution_failed"
                    })


        # --- Format and Return Success ---
        # Handle potential complex numbers if cmath was used (not currently, but for future)
        if isinstance(result, complex):
             result_str = f"{result.real}{'+' if result.imag >= 0 else ''}{result.imag}j"
        else:
             # Try to format nicely (e.g., show integers as ints)
             try:
                 if isinstance(result, float) and result.is_integer():
                     result = int(result)
             except OverflowError:
                 pass # Keep large floats as floats
             result_str = result # Keep original for JSON

        print(f"Success: {operation} Result: {result_str}")
        return json.dumps({
            "operation": operation,
            "arguments_used": args_used,
            "result": result_str, # Use the potentially formatted value
            "status": "success"
        })

    # --- Error Handling During Math Execution ---
    except ValueError as ve: # Math domain errors (e.g., sqrt(-1), log(0))
        print(f"Math domain error for {operation}: {ve}")
        return json.dumps({
            "operation": operation,
            "arguments": [arg1, arg2] if arg2 is not None else [arg1],
            "error": f"Mathematical domain error: {ve}",
            "status": "error_math_domain"
        })
    except OverflowError as oe: # Result too large
        print(f"Overflow error for {operation}: {oe}")
        return json.dumps({
            "operation": operation,
            "arguments": [arg1, arg2] if arg2 is not None else [arg1],
            "error": f"Calculation resulted in overflow: {oe}",
            "status": "error_overflow"
        })
    except TypeError as te: # Catch unexpected TypeErrors during calls if logic missed something
         print(f"Type error during execution for {operation}: {te}")
         return json.dumps({
            "operation": operation,
            "arguments": [arg1, arg2] if arg2 is not None else [arg1],
            "error": f"Type error during calculation: {te}. Check argument types.",
            "status": "error_type"
         })
    except Exception as e: # Catch-all for any other errors
        print(f"Unexpected error during math calculation for {operation}: {e}")
        print(traceback.format_exc())
        return json.dumps({
            "operation": operation,
            "arguments": [arg1, arg2] if arg2 is not None else [arg1],
            "error": f"An unexpected error occurred during calculation: {e}",
            "status": "error_unexpected"
        })

# --- Example Test Cases ---
if __name__ == '__main__':
    print("--- Testing calculate_math ---")
    # Standard cases
    print("SQRT(16):", calculate_math('sqrt', 16))
    print("POW(2, 8):", calculate_math('pow', 2, 8))
    print("LOG10(100):", calculate_math('log10', 100))
    print("LOG(100, 10):", calculate_math('log', 100, 10)) # Log base 10
    print("LOG(math.e):", calculate_math('log', math.e))     # Natural log (arg2=None)
    print("LOG(8, 2):", calculate_math('log', 8, 2))        # Log base 2
    print("LOG2(8):", calculate_math('log2', 8))
    print("SIN(PI/2):", calculate_math('sin', math.pi / 2))
    print("DEGREES(PI):", calculate_math('degrees', math.pi))
    print("FACTORIAL(5):", calculate_math('factorial', 5))
    print("FACTORIAL(5.0):", calculate_math('factorial', 5.0)) # Should work
    print("GCD(48, 18):", calculate_math('gcd', 48, 18))
    print("GCD(48.0, 18):", calculate_math('gcd', 48.0, 18)) # Should work
    print("PI:", calculate_math('pi', 999)) # Arg ignored
    print("E:", calculate_math('e', None)) # Arg ignored
    print("EXP(2):", calculate_math('exp', 2))
    print("ATAN2(1, 1):", calculate_math('atan2', 1, 1)) # Should be pi/4

    print("\n--- Info/Warning Cases ---")
    print("FACTORIAL with 2 args:", calculate_math('factorial', 5, 2)) # Info: Extra arg ignored
    print("SQRT with 2 args:", calculate_math('sqrt', 16, 99)) # Info: Extra arg ignored
    print("PI with args:", calculate_math('pi', 1, 2))       # Info: Args ignored

    print("\n--- Error Cases ---")
    print("SQRT(-1):", calculate_math('sqrt', -1))               # Domain error
    print("LOG(-1):", calculate_math('log', -1))                 # Domain error
    print("LOG(10, -1):", calculate_math('log', 10, -1))         # Domain error (base)
    print("POW(2):", calculate_math('pow', 2))                   # Needs 2 args
    print("GCD(48):", calculate_math('gcd', 48))                 # Needs 2 args
    print("ATAN2(1):", calculate_math('atan2', 1))               # Needs 2 args
    print("FACTORIAL(5.5):", calculate_math('factorial', 5.5))   # Needs integer
    print("FACTORIAL(-5):", calculate_math('factorial', -5))     # Domain error
    print("GCD(48, 18.5):", calculate_math('gcd', 48, 18.5))    # Needs integer arg2
    print("UNKNOWN_FUNC(1):", calculate_math('unknown_func', 1)) # Non-existent func
    print("Empty Op:", calculate_math('', 1))                   # Invalid op
    print("No Arg1:", calculate_math('sqrt', None))             # Missing arg1 (internal check)
    print("Bad Op Type:", calculate_math(123, 1))               # Invalid op type
    print("Exp Large:", calculate_math('exp', 1000))            # Overflow error
    print("Pow Type Error:", calculate_math('pow', "a", "b"))    # Type error during execution (caught by general TypeError)