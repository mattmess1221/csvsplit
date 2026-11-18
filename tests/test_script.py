from pathlib import Path

import pytest
from syrupy.assertion import SnapshotAssertion

from csvsplit import main

data_fixture = Path(__file__).parent / "fixtures/data"
input_csv = data_fixture / "input/input.csv"


def test_script_help(capsys: pytest.CaptureFixture, snapshot: SnapshotAssertion):
    try:
        main(["-h"])
    except SystemExit as e:
        assert e.code == 0

    out, _err = capsys.readouterr()
    assert snapshot == out


def test_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
):
    monkeypatch.chdir(tmp_path)

    try:
        main([str(input_csv)])
    except SystemExit as e:
        assert e.code == 0

    for path in tmp_path.iterdir():
        assert snapshot(name=path.name) == path.read_text()


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--records=10000"], id="records"),
        pytest.param(["--headers"], id="headers"),
    ],
)
def test_script_output_content(
    args: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
):

    monkeypatch.chdir(tmp_path)

    try:
        main([str(input_csv), *args])
    except SystemExit as e:
        assert e.code == 0

    for file in tmp_path.iterdir():
        assert snapshot(name=file.name) == {"row_count": file.read_text().count("\n")}


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["prefix-", "--additional-suffix=-suffix"], id="prefix-suffix"),
        pytest.param(["-x"], id="hexnames"),
        pytest.param(["-d"], id="decnames"),
    ],
)
def test_script_output_names(
    args: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
):
    monkeypatch.chdir(tmp_path)

    try:
        main([str(input_csv), *args])
    except SystemExit as e:
        assert e.code == 0

    assert snapshot == {p.name for p in tmp_path.iterdir()}
