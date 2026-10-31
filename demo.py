"""Command-line demonstration covering the project rubric."""

from pathlib import Path

from conference_registration import AttendeeActor, Blockchain, MinerActor, OrganizerActor


def main() -> None:
    data_dir = Path("data")
    blockchain = Blockchain(initial_difficulty=2)
    miner = MinerActor(blockchain, "miner-1")
    organizer = OrganizerActor(blockchain)
    print("=== Register attendees ===")
    attendees = []
    for name, email in [("Alice Chan", "alice@example.com"), ("Bob Lee", "bob@example.com"), ("Carol Wong", "carol@example.com")]:
        attendee = AttendeeActor(blockchain, wallet_directory=data_dir / "wallets")
        result = attendee.register(name, email)
        attendees.append(attendee)
        print(f"{result['attendee_id']}: key pair created; private key saved; public key queued")
    print("Pending registrations:", [attendee["attendee_id"] for attendee in blockchain.list_attendees(include_pending=True)])
    print("Miner pending pool:", len(miner.pending_transactions()), "transactions")
    miner.mine()
    blockchain.save_attendees(data_dir / "attendees.json")
    print("Registration block mined; attendees saved to data/attendees.json")
    print("\n=== Record signed attendance ===")
    for attendee, session_id in [(attendees[0], "S101"), (attendees[0], "S102"), (attendees[1], "S101")]:
        result = attendee.check_in(session_id)
        print(f"{attendee.attendee_id} -> {session_id}: {result['message']}")
    print("Miner verification:", miner.verify_pending_attendance())
    miner.mine()
    tampered = blockchain.create_attendance(attendees[2].wallet, "A003", "S101")
    tampered["session_id"] = "S999"
    print(f"Tampered certificate accepted? {blockchain.verify_attendance(tampered)}")
    print("\n=== Queries ===")
    print("Registered attendees:", organizer.registered_attendees())
    print("A001 sessions:", organizer.sessions_for_participant("A001"))
    print("S101 attendees:", organizer.participants_in_session("S101"))
    print("Not in S102:", organizer.participants_not_in_session("S102"))
    print("A003 status:", organizer.registration_status("A003"))
    print("Statistics:", organizer.attendance_statistics())
    print("Difficulty history:", blockchain.difficulty_history)
    valid, reason = miner.validate_chain()
    print(f"\nBlockchain validation: {valid} ({reason})")
    blockchain.save(data_dir / "blockchain.json")
    print("Saved data/blockchain.json, data/attendees.json, and data/wallets/")


if __name__ == "__main__":
    main()