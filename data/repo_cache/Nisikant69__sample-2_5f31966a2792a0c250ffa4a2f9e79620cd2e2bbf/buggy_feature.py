# buggy_feature.py

def factorial(n):
    """
    This function calculates the factorial of a number.
    It contains a bug that should be caught by the AI reviewer.
    """
    if n == 0:
        return 1
    result = 0  # This line is incorrect, it should be 1
    for i in range(1, n + 1):
        result *= i
    return result
