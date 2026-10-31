"""Interactive command-line application for the conference registration system."""

from pathlib import Path

from conference_registration import AttendeeActor, Blockchain, MinerActor, OrganizerActor


DATA_DIR = Path("data")


def print_role_menu() -> None:
    print(
        """
=== Conference Registration System ===
1. Attendee menu
2. Conference organizer menu
0. Exit
"""
    )


def print_attendee_menu() -> None:
    print(
        """
=== Attendee Menu ===
1. Register attendee account
2. Submit session check-in
3. View personal attendance history
0. Back to role selection
"""
    )


def print_conference_menu() -> None:
    print(
        """
=== Conference Organizer Menu ===
1. Mine pending transactions
2. View pending transactions
3. View registered attendees
4. Query sessions for attendee
5. Query attendees in session
6. Query registration status
7. Query attendees absent from session
8. View attendance statistics
9. Validate blockchain
0. Back to role selection
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
    if choice == "3":
        for attendee in organizer.registered_attendees():
            print(f"{attendee['attendee_id']} | {attendee['name']} | {attendee['email']} | {attendee['status']}")
    elif choice == "4":
        attendee_id = input("Enter attendee ID: ").strip()
        print("Sessions:", organizer.sessions_for_participant(attendee_id))
    elif choice == "5":
        session_id = input("Enter session ID: ").strip()
        print("Attendees:", organizer.participants_in_session(session_id))
    elif choice == "6":
        attendee_id = input("Enter attendee ID: ").strip()
        print("Registration status:", organizer.registration_status(attendee_id))
    elif choice == "7":
        session_id = input("Enter session ID: ").strip()
        print("Attendees absent:", organizer.participants_not_in_session(session_id))
    elif choice == "8":
        print("Attendance statistics:", organizer.attendance_statistics())


def attendee_menu(blockchain: Blockchain, attendee_sessions: dict[str, AttendeeActor]) -> None:
    while True:
        print_attendee_menu()
        choice = input("Attendee option: ").strip()
        if choice == "0":
            return
        if choice == "1":
            register_attendee(blockchain, attendee_sessions)
        elif choice == "2":
            attendee_check_in(blockchain, attendee_sessions)
        elif choice == "3":
            view_history(attendee_sessions)
        else:
            print("Invalid option. Please choose a number from the menu.")


def conference_menu(blockchain: Blockchain, miner: MinerActor, organizer: OrganizerActor) -> None:
    while True:
        print_conference_menu()
        choice = input("Conference option: ").strip()
        if choice == "0":
            return
        if choice == "1":
            mine_transactions(miner)
        elif choice == "2":
            pending = miner.pending_transactions()
            print(f"Pending transactions: {len(pending)}")
            for transaction in pending:
                print(transaction)
        elif choice in {"3", "4", "5", "6", "7", "8"}:
            organizer_queries(organizer, choice)
        elif choice == "9":
            valid, reason = miner.validate_chain()
            print(f"Blockchain valid: {valid} ({reason})")
        else:
            print("Invalid option. Please choose a number from the menu.")


def main() -> None:
    blockchain = Blockchain(initial_difficulty=2)
    miner = MinerActor(blockchain, "interactive-miner")
    organizer = OrganizerActor(blockchain)
    attendee_sessions: dict[str, AttendeeActor] = {}

    while True:
        print_role_menu()
        role = input("Select a user role: ").strip()
        if role == "0":
            print("Goodbye.")
            return
        if role == "1":
            attendee_menu(blockchain, attendee_sessions)
        elif role == "2":
            conference_menu(blockchain, miner, organizer)
        else:
            print("Invalid role. Choose Attendee, Conference organizer, or Exit.")


if __name__ == "__main__":
    main()