import datetime
import logging
from multiprocessing import Pool
from typing import Tuple, Iterable

from src.parse.edbo import EdboData, EdboParser, ParserException

logging.basicConfig(filename="parser.log", level=logging.INFO)


DATA = EdboData(
    last_name="Іваненко",
    first_name="Іван",
    middle_name="Іванович",
    first_select_text="Документи про вищу освіту",
    second_select_text="Диплом БАКАЛАВРА",
    document_series="В12",
    number_of_digits=7,
    birth_date=datetime.date(1995, 9, 14),
)


SESSION_ID = "kbmuvp213goegksbf1b1r2ilk9"
CAPTCHA = "v9y2"


def run_parser(range_: Tuple[int, int]):
    try:
        parser = EdboParser(DATA, range_, SESSION_ID, CAPTCHA)
    except ParserException:
        raise

    parser.run()


def split(range_: Tuple[int, int], parts: int) -> Iterable[Tuple[int, int]]:
    """Splits `range_` into `parts` of equal ranges
        Example:
        >>> split((1, 3), 2)
        [(1, 2), (2, 3)]
    """
    size = abs(range_[1] - range_[0])
    offset = range_[0]
    k, m = divmod(size, parts)
    return (
        (i * k + min(i, m) + offset, (i + 1) * k + min(i + 1, m) + offset)
        for i in range(parts)
    )


def main():
    RANGE = (5355, 99999)
    WORKERS = 3  # Looks like an optimal number of workers per one machine

    subranges = split(RANGE, WORKERS)

    with Pool(processes=WORKERS) as pool:
        pool.map(run_parser, subranges)


if __name__ == "__main__":
    main()
