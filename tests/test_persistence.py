"""Tests for position and config persistence."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from readaloud.persistence import ConfigStore, PositionStore, file_hash


def test_file_hash(tmp_path: Path):
    f = tmp_path / "sample.txt"
    f.write_text("Hello world readaloud", encoding="utf-8")
    h1 = file_hash(f)
    assert len(h1) == 16

    # Same content produces same hash
    f2 = tmp_path / "sample2.txt"
    f2.write_text("Hello world readaloud", encoding="utf-8")
    assert file_hash(f2) == h1

    # Different content produces different hash
    f3 = tmp_path / "sample3.txt"
    f3.write_text("Different content", encoding="utf-8")
    assert file_hash(f3) != h1


def test_position_store(tmp_path: Path):
    with patch("readaloud.persistence._data_dir", return_value=tmp_path):
        store = PositionStore()
        assert store.get("nonexistent") is None

        store.save("hash123", page=3, sentence=7, filename="test.pdf")
        saved = store.get("hash123")
        assert saved is not None
        assert saved["page"] == 3
        assert saved["sentence"] == 7
        assert saved["filename"] == "test.pdf"

        # Persistence across new instance
        store2 = PositionStore()
        saved2 = store2.get("hash123")
        assert saved2["page"] == 3

        # Clear position
        store.clear("hash123")
        assert store.get("hash123") is None


def test_config_store(tmp_path: Path):
    with patch("readaloud.persistence._config_dir", return_value=tmp_path):
        cfg = ConfigStore()
        assert cfg.get("speed") == 1.0

        cfg.set("speed", 1.5)
        assert cfg.get("speed") == 1.5

        # Persistence across new instance
        cfg2 = ConfigStore()
        assert cfg2.get("speed") == 1.5

        # Update multiple
        cfg2.update(speed=2.0, voice="en_US_1")
        assert cfg2.get("speed") == 2.0
        assert cfg2.get("voice") == "en_US_1"
