#!/usr/bin/env python3
"""
This script mimicks the behavior of the unix split command, but specialized for csv files.
"""

from __future__ import annotations

import argparse
import csv
import sys
import textwrap
from abc import ABC, abstractmethod
from collections.abc import Callable, Generator, Iterable
from contextlib import AbstractContextManager, contextmanager
from functools import partial
from types import SimpleNamespace, TracebackType
from typing import TYPE_CHECKING, Generic, Literal, ParamSpec, TextIO, TypeVar, cast

if TYPE_CHECKING:
    import _csv

    from _typeshed import SupportsWrite


P = ParamSpec("P")
R = TypeVar("R")


class LazyContextManager(Generic[R]):
    """
    Creates a new context manager, which lazily initializes on the first access
    to one of the entered object's attributes.

    Example:

        ```py
        with LazyContextManager(open, "file", "w") as file:
            print("file is not yet opened")
            file.write("Hello, world!\\n")  # file is opened here
        print("file is closed")

        ```
    """

    def __init__(
        self,
        factory: Callable[P, AbstractContextManager[R]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self._factory = partial(factory, *args, **kwargs)
        self._ctx: AbstractContextManager[R] | None = None
        self._value: R

    def __enter__(self) -> R:
        if self._ctx is not None:
            raise TypeError("LazyContextManager cannot be reused")
        that = self

        class proxy:
            def __getattribute__(self, name: str) -> object:
                # Initialize the context manager on the first attribute access.
                if that._ctx is None:
                    that._ctx = that._factory()
                    that._value = that._ctx.__enter__()

                return that._value.__getattribute__(name)

        return cast(R, proxy())

    def __exit__(
        self,
        exc_t: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        if self._ctx is None:
            # If no attributes were accessed, __exit__ doesn't need to be called
            return

        return self._ctx.__exit__(exc_t, exc, tb)


class Args(SimpleNamespace):
    file: str
    prefix: str

    suffix_length: int
    additional_suffix: str

    suffixes: Suffixes

    records: int

    verbose: bool

    headers: bool

    dialect: str
    delimiter: str
    quotechar: str
    escapechar: str

    def reader(self, buffer: Iterable[str]) -> _csv.Reader:
        return csv.reader(
            buffer,
            dialect=self.dialect,
            delimiter=self.delimiter,
            quotechar=self.quotechar,
            escapechar=self.escapechar,
        )

    def writer(self, buffer: SupportsWrite[str]) -> _csv.Writer:
        return csv.writer(
            buffer,
            dialect=self.dialect,
            delimiter=self.delimiter,
            quotechar=self.quotechar,
            escapechar=self.escapechar,
        )


@contextmanager
def open_file(file: str, mode: Literal["r", "w"] = "r") -> Generator[TextIO]:
    if mode == "r" and file == "-":
        yield sys.stdin
    else:
        with open(file, mode, encoding="utf-8", newline="") as f:
            yield f


class Suffixes(ABC):
    def __init__(self, start: str | int = 0) -> None:
        self.start = int(start)

    def _counting(self) -> Generator[int]:
        num = self.start
        while True:
            yield num
            num += 1

    def suffixes(self, suffix_length: int) -> Generator[str]:
        for x in self._counting():
            yield self.format_filename(x, suffix_length)

    @abstractmethod
    def format_filename(self, value: int, suffix_length) -> str: ...


class HexSuffixes(Suffixes):
    def format_filename(self, value: int, suffix_length: int) -> str:
        return f"{value:0{suffix_length}x}"


class NumericSuffixes(Suffixes):
    def format_filename(self, value: int, suffix_length: int) -> str:
        return f"{value:0{suffix_length}d}"


class AlphabeticSuffixes(Suffixes):
    A_ORD = ord("a")

    def format_filename(self, value: int, suffix_length: int) -> str:
        max_value = 26**suffix_length
        prefix = "z" * ((value) // max_value)
        value %= max_value
        digits = []
        while value:
            digits.insert(0, chr(self.A_ORD + (value % 26)))
            value //= 26
        return prefix + "".join(digits).rjust(suffix_length, "a")


def parse_args(argv: list[str]) -> Args:
    parser = argparse.ArgumentParser(
        prog="csvsplit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """
            Output pieces of a csv FILE to PREFIXaa, PREFIXab, ...;
            default size is 1000 records, and default PREFIX is 'x'.

            With no FILE, or when FILE is -, read standard input
            """
        ),
    )
    parser.add_argument("file", metavar="FILE", type=str, nargs="?", default="-")
    parser.add_argument("prefix", metavar="PREFIX", nargs="?", default="x")
    parser.add_argument(
        "-a",
        "--suffix-length",
        metavar="N",
        type=int,
        default=2,
        help="Generate suffixes of length N (default: 2)",
    )
    parser.add_argument(
        "--additional-suffix",
        metavar="SUFFIX",
        default="",
        help="Append an additional SUFFIX to file names",
    )
    parser.add_argument(
        "-d",
        "--numeric-suffixes",
        dest="suffixes",
        nargs="?",
        type=NumericSuffixes,
        const=NumericSuffixes(0),
        help="Use decimal suffixes with an optional starting value",
    )
    parser.add_argument(
        "-x",
        "--hex-suffixes",
        dest="suffixes",
        nargs="?",
        type=HexSuffixes,
        const=HexSuffixes(0),
        help="Use hex suffixes with an optional starting value",
    )
    parser.set_defaults(suffixes=AlphabeticSuffixes())

    parser.add_argument(
        "-r",
        "--records",
        metavar="NUMBER",
        type=int,
        default=1000,
        help="Include NUMBER records per file (default: 1000)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print a disgnostic just before each output file is opened",
    )

    csv_group = parser.add_argument_group(title="CSV Properties")
    csv_group.add_argument(
        "-H",
        "--headers",
        action="store_true",
        help="Include headers from input file in output files",
    )
    csv_group.add_argument(
        "-D",
        "--dialect",
        choices=csv.list_dialects(),
        default="excel",
        help="The registered dialect preset to use (default: excel)",
    )
    csv_group.add_argument(
        "-m", "--delimiter", default=",", help="The CSV field delimiter (default: ,)"
    )
    csv_group.add_argument(
        "-q", "--quotechar", default='"', help='The CSV quote charater (default: ")'
    )
    csv_group.add_argument("-e", "--escapechar", help="The CSV escape character")

    return parser.parse_args(argv, Args())


def copy_csv_file(
    reader: _csv.Reader,
    writer: _csv.Writer,
    *,
    max_records: int,
) -> bool:
    """Copies csv contents from a reader to a writer

    Returns False when max_records is reached or True when there are no more records to read.
    """
    for i, row in enumerate(reader):
        writer.writerow(row)
        if i >= max_records:
            return False

    return True


@contextmanager
def exit_on_interrupt():
    try:
        yield
    except KeyboardInterrupt as e:
        raise SystemExit(130) from e


@exit_on_interrupt()
def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    @contextmanager
    def create_writer(suffix: str, headers: list[str] | None) -> Generator[_csv.Writer]:
        fname = args.prefix + suffix + args.additional_suffix

        if args.verbose:
            print(f"creating file {fname!r}")

        with open_file(fname, "w") as f:
            writer = args.writer(f)

            if headers is not None:
                writer.writerow(headers)

            yield writer

    with open_file(args.file) as f:
        reader = args.reader(f)

        headers = None
        if args.headers:
            try:
                headers = next(reader)
            except StopIteration:
                return

        for suffix in args.suffixes.suffixes(args.suffix_length):
            with LazyContextManager(create_writer, suffix, headers) as writer:
                if copy_csv_file(reader, writer, max_records=args.records):
                    break


if __name__ == "__main__":
    main()
