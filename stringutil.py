import functools
import dateutil


Any = object



def zip_max(*lists):
    """
    Return a list of maxiumum elements of lists compared index-wise

    zipped = [0, 9, 0] zip [1, 2, 3] -> [(0,1), (9,2), (0,3)]
    for each in zipped: max(each) = [ 1, 9, 3 ]
    """
    if len({len(input_list) for input_list in lists}) > 1:
        raise ValueError("input lists must have equal sizes")
    return [max(zipped_tuple) for zipped_tuple in zip(*lists)]


def clean_string(input: str, remove_phrases: list[str]) -> str:
    def remove_phrase(input: str, phrase: str):
        return input.replace(phrase, "")

    return functools.reduce(remove_phrase, remove_phrases, input)


def clean_row(row: tuple[str, ...], remove_phrases: list[str]):
    return tuple(clean_string(s, remove_phrases) for s in row)

