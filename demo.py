"""Command-line demonstration covering the project rubric."""

from pathlib import Path

from conference_registration import Attendee, Blockchain, Wallet


def main() -> None:
    data_dir = Path("data")
    wallet = Wallet()
    blockchain = Blockchain(initial_difficulty=2)
    attendees = [("A001", "Alice Chan", "alice@example.com"), ("A002", "Bob Lee", "bob@example.com"), ("A003", "Carol Wong", "carol@example.com")]
    print("=== Register attendees ===")
    for attendee_id, name, email in attendees:
        public_key = wallet.create_key_pair(attendee_id)
        blockchain.add_registration(Attendee(attendee_id, name, email, public_key))
        print(f"{attendee_id}: wallet key created; public key queued")
    blockchain.mine_pending_transactions("miner-1")
    print("\n=== Record signed attendance ===")
    for attendee_id, session_id in [("A001", "S101"), ("A001", "S102"), ("A002", "S101")]:
        record = blockchain.create_attendance(wallet, attendee_id, session_id)
        blockchain.add_attendance(record)
        print(f"{attendee_id} -> {session_id}: signature verified and queued")
    blockchain.mine_pending_transactions("miner-1")
    tampered = blockchain.create_attendance(wallet, "A003", "S101")
    tampered["session_id"] = "S999"
    print(f"Tampered certificate accepted? {blockchain.verify_attendance(tampered)}")
    print("\n=== Queries ===")
    print("A001 sessions:", blockchain.sessions_attended_by("A001"))
    print("S101 attendees:", blockchain.attendees_in_session("S101"))
    print("Not in S102:", blockchain.registered_not_in_session("S102"))
    print("A003 status:", blockchain.registration_status("A003"))
    print("Statistics:", blockchain.attendance_statistics())
    print("Difficulty history:", blockchain.difficulty_history)
    valid, reason = blockchain.validate()
    print(f"\nBlockchain validation: {valid} ({reason})")
    blockchain.save(data_dir / "blockchain.json")
    wallet.save(data_dir / "wallet.json")
    print("Saved data/blockchain.json and data/wallet.json")


if __name__ == "__main__":
    main()