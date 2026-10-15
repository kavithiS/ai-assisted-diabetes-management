from pathlib import Path

import pytest

from c1_food_nutrition.ml.labels import (
    DEFAULT_PATH,
    UnmappedClassError,
    UnreviewedClassError,
    concepts_for,
    foods_for,
    load_class_concepts,
    load_class_foods,
)


def test_shipped_map_is_complete_and_consistent() -> None:
    mapping = load_class_concepts()
    assert len(mapping) >= 100
    assert all(concept for concept in mapping.values())
    # Classes the trained model uses (checked against the curation class map on 2026-10-15).
    for name in ("kiribath", "lunu_miris", "pol_sambol", "hoppers", "white_rice", "fish_curry"):
        assert name in mapping, name
    assert mapping["lunu_miris"] == mapping["pol_sambol"] == "sambol"
    assert DEFAULT_PATH.is_file()


def test_concepts_for_returns_only_requested_classes() -> None:
    mapping = {"a": "x", "b": "y", "c": "z"}
    assert concepts_for(["c", "a"], mapping) == {"c": "z", "a": "x"}


def test_unmapped_class_is_an_error() -> None:
    with pytest.raises(UnmappedClassError, match="no_such_food"):
        concepts_for(["no_such_food"], {"a": "x"})


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("class,concept_id\na,x\na,y\n", "twice"),
        ("class,concept_id\na,\n", "empty"),
    ],
)
def test_bad_map_files_are_rejected(tmp_path: Path, text: str, message: str) -> None:
    path = tmp_path / "map.csv"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_class_concepts(path)


def test_reviewed_food_matches_are_consistent() -> None:
    table = load_class_foods()
    reviewed = {name: e for name, e in table.items() if e.match}
    assert len(reviewed) >= 48
    for name, entry in reviewed.items():
        assert (entry.food_id is not None) == (entry.match != "none"), name
        assert entry.note, f"{name} needs a note"
    assert table["kiribath"].food_id == "SL_9" and table["kiribath"].match == "exact"
    assert not table["kiribath"].is_approximate
    assert table["chicken_bun"].is_approximate and table["chicken_bun"].food_id == "SL_11"
    # No honest match: the nutrients stay unknown instead of borrowing a broad concept.
    for name in ("lunu_miris", "dhal_curry", "meat_curry", "cutlet"):
        assert table[name].food_id is None and table[name].match == "none", name
    # Fried Noodles (SL_32) has the same numbers as Carrot Curry (SL_74): never matched.
    assert "SL_32" not in {e.food_id for e in table.values()}


def test_unreviewed_class_cannot_be_used_by_a_model() -> None:
    table = load_class_foods()
    assert table["almond"].match == ""  # in the map, but its food match was not reviewed
    with pytest.raises(UnreviewedClassError, match="almond"):
        foods_for(["kiribath", "almond"], table)
    with pytest.raises(UnmappedClassError, match="no_such_food"):
        foods_for(["no_such_food"], table)
    assert set(foods_for(["kiribath", "lunu_miris"], table)) == {"kiribath", "lunu_miris"}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("class,concept_id,food_id,match,note\na,x,SL_1,great,\n", "unknown match"),
        ("class,concept_id,food_id,match,note\na,x,,exact,\n", "exactly when"),
        ("class,concept_id,food_id,match,note\na,x,SL_1,none,\n", "exactly when"),
    ],
)
def test_bad_food_matches_are_rejected(tmp_path: Path, text: str, message: str) -> None:
    path = tmp_path / "map.csv"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_class_foods(path)
