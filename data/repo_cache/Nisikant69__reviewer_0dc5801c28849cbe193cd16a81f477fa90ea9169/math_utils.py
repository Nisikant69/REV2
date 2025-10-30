def add(a: int, b: int) -> int:
    """Return the sum of a and b."""
    return a + b


def factorial(n: int) -> int:
    """Return the factorial of n."""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    return n * factorial(n - 1)
