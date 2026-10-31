"""Interactive command-line application for the conference registration system."""

from pathlib import Path

from conference_registration import AttendeeActor, Blockchain, MinerActor, OrganizerActor


DATA_DIR = Path("data")


def print_menu() -> None:
    print(
        """
=== Conference Registration System ===
1. Register attendee
2. Mine pending transactions
3. Attendee check-in
4. View attendee attendance history
5. View registered attendees
6. Query sessions for attendee
7. Query attendees in session
8. Query registration status
9. Query attendees absent from session
10. View attendance statistics
11. Validate blockchain
0. Exit
"""
    )


def register_attendee(blockchain: Blockchain, attendee_sessions: dict[str, AttendeeActor]) -> None:
    name = input("Enter attendee name: ")
    email = input("Enter attendee email: ")
    attendee = AttendeeActor(blockchain, wallet_directory=DATA_DIR / "wallets")
    try:
        result = attendee.register(name, email)
    except ValueError as error:
        print(f"Registration failed: {error}")
        return
    attendee_sessions[result["attendee_id"]] = attendee
    blockchain.save_attendees(DATA_DIR / "attendees.json")
    print(f"Registration successful. Attendee ID: {result['attendee_id']}")
    print(f"Private key wallet: {result['wallet_file']}")
    print("Registration transaction added to the pending pool.")


def mine_transactions(miner: MinerActor) -> None:
    pending_count = len(miner.pending_transactions())
    if pending_count == 0:
        print("No pending transactions to mine.")
        return
    print(f"Pending transactions: {pending_count}")
    print(f"Attendance verification: {miner.verify_pending_attendance()}")
    block = miner.mine()
    print(f"Block {block.index} mined successfully.")
    print(f"Hash: {block.hash}")
    print(f"Nonce: {block.nonce}; difficulty: {block.difficulty}")


def attendee_check_in(blockchain: Blockchain, attendee_sessions: dict[str, AttendeeActor]) -> None:
    attendee_id = input("Enter attendee ID: ").strip()
    session_id = input("Enter session ID: ").strip()
    attendee = attendee_sessions.get(attendee_id)
    if attendee is None:
        print("Check-in failed: attendee wallet is not loaded in this session.")
        print("Register the attendee through this application before checking in.")
        return
    try:
        result = attendee.check_in(session_id)
    except ValueError as error:
        print(error)
        return
    print(result["message"])
    print("Attendance transaction is waiting for miner verification and mining.")


def view_history(attendee_sessions: dict[str, AttendeeActor]) -> None:
    attendee_id = input("Enter attendee ID: ").strip()
    attendee = attendee_sessions.get(attendee_id)
    if attendee is None:
        print("No active attendee wallet found for that ID.")
        return
    print(f"{attendee_id} attendance history: {attendee.attendance_history()}")


def organizer_queries(organizer: OrganizerActor, choice: str) -> None:
    if choice == "5":
        for attendee in organizer.registered_attendees():
            print(f"{attendee['attendee_id']} | {attendee['name']} | {attendee['email']} | {attendee['status']}")
    elif choice == "6":
        attendee_id = input("Enter attendee ID: ").strip()
        print("Sessions:", organizer.sessions_for_participant(attendee_id))
    elif choice == "7":
        session_id = input("Enter session ID: ").strip()
        print("Attendees:", organizer.participants_in_session(session_id))
    elif choice == "8":
        attendee_id = input("Enter attendee ID: ").strip()
        print("Registration status:", organizer.registration_status(attendee_id))
    elif choice == "9":
        session_id = input("Enter session ID: ").strip()
        print("Attendees absent:", organizer.participants_not_in_session(session_id))
    elif choice == "10":
        print("Attendance statistics:", organizer.attendance_statistics())


def main() -> None:
    blockchain = Blockchain(initial_difficulty=2)
    miner = MinerActor(blockchain, "interactive-miner")
    organizer = OrganizerActor(blockchain)
    attendee_sessions: dict[str, AttendeeActor] = {}

    while True:
        print_menu()
        choice = input("Select an option: ").strip()
        if choice == "0":
            print("Goodbye.")
            return
        if choice == "1":
            register_attendee(blockchain, attendee_sessions)
        elif choice == "2":
            mine_transactions(miner)
        elif choice == "3":
            attendee_check_in(blockchain, attendee_sessions)
        elif choice == "4":
            view_history(attendee_sessions)
        elif choice in {"5", "6", "7", "8", "9", "10"}:
            organizer_queries(organizer, choice)
        elif choice == "11":
            valid, reason = miner.validate_chain()
            print(f"Blockchain valid: {valid} ({reason})")
        else:
            print("Invalid option. Please choose a number from the menu.")


if __name__ == "__main__":
    main()