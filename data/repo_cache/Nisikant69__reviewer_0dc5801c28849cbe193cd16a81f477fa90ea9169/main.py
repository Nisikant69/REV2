import math_utils
import string_utils
import file_utils

def demo():
    # Math utils
    print("Add 3 + 5 =", math_utils.add(3, 5))
    print("Factorial of 5 =", math_utils.factorial(5))

    # String utils
    text = "hello world"
    print("Reversed:", string_utils.reverse_string(text))
    print("Capitalized:", string_utils.capitalize_words(text))

    # File utils
    file_utils.write_file("demo.txt", "This is a demo file.")
    print("File content:", file_utils.read_file("demo.txt"))


if __name__ == "__main__":
    demo()
