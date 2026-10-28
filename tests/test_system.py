import json

import pytest

from conference_registration import Attendee, Blockchain, Wallet


def registered_chain() -> tuple[Blockchain, Wallet]:
    chain = Blockchain(initial_difficulty=1)
    wallet = Wallet()
    public_key = wallet.create_key_pair("A001")
    chain.add_registration(Attendee("A001", "Alice", "alice@example.com", public_key))
    chain.mine_pending_transactions("tester")
    return chain, wallet


def test_registration_attendance_and_queries() -> None:
    chain, wallet = registered_chain()
    record = chain.create_attendance(wallet, "A001", "S1")
    chain.add_attendance(record)
    chain.mine_pending_transactions("tester")
    assert chain.validate() == (True, "Blockchain is valid")
    assert chain.sessions_attended_by("A001") == ["S1"]
    assert chain.attendees_in_session("S1") == ["A001"]
    assert chain.registration_status("A001") == "registered"


def test_tampering_fails_and_duplicate_is_rejected() -> None:
    chain, wallet = registered_chain()
    record = chain.create_attendance(wallet, "A001", "S1")
    chain.add_attendance(record)
    tampered = dict(record, session_id="S2")
    assert chain.verify_attendance(tampered) is False
    with pytest.raises(ValueError, match="Duplicate"):
        chain.add_attendance(record)


def test_json_persistence(tmp_path) -> None:
    chain, _ = registered_chain()
    path = tmp_path / "blockchain.json"
    chain.save(path)
    loaded = Blockchain.load(path)
    assert loaded.validate() == (True, "Blockchain is valid")
    assert json.loads(path.read_text())[-1]["transactions"][0]["type"] == "registration"


def test_dynamic_adjustment_never_below_one() -> None:
    chain = Blockchain(initial_difficulty=1)
    chain.TARGET_BLOCK_TIME = 0.000001
    chain.ADJUSTMENT_INTERVAL = 2
    for _ in range(2):
        chain.mine_pending_transactions("tester")
    assert chain.latest_block.difficulty >= 1
    assert any("adjustment_at_block" in item for item in chain.difficulty_history)