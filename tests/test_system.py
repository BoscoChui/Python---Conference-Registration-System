import json

import pytest

from conference_registration import Attendee, AttendeeActor, Blockchain, MinerActor, OrganizerActor, Wallet


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


def test_attendee_registration_workflow_and_persistence(tmp_path) -> None:
    chain = Blockchain(initial_difficulty=1)
    wallet = Wallet()
    wallet_directory = tmp_path / "wallets"

    transaction = chain.register_attendee(wallet, " Alice ", "ALICE@example.com", wallet_directory)

    assert transaction["attendee_id"] == "A001"
    assert transaction["name"] == "Alice"
    assert transaction["email"] == "alice@example.com"
    assert transaction["public_key"].startswith("-----BEGIN RSA PUBLIC KEY-----")
    assert (wallet_directory / "A001.pem").exists()
    assert "private" not in json.dumps(transaction).lower()
    assert chain.get_public_key("A001") == transaction["public_key"]
    assert chain.list_attendees(include_pending=True)[0]["status"] == "Pending"

    chain.mine_pending_transactions("tester")
    attendees_path = tmp_path / "attendees.json"
    chain.save_attendees(attendees_path)
    saved_attendees = json.loads(attendees_path.read_text())
    assert saved_attendees[0]["status"] == "Registered"
    assert saved_attendees[0]["attendee_id"] == "A001"


def test_registration_rejects_invalid_and_duplicate_details(tmp_path) -> None:
    chain = Blockchain(initial_difficulty=1)
    wallet = Wallet()
    chain.register_attendee(wallet, "Alice", "alice@example.com", tmp_path / "wallets")

    with pytest.raises(ValueError, match="invalid email"):
        chain.register_attendee(wallet, "Bob", "not-an-email", tmp_path / "wallets")
    with pytest.raises(ValueError, match="email already registered"):
        chain.register_attendee(wallet, "Bob", "ALICE@example.com", tmp_path / "wallets")
    with pytest.raises(ValueError, match="ID already registered"):
        chain.register_attendee(wallet, "Bob", "bob@example.com", tmp_path / "wallets", attendee_id="A001")


def test_actor_workflows_end_to_end(tmp_path) -> None:
    chain = Blockchain(initial_difficulty=1)
    alice = AttendeeActor(chain, wallet_directory=tmp_path / "wallets")
    miner = MinerActor(chain, "miner-1")
    organizer = OrganizerActor(chain)

    registration = alice.register("Alice", "alice@example.com")
    assert registration["message"] == "Registration transaction created and added to pending pool"
    assert miner.verify_pending_attendance() == {"valid_attendance": 0, "invalid_attendance": 0}
    miner.mine()

    check_in = alice.check_in("S101")
    assert check_in["message"] == "Signed attendance certificate added to pending pool"
    assert miner.verify_pending_attendance() == {"valid_attendance": 1, "invalid_attendance": 0}
    miner.mine()

    assert alice.attendance_history() == ["S101"]
    assert organizer.registered_attendees()[0]["attendee_id"] == "A001"
    assert organizer.sessions_for_participant("A001") == ["S101"]
    assert organizer.participants_in_session("S101") == ["A001"]
    assert organizer.registration_status("A001") == "registered"
    assert organizer.participants_not_in_session("S102") == ["A001"]
    assert organizer.attendance_statistics()["total_attendance_records"] == 1
    assert miner.validate_chain() == (True, "Blockchain is valid")


def test_attendee_cannot_check_in_before_registration(tmp_path) -> None:
    attendee = AttendeeActor(Blockchain(initial_difficulty=1), wallet_directory=tmp_path / "wallets")
    with pytest.raises(ValueError, match="register an attendee account first"):
        attendee.check_in("S101")