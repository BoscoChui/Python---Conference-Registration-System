# Conference Registration System

A command-line, blockchain-based conference registration system for DSAI 4202. It demonstrates RSA attendee identities, signed attendance certificates, SHA-256 linked blocks, proof-of-work, dynamic difficulty adjustment, organizer queries, duplicate prevention, rewards, validation, and JSON persistence.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Demonstration

```powershell
python demo.py
```

For live user input, run the interactive application:

```powershell
python app.py
```

The interactive menu lets attendees register and check in, lets the miner inspect and mine pending transactions, and lets the organizer run all required queries. Use option `2` after registration or check-in to confirm transactions and store them in a block. Use option `0` to exit.

The demo creates `data/blockchain.json`, `data/attendees.json`, and `data/wallets/`. The blockchain and attendee files contain public keys only; private RSA keys are kept in individual wallet PEM files and are never included in transactions or blocks.

## Tests

```powershell
python -m pytest -q
```

## Architecture

- `Wallet`: creates RSA key pairs, stores individual private-key PEM files, and signs attendance certificates. Private keys remain outside the blockchain.
- `Attendee`: registration data and the public key published on-chain.
- `Block`: canonical JSON hashing, nonce search, and proof-of-work.
- `Blockchain`: pending pool, signature checks, mining rewards, chain validation, dynamic difficulty, queries, and persistence.
- `AttendeeActor`: student-facing registration, check-in, and personal-history workflow.
- `MinerActor`: system-facing pending-pool inspection, signature verification, mining, and validation workflow.
- `OrganizerActor`: teacher-facing registered-attendee, attendance, status, and statistics queries.
- `demo.py`: presentation/demo script.
- `app.py`: interactive CLI where users enter information through a menu.

## Actors and Permissions

| Actor | Main responsibility | Allowed interactions |
| --- | --- | --- |
| Attendee (student) | Own identity and attendance | Register, create signed check-in certificates, view personal attendance history |
| Miner/system | Process transactions and protect the ledger | Inspect pending transactions, verify signatures, mine blocks, adjust difficulty, validate the chain |
| Organizer/teacher | Read conference records | View attendees, query attendance, check status, find absences, view statistics |

The actor classes are application roles, not separate blockchain nodes. They call the same `Blockchain` service, while the service remains the single owner of transaction validation and ledger mutation.

## End-to-End Workflows

### 1. Attendee Registration

**Input:** attendee name and email. An ID is generated automatically, for example `A001`.

**Processing:** `AttendeeActor.register()` validates a non-empty name and email format, checks email and ID uniqueness, asks `Wallet` to generate an RSA key pair, saves the private key to `wallets/A001.pem`, and creates a registration transaction.

**Transaction added to pending pool:**

```json
{
	"type": "registration",
	"attendee_id": "A001",
	"name": "Alice",
	"email": "alice@example.com",
	"public_key": "-----BEGIN RSA PUBLIC KEY-----...",
	"timestamp": "..."
}
```

The private key is never included in the transaction. `MinerActor.mine()` packages the pending registration into a proof-of-work block. After mining, `OrganizerActor.registered_attendees()` displays the on-chain record.

**Expected output:** `Registration transaction created and added to pending pool`, followed by a mined registration block and status `Registered`.

**Errors:** empty name, invalid email, duplicate email, duplicate attendee ID, invalid ID format, or an existing wallet key produce a clear `ValueError` and no accepted registration.

### 2. Session Check-in

**Input:** an attendee's session ID.

**Processing:** `AttendeeActor.check_in()` creates a certificate containing `attendee_id`, `session_id`, and a UTC timestamp. The attendee wallet signs the canonical JSON certificate with the private RSA key. The signed attendance transaction is added to the pending pool.

**Transaction added to pending pool:**

```json
{
	"type": "attendance",
	"attendee_id": "A001",
	"session_id": "S101",
	"timestamp": "...",
	"signature": "..."
}
```

`MinerActor.verify_pending_attendance()` checks each signature against the public key stored in the registration transaction. `MinerActor.mine()` includes only valid attendance records in a new block. `Blockchain.validate()` checks the stored signature again when validating the complete chain.

**Expected output:** `Signed attendance certificate added to pending pool`, then a verification count such as `{'valid_attendance': 1, 'invalid_attendance': 0}`, followed by a mined attendance block.

**Errors:** an attendee cannot check in before registration is mined, an empty session ID is rejected, duplicate attendance for the same attendee and session is rejected, and a tampered certificate fails verification and is not mined.

### 3. Organizer Queries

**Input:** an attendee ID or session ID, depending on the query.

**Processing:** `OrganizerActor` searches confirmed blockchain transactions and returns read-only results.

| Query | Input | Output |
| --- | --- | --- |
| Registered attendees | None | ID, name, email, public key, and `Registered` status |
| Sessions for participant | `attendee_id` | List of session IDs |
| Participants in session | `session_id` | List of attendee IDs |
| Registration status | `attendee_id` | `registered` or `not registered` |
| Participants not in session | `session_id` | Registered IDs without an attendance record for that session |
| Attendance statistics | None | Registration count, attendance count, unique sessions, unique attendees |

**Expected output:** formatted lists and dictionaries suitable for command-line demonstration. Unknown IDs return an empty result or `not registered`; they do not modify the blockchain.

### 4. Miner/System Workflow

The miner workflow is: inspect pending pool, verify attendance signatures, discard invalid attendance transactions, add a reward transaction, mine by incrementing `nonce` until `hash.startswith("0" * difficulty)`, append the block, and validate the chain. Every 10 mined blocks, elapsed block time is compared with the target interval of 10 seconds. Difficulty increases when mining is substantially faster and decreases when substantially slower, never below 1. The next block receives the adjusted difficulty so already-mined block hashes remain immutable.

## Demonstration Sequence

`demo.py` follows the same sequence used in the presentation:

1. Create three attendee actors and register them.
2. Show generated IDs and pending registration transactions.
3. Let the miner mine the registration block.
4. Save `data/attendees.json` and individual wallet files.
5. Submit three signed check-ins and show miner verification counts.
6. Attempt a tampered certificate and show `False` verification.
7. Mine the attendance block.
8. Run all organizer queries and display statistics.
9. Validate the blockchain and save `data/blockchain.json`.

## Rubric coverage

The two required queries are `sessions_attended_by()` and `attendees_in_session()`. Additional queries are `registered_not_in_session()` and `registration_status()`. Difficulty is recalculated every 10 mined blocks using a 10-second target per block, with a minimum difficulty of 1. The demo prints the difficulty history and validation result.

Attendee registration is exposed through `register_attendee()`. It generates IDs such as `A001`, validates the name and email, rejects duplicate IDs/emails, saves the private key in `wallets/`, queues a registration transaction containing the public key, and supports `get_public_key()`, `list_attendees()`, and `save_attendees()`.

## Security notes

This is a teaching model, not production blockchain software. RSA keys are generated for demonstration, wallet PEM files are not encrypted, and the chain is local rather than distributed. Real systems need encrypted key storage, access control, consensus, replay protection, and operational key management.

## Five-slide presentation outline

1. **Goal and architecture**: attendee, wallet, pending pool, miner, blockchain.
2. **Identity and attendance**: RSA public/private keys and the signed certificate fields.
3. **Block and mining**: SHA-256 links, nonce search, reward transaction, and validation.
4. **Dynamic difficulty and queries**: adjustment interval, target time, and organizer queries.
5. **Live results**: run the demo, show tamper rejection, query output, JSON files, and tests.

## Report outline

1. **Project overview**: objective and requirements implemented.
2. **System design**: wallet, transaction model, block structure, signature verification, and proof-of-work.
3. **Dynamic difficulty**: target interval, adjustment rule, lower bound, and observed history.
4. **Testing and results**: valid attendance, tampered attendance rejection, duplicate prevention, validation, persistence, and query output.
5. **Limitations and contributions**: educational scope, security limitations, and individual contribution.