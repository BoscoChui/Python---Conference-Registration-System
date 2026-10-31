from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import rsa


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass
class Attendee:
    attendee_id: str
    name: str
    email: str
    public_key: str


@dataclass
class Block:
    index: int
    timestamp: str
    transactions: list[dict[str, Any]]
    previous_hash: str
    nonce: int
    difficulty: int
    hash: str = ""

    def content(self) -> dict[str, Any]:
        return {"index": self.index, "timestamp": self.timestamp, "transactions": self.transactions, "previous_hash": self.previous_hash, "nonce": self.nonce, "difficulty": self.difficulty}

    def calculate_hash(self) -> str:
        return sha256_text(canonical_json(self.content()))

    def mine(self) -> int:
        attempts = 0
        prefix = "0" * self.difficulty
        while True:
            self.hash = self.calculate_hash()
            attempts += 1
            if self.hash.startswith(prefix):
                return attempts
            self.nonce += 1


class Wallet:
    """An attendee wallet containing private keys, never blockchain data."""

    def __init__(self) -> None:
        self._private_keys: dict[str, rsa.PrivateKey] = {}

    def create_key_pair(self, attendee_id: str, bits: int = 1024) -> str:
        if attendee_id in self._private_keys:
            raise ValueError(f"Wallet already contains {attendee_id}")
        public_key, private_key = rsa.newkeys(bits)
        self._private_keys[attendee_id] = private_key
        return public_key.save_pkcs1().decode("ascii")

    def sign(self, attendee_id: str, payload: str) -> str:
        private_key = self._private_keys.get(attendee_id)
        if private_key is None:
            raise ValueError(f"No private key for {attendee_id}")
        return rsa.sign(payload.encode("utf-8"), private_key, "SHA-256").hex()

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        contents = {attendee_id: key.save_pkcs1().decode("ascii") for attendee_id, key in self._private_keys.items()}
        path.write_text(json.dumps(contents, indent=2), encoding="utf-8")

    def save_attendee_wallet(self, attendee_id: str, directory: str | Path = "wallets") -> Path:
        """Persist one attendee's private key separately from blockchain data."""
        private_key = self._private_keys.get(attendee_id)
        if private_key is None:
            raise ValueError(f"No private key for {attendee_id}")
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{attendee_id}.pem"
        path.write_bytes(private_key.save_pkcs1())
        return path


class Blockchain:
    TARGET_BLOCK_TIME = 10.0
    ADJUSTMENT_INTERVAL = 10
    MAX_DIFFICULTY = 6

    def __init__(self, initial_difficulty: int = 2, miner_reward: int = 10) -> None:
        if initial_difficulty < 1:
            raise ValueError("Initial difficulty must be at least 1")
        self.miner_reward = miner_reward
        self.pending_transactions: list[dict[str, Any]] = []
        self.difficulty_history: list[dict[str, Any]] = []
        self.next_difficulty = initial_difficulty
        self.chain: list[Block] = [self._create_genesis_block(initial_difficulty)]

    def _create_genesis_block(self, difficulty: int) -> Block:
        block = Block(0, utc_timestamp(), [], "0" * 64, 0, difficulty)
        block.mine()
        return block

    @property
    def latest_block(self) -> Block:
        return self.chain[-1]

    def _registered_attendee(self, attendee_id: str) -> dict[str, Any] | None:
        for block in self.chain:
            for transaction in block.transactions:
                if transaction.get("type") == "registration" and transaction.get("attendee_id") == attendee_id:
                    return transaction
        return None

    def _attendance_records(self) -> list[dict[str, Any]]:
        return [transaction for block in self.chain for transaction in block.transactions if transaction.get("type") == "attendance"]

    def _registration_transactions(self, include_pending: bool = True) -> list[dict[str, Any]]:
        transactions = [transaction for block in self.chain for transaction in block.transactions if transaction.get("type") == "registration"]
        if include_pending:
            transactions.extend(transaction for transaction in self.pending_transactions if transaction.get("type") == "registration")
        return transactions

    def _next_attendee_id(self) -> str:
        used_ids = {transaction["attendee_id"] for transaction in self._registration_transactions()}
        number = 1
        while f"A{number:03d}" in used_ids:
            number += 1
        return f"A{number:03d}"

    def register_attendee(
        self,
        wallet: Wallet,
        name: str,
        email: str,
        wallet_directory: str | Path = "wallets",
        attendee_id: str | None = None,
    ) -> dict[str, Any]:
        """Create an identity, save its private key, and queue its public identity."""
        name = name.strip()
        email = email.strip().lower()
        if not name:
            raise ValueError("Registration failed: name cannot be empty")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Registration failed: invalid email format")
        existing = self._registration_transactions()
        if any(transaction.get("email", "").lower() == email for transaction in existing):
            raise ValueError("Registration failed: email already registered")
        attendee_id = attendee_id or self._next_attendee_id()
        if not re.fullmatch(r"A\d{3,}", attendee_id):
            raise ValueError("Registration failed: attendee ID must look like A001")
        if any(transaction.get("attendee_id") == attendee_id for transaction in existing):
            raise ValueError("Registration failed: attendee ID already registered")
        public_key = wallet.create_key_pair(attendee_id)
        wallet_path = wallet.save_attendee_wallet(attendee_id, wallet_directory)
        try:
            transaction = self.add_registration(Attendee(attendee_id, name, email, public_key))
        except Exception:
            wallet_path.unlink(missing_ok=True)
            raise
        return transaction

    def add_registration(self, attendee: Attendee) -> dict[str, Any]:
        if not attendee.name.strip():
            raise ValueError("Registration failed: name cannot be empty")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", attendee.email.strip()):
            raise ValueError("Registration failed: invalid email format")
        if self._registered_attendee(attendee.attendee_id) is not None:
            raise ValueError(f"Attendee {attendee.attendee_id} is already registered")
        if any(transaction.get("type") == "registration" and transaction.get("attendee_id") == attendee.attendee_id for transaction in self.pending_transactions):
            raise ValueError(f"Attendee {attendee.attendee_id} is already pending")
        if any(transaction.get("email", "").lower() == attendee.email.strip().lower() for transaction in self._registration_transactions()):
            raise ValueError("Registration failed: email already registered")
        transaction = {"type": "registration", **asdict(attendee), "timestamp": utc_timestamp()}
        self.pending_transactions.append(transaction)
        return transaction

    def create_attendance(self, wallet: Wallet, attendee_id: str, session_id: str) -> dict[str, Any]:
        if self._registered_attendee(attendee_id) is None:
            raise ValueError("Attendee must be registered on-chain before attending")
        records = self._attendance_records() + [transaction for transaction in self.pending_transactions if transaction.get("type") == "attendance"]
        if any(record.get("attendee_id") == attendee_id and record.get("session_id") == session_id for record in records):
            raise ValueError("Duplicate attendance is not allowed")
        certificate = {"attendee_id": attendee_id, "session_id": session_id, "timestamp": utc_timestamp()}
        return {"type": "attendance", **certificate, "signature": wallet.sign(attendee_id, canonical_json(certificate))}

    def add_attendance(self, record: dict[str, Any]) -> None:
        if record.get("type") != "attendance":
            raise ValueError("Only attendance records can be added with add_attendance")
        if self._registered_attendee(record.get("attendee_id", "")) is None:
            raise ValueError("Attendance signer is not registered")
        if not self.verify_attendance(record):
            raise ValueError("Attendance signature is invalid")
        records = self._attendance_records() + [transaction for transaction in self.pending_transactions if transaction.get("type") == "attendance"]
        if any(existing.get("attendee_id") == record.get("attendee_id") and existing.get("session_id") == record.get("session_id") for existing in records):
            raise ValueError("Duplicate attendance is not allowed")
        self.pending_transactions.append(record)

    def verify_attendance(self, record: dict[str, Any]) -> bool:
        attendee = self._registered_attendee(record.get("attendee_id", ""))
        required = {"type", "attendee_id", "session_id", "timestamp", "signature"}
        if attendee is None or not required.issubset(record):
            return False
        certificate = {"attendee_id": record["attendee_id"], "session_id": record["session_id"], "timestamp": record["timestamp"]}
        try:
            rsa.verify(canonical_json(certificate).encode("utf-8"), bytes.fromhex(record["signature"]), rsa.PublicKey.load_pkcs1(attendee["public_key"].encode("ascii")))
            return True
        except (ValueError, IndexError, rsa.VerificationError):
            return False

    def mine_pending_transactions(self, miner_id: str = "miner") -> Block:
        valid_transactions: list[dict[str, Any]] = []
        for transaction in self.pending_transactions:
            if transaction.get("type") == "registration" or (transaction.get("type") == "attendance" and self.verify_attendance(transaction)):
                valid_transactions.append(transaction)
        valid_transactions.append({"type": "reward", "miner_id": miner_id, "amount": self.miner_reward})
        block = Block(len(self.chain), utc_timestamp(), valid_transactions, self.latest_block.hash, 0, self.next_difficulty)
        started = time.perf_counter()
        attempts = block.mine()
        elapsed = time.perf_counter() - started
        self.chain.append(block)
        self.pending_transactions = [transaction for transaction in self.pending_transactions if transaction not in valid_transactions]
        self._adjust_difficulty()
        self.difficulty_history.append({"block": block.index, "difficulty": block.difficulty, "attempts": attempts, "seconds": elapsed})
        return block

    def _adjust_difficulty(self) -> None:
        if len(self.chain) <= 1 or (len(self.chain) - 1) % self.ADJUSTMENT_INTERVAL != 0:
            return
        end_block = self.latest_block
        start_block = self.chain[-self.ADJUSTMENT_INTERVAL]
        elapsed = datetime.fromisoformat(end_block.timestamp).timestamp() - datetime.fromisoformat(start_block.timestamp).timestamp()
        expected = self.TARGET_BLOCK_TIME * self.ADJUSTMENT_INTERVAL
        old_difficulty = self.next_difficulty
        if elapsed < expected / 2:
            new_difficulty = min(old_difficulty + 1, self.MAX_DIFFICULTY)
        elif elapsed > expected * 2:
            new_difficulty = max(old_difficulty - 1, 1)
        else:
            new_difficulty = old_difficulty
        self.next_difficulty = new_difficulty
        self.difficulty_history.append({"adjustment_at_block": end_block.index, "old": old_difficulty, "new": new_difficulty, "elapsed": elapsed})

    def validate(self) -> tuple[bool, str]:
        for index, block in enumerate(self.chain):
            if block.hash != block.calculate_hash():
                return False, f"Block {block.index} hash does not match its contents"
            if not block.hash.startswith("0" * block.difficulty):
                return False, f"Block {block.index} does not satisfy proof of work"
            if index == 0 and block.previous_hash != "0" * 64:
                return False, "Genesis block has an invalid previous hash"
            if index > 0 and block.previous_hash != self.chain[index - 1].hash:
                return False, f"Block {block.index} is not linked to its predecessor"
            for transaction in block.transactions:
                if transaction.get("type") == "attendance" and not self.verify_attendance(transaction):
                    return False, f"Block {block.index} contains an invalid attendance signature"
        return True, "Blockchain is valid"

    def sessions_attended_by(self, attendee_id: str) -> list[str]:
        return sorted({record["session_id"] for record in self._attendance_records() if record["attendee_id"] == attendee_id})

    def attendees_in_session(self, session_id: str) -> list[str]:
        return sorted({record["attendee_id"] for record in self._attendance_records() if record["session_id"] == session_id})

    def registered_not_in_session(self, session_id: str) -> list[str]:
        registered = {transaction["attendee_id"] for block in self.chain for transaction in block.transactions if transaction.get("type") == "registration"}
        return sorted(registered - set(self.attendees_in_session(session_id)))

    def registration_status(self, attendee_id: str) -> str:
        return "registered" if self._registered_attendee(attendee_id) else "not registered"

    def get_public_key(self, attendee_id: str) -> str | None:
        attendee = next((transaction for transaction in self._registration_transactions() if transaction.get("attendee_id") == attendee_id), None)
        return attendee.get("public_key") if attendee else None

    def list_attendees(self, include_pending: bool = False) -> list[dict[str, Any]]:
        attendees = self._registration_transactions(include_pending=include_pending)
        return [
            {
                "attendee_id": attendee["attendee_id"],
                "name": attendee["name"],
                "email": attendee["email"],
                "public_key": attendee["public_key"],
                "status": "Registered" if attendee in self._registration_transactions(include_pending=False) else "Pending",
            }
            for attendee in attendees
        ]

    def save_attendees(self, path: str | Path = "attendees.json") -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.list_attendees(), indent=2), encoding="utf-8")

    def attendance_statistics(self) -> dict[str, Any]:
        records = self._attendance_records()
        sessions = {record["session_id"] for record in records}
        attendees = {record["attendee_id"] for record in records}
        registrations = sum(transaction.get("type") == "registration" for block in self.chain for transaction in block.transactions)
        return {"total_registrations": registrations, "total_attendance_records": len(records), "unique_sessions": len(sessions), "unique_attendees": len(attendees)}

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([asdict(block) for block in self.chain], indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Blockchain":
        blocks = json.loads(Path(path).read_text(encoding="utf-8"))
        if not blocks:
            raise ValueError("Blockchain file is empty")
        instance = cls.__new__(cls)
        instance.miner_reward = 10
        instance.pending_transactions = []
        instance.difficulty_history = []
        instance.chain = [Block(**block) for block in blocks]
        instance.next_difficulty = instance.latest_block.difficulty
        valid, reason = instance.validate()
        if not valid:
            raise ValueError(f"Cannot load invalid blockchain: {reason}")
        return instance


class AttendeeActor:
    """Student-facing workflow: register, check in, and view own history."""

    def __init__(self, blockchain: Blockchain, wallet: Wallet | None = None, wallet_directory: str | Path = "wallets") -> None:
        self.blockchain = blockchain
        self.wallet = wallet or Wallet()
        self.wallet_directory = Path(wallet_directory)
        self.attendee_id: str | None = None

    def register(self, name: str, email: str) -> dict[str, Any]:
        transaction = self.blockchain.register_attendee(self.wallet, name, email, self.wallet_directory)
        self.attendee_id = transaction["attendee_id"]
        return {
            "message": "Registration transaction created and added to pending pool",
            "attendee_id": self.attendee_id,
            "wallet_file": str(self.wallet_directory / f"{self.attendee_id}.pem"),
            "transaction": transaction,
        }

    def check_in(self, session_id: str) -> dict[str, Any]:
        if not self.attendee_id:
            raise ValueError("Check-in failed: register an attendee account first")
        if not session_id.strip():
            raise ValueError("Check-in failed: session ID cannot be empty")
        record = self.blockchain.create_attendance(self.wallet, self.attendee_id, session_id.strip())
        self.blockchain.add_attendance(record)
        return {"message": "Signed attendance certificate added to pending pool", "transaction": record}

    def attendance_history(self) -> list[str]:
        if not self.attendee_id:
            raise ValueError("Attendance history unavailable: register an attendee account first")
        return self.blockchain.sessions_attended_by(self.attendee_id)


class MinerActor:
    """Miner/system workflow: inspect, verify, mine, adjust, and validate."""

    def __init__(self, blockchain: Blockchain, miner_id: str = "miner") -> None:
        self.blockchain = blockchain
        self.miner_id = miner_id

    def pending_transactions(self) -> list[dict[str, Any]]:
        return list(self.blockchain.pending_transactions)

    def verify_pending_attendance(self) -> dict[str, int]:
        valid = sum(transaction.get("type") == "attendance" and self.blockchain.verify_attendance(transaction) for transaction in self.blockchain.pending_transactions)
        invalid = sum(transaction.get("type") == "attendance" and not self.blockchain.verify_attendance(transaction) for transaction in self.blockchain.pending_transactions)
        return {"valid_attendance": valid, "invalid_attendance": invalid}

    def mine(self) -> Block:
        return self.blockchain.mine_pending_transactions(self.miner_id)

    def validate_chain(self) -> tuple[bool, str]:
        return self.blockchain.validate()


class OrganizerActor:
    """Organizer workflow: read registered identities and attendance records."""

    def __init__(self, blockchain: Blockchain) -> None:
        self.blockchain = blockchain

    def registered_attendees(self) -> list[dict[str, Any]]:
        return self.blockchain.list_attendees()

    def sessions_for_participant(self, attendee_id: str) -> list[str]:
        return self.blockchain.sessions_attended_by(attendee_id)

    def participants_in_session(self, session_id: str) -> list[str]:
        return self.blockchain.attendees_in_session(session_id)

    def registration_status(self, attendee_id: str) -> str:
        return self.blockchain.registration_status(attendee_id)

    def participants_not_in_session(self, session_id: str) -> list[str]:
        return self.blockchain.registered_not_in_session(session_id)

    def attendance_statistics(self) -> dict[str, Any]:
        return self.blockchain.attendance_statistics()