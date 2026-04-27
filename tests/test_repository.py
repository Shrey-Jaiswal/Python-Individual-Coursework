from pathlib import Path

import pytest

from digital_id.domain import DigitalId, IdentityAttributes, MutableAttributes
from digital_id.persistence import DuplicateIdentityError, InMemoryRepository, JsonStore, NotFoundError


def make_identity(digital_id: str, national_id: str) -> DigitalId:
    identity = IdentityAttributes(
        digital_id=digital_id,
        national_id=national_id,
        date_of_birth="1990-01-01",
    )
    mutable = MutableAttributes(
        name="Ava Example",
        address="1 High Street",
        email="ava@example.com",
        phone="0000000000",
    )
    return DigitalId(identity=identity, mutable=mutable)


def test_repository_add_and_get() -> None:
    repo = InMemoryRepository()
    identity = make_identity("did-1", "nat-1")
    repo.add(identity)

    assert repo.get_by_id("did-1") is identity
    assert repo.get_by_national_id("nat-1") is identity


def test_repository_duplicate_rejected() -> None:
    repo = InMemoryRepository()
    repo.add(make_identity("did-1", "nat-1"))
    with pytest.raises(DuplicateIdentityError):
        repo.add(make_identity("did-1", "nat-2"))


def test_repository_remove_missing_raises() -> None:
    repo = InMemoryRepository()
    with pytest.raises(NotFoundError):
        repo.remove("missing")


def test_json_store_roundtrip(tmp_path: Path) -> None:
    store = JsonStore(tmp_path / "ids.json")
    identity = make_identity("did-1", "nat-1")
    store.save([identity])

    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].identity.digital_id == "did-1"
    assert loaded[0].identity.national_id == "nat-1"
