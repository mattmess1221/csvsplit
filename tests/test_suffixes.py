import itertools

import pytest
from syrupy.assertion import SnapshotAssertion

from csvsplit.csvsplit import AlphabeticSuffixes, HexSuffixes, NumericSuffixes, Suffixes


@pytest.mark.parametrize(
    ("suffix", "suffix_length", "cutoff"),
    [
        pytest.param(HexSuffixes(), 3, 100, id="hex"),
        pytest.param(NumericSuffixes(1), 2, 50, id="numeric"),
        pytest.param(AlphabeticSuffixes(), 2, 26**2 + 1, id="alphabetic"),
    ],
)
def test_suffixes(
    suffix: Suffixes, suffix_length: int, cutoff: int, snapshot: SnapshotAssertion
):
    suffixes = list(itertools.islice(suffix.suffixes(suffix_length), cutoff))

    assert snapshot == suffixes


# def test_numeric_suffixes(snapshot: SnapshotAssertion):
#     suffixes = list(itertools.islice(NumericSuffixes(1).suffixes(2), 50))

#     assert snapshot == suffixes


# def test_alphabetic_suffixes(snapshot: SnapshotAssertion):
#     suffixes = list(itertools.islice(AlphabeticSuffixes().suffixes(2), 26**2 + 1))

#     assert snapshot == suffixes
