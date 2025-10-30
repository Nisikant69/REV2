# main.py

def sum_of_squares(n):
    """
    Calculates the sum of squares up to n.
    """
    total = 0
    for i in range(1, n + 1):
        total += i * i
    return total

def calculate_average(numbers):
    """
    Calculates the average of a list of numbers.
    """
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)

# --- NEW CODE FOR PR TESTING ---
from buggy_feature import factorial

def test_factorial_function():
    """
    A test function to ensure the factorial function works.
    This will also be used to trigger the review process.
    """
    print("Testing factorial(5)...")
    result = factorial(5)
    print(f"The factorial of 5 is: {result}")
    
# --- END NEW CODE ---

if __name__ == "__main__":
    result = sum_of_squares(5)
    print(f"The sum of squares up to 5 is: {result}")
    
    avg = calculate_average([10, 20, 30])
    print(f"The average is: {avg}")

    # Call the new test function
    test_factorial_function()
