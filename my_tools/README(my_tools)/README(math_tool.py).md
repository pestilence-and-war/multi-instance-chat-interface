# Math Tool

This tool provides the AI with the ability to perform various mathematical calculations using Python's built-in `math` module functions and constants. It's designed to handle common operations requested in a conversational context.

## Purpose

To enable the AI to perform basic to advanced mathematical operations, retrieve mathematical constants, and answer numerical queries by leveraging Python's `math` library.

## How to Use (for AI)

The AI can call the `calculate_math` function when a user asks for a mathematical operation, a calculation involving numbers, or the value of a mathematical constant.

## Function Details

### `calculate_math(operation: str, arg1: float | int, arg2: float | int=None) -> str`

Performs mathematical calculations using Python's `math` module functions and constants.

**Description:**
Handles common functions like square root (`sqrt`), power (`pow`), logarithms (`log`, `log10`), trigonometric functions (`sin`, `cos`, `tan`), factorial, greatest common divisor (`gcd`), as well as constants like pi and e.

**Parameters:**

*   **`operation`** (`str`): The name of the math function or constant (e.g., `'sqrt'`, `'pow'`, `'log'`, `'log10'`, `'sin'`, `'cos'`, `'factorial'`, `'gcd'`, `'pi'`, `'e'`, `'tau'`). This is case-insensitive. **Required.**
*   **`arg1`** (`float | int`): The primary numeric argument. **Required** for functions, ignored for constants.
*   **`arg2`** (`float | int`, *optional*): The secondary numeric argument (e.g., for `pow(arg1, arg2)`, `log(arg1, arg2)` [log base `arg2`], `gcd(arg1, arg2)`). Used only if the operation requires it.

**Returns:**
`str`: A string representation of the calculation result or the constant's value.