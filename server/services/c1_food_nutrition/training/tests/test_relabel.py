from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from c1_training.manifest import read_rows
from c1_training.relabel import (
    Change,
    RelabelError,
    apply_changes,
    main,
    read_changes,
    split_labels,
)

RowFactory = Callable[..., dict[str, str]]
ManifestWriter = Callable[[Path, Sequence[dict[str, str]]], Path]


def test_split_labels() -> None:
    assert split_labels("a|b") == ("a", "b")
    assert split_labels("") == ()


def test_apply_changes_sets_classes_and_note(row: RowFactory) -> None:
    rows = [
        row("a", classes="kiribath|lunu_sambol", processed="_processed/x/a.jpg"),
        row("b", classes="rice", processed="_processed/x/b.jpg"),
    ]
    change = Change(
        "_processed/x/a.jpg", ("lunu_sambol", "kiribath"), ("kiribath", "lunu_miris"), "red"
    )
    assert apply_changes(rows, [change], "relabelled") == 1
    assert rows[0]["classes"] == "kiribath|lunu_miris"
    assert rows[0]["clean_note"] == "relabelled (red)"
    assert rows[1]["classes"] == "rice" and rows[1]["clean_note"] == ""


def test_same_labels_count_as_no_change(row: RowFactory) -> None:
    rows = [row("a", classes="x|y", processed="p/a.jpg")]
    assert apply_changes(rows, [Change("p/a.jpg", ("x", "y"), ("y", "x"))], "n") == 0
    assert rows[0]["classes"] == "x|y"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (Change("p/none.jpg", ("rice",), ("rice",)), "not in the manifest"),
        (Change("p/a.jpg", ("dhal",), ("rice",)), "decision expects"),
        (Change("p/a.jpg", ("rice",), ()), "no new label"),
    ],
)
def test_bad_decisions_change_nothing(row: RowFactory, change: Change, message: str) -> None:
    rows = [
        row("a", classes="rice", processed="p/a.jpg"),
        row("b", classes="rice", processed="p/b.jpg"),
    ]
    good = Change("p/b.jpg", ("rice",), ("dhal",))
    with pytest.raises(RelabelError, match=message):
        apply_changes(rows, [good, change], "n")
    assert rows[1]["classes"] == "rice"  # the valid change was not applied either


def test_duplicate_decision_is_rejected(row: RowFactory) -> None:
    rows = [row("a", classes="rice", processed="p/a.jpg")]
    change = Change("p/a.jpg", ("rice",), ("dhal",))
    with pytest.raises(RelabelError, match="twice"):
        apply_changes(rows, [change, change], "n")


def test_read_changes_needs_columns(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("image,old_labels\np/a.jpg,rice\n", encoding="utf-8")
    with pytest.raises(RelabelError, match="new_labels"):
        read_changes(bad)


def test_cli_dry_run_then_apply(
    row: RowFactory,
    write_manifest: ManifestWriter,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    curation = tmp_path / "_curation"
    curation.mkdir()
    manifest = write_manifest(
        curation / "processed_manifest.csv",
        [row("a", classes="rice", processed="_processed/x/a.jpg"), row("b", classes="rice")],
    )
    decisions = tmp_path / "d.csv"
    decisions.write_text(
        "image,old_labels,new_labels,reason\n_processed\\x\\a.jpg,rice,dhal|rice,test\n",
        encoding="utf-8",
    )
    args = ["--data-dir", str(tmp_path), "--changes", str(decisions)]

    assert main(args) == 0
    assert "Dry run" in capsys.readouterr().out
    assert read_rows(manifest)[1][0]["classes"] == "rice"

    assert main([*args, "--apply"]) == 0
    assert read_rows(manifest)[1][0]["classes"] == "dhal|rice"
    assert len(list(curation.glob("processed_manifest_before_relabel_*.csv"))) == 1
    assert main([*args, "--apply"]) == 1  # decision no longer matches, and no second backup
    assert "decision expects" in capsys.readouterr().err
