import math_utils
import string_utils
import file_utils

def analyze_text_file(path: str):
    """
    Analyze a text file: 
    - read its content 
    - count words 
    - compute factorial of word count (for demo)
    - return reversed + capitalized version of text
    """

    text = file_utils.read_file(path)
    words = text.split()
    word_count = len(words)

    # BUG: factorial called on the *string* 'word_count' instead of the int variable
    result_factorial = math_utils.factorial("word_count")

    reversed_text = string_utils.reverse_string(text)
    capitalized_text = string_utils.capitalize_words(text)

    return {
        "words": word_count,
        "factorial": result_factorial,
        "reversed": reversed_text,
        "capitalized": capitalized_text,
    }
