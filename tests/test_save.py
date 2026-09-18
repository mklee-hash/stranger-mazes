import pytest

from stranger_mazes.engine import save


@pytest.fixture(autouse=True)
def _isolated_save_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(save, "SAVE_DIR", tmp_path / "saves")


def test_no_save_exists_until_something_is_written():
    assert save.has_save("guest_like_user") is False
    assert save.load_save("guest_like_user") is None


def test_write_then_load_roundtrip():
    state = {"character_id": "mike", "hp": 2, "stage_id": 2, "position": 1}
    save.write_save("alice", state)
    assert save.has_save("alice") is True
    assert save.load_save("alice") == state


def test_write_overwrites_previous_save_for_the_same_user():
    save.write_save("bob", {"stage_id": 1})
    save.write_save("bob", {"stage_id": 3})
    assert save.load_save("bob") == {"stage_id": 3}


def test_delete_save_removes_it():
    save.write_save("carol", {"stage_id": 1})
    save.delete_save("carol")
    assert save.has_save("carol") is False
    assert save.load_save("carol") is None


def test_different_usernames_do_not_collide():
    save.write_save("dave", {"stage_id": 1})
    save.write_save("eve", {"stage_id": 5})
    assert save.load_save("dave") == {"stage_id": 1}
    assert save.load_save("eve") == {"stage_id": 5}
