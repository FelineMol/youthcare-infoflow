"""Publication label overrides for reverse-scored items."""
from src.labels import load_label_overrides, publication_label


def test_reverse_scored_items_stated_positively():
    ov = load_label_overrides()
    assert len(ov) >= 11
    # negatively-worded items are overridden to read in the positive direction
    assert ov["FAM-BEV-c"].lower().startswith("does not")
    assert ov["PRO-INFO-b"].lower().startswith("rarely")


def test_publication_label_falls_back_when_no_override():
    assert publication_label("NO-SUCH-BUNDLE", "fallback", {}) == "fallback"
    assert publication_label("FAM-BEV-c", "ignored fallback",
                             {"FAM-BEV-c": "Overridden"}) == "Overridden"
