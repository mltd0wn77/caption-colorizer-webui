import re
from typing import List
from .parser import Caption

def split_long_lines(captions: List[Caption], max_length: int = 16) -> List[Caption]:
    """
    Splits long single-line captions into two lines, ensuring words are not broken.
    This is applied only to captions that are currently on a single line and exceed
    the specified max_length. It correctly handles numbers with spaces as single tokens.
    """
    # This regex finds sequences of digits (potentially separated by spaces) or any non-whitespace sequences.
    # This ensures that "128 000" is treated as one token.
    token_regex = re.compile(r'\d+(?:\s\d+)*|\S+')

    for caption in captions:
        if len(caption.lines) == 1 and len(caption.lines[0]) > max_length:
            line_text = caption.lines[0]
            words = token_regex.findall(line_text)

            if len(words) < 2:
                continue  # Cannot split if there's only one word or none

            # Find the split point that results in two lines of the most similar length
            best_split_index = -1
            min_length_diff = float('inf')

            for i in range(1, len(words)):
                line1 = " ".join(words[:i])
                line2 = " ".join(words[i:])
                diff = abs(len(line1) - len(line2))
                
                if diff < min_length_diff:
                    min_length_diff = diff
                    best_split_index = i
            
            if best_split_index != -1:
                new_line1 = " ".join(words[:best_split_index])
                new_line2 = " ".join(words[best_split_index:])
                caption.lines = [new_line1, new_line2]
    
    return captions


