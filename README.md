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

The demo creates `data/blockchain.json` and `data/wallet.json`. The blockchain file contains public keys only; private RSA keys are kept in the wallet file and are never included in transactions or blocks.

## Tests

```powershell
python -m pytest -q
```

## Architecture

- `Wallet`: creates RSA key pairs and signs attendance certificates. Private keys remain outside the blockchain.
- `Attendee`: registration data and the public key published on-chain.
- `Block`: canonical JSON hashing, nonce search, and proof-of-work.
- `Blockchain`: pending pool, signature checks, mining rewards, chain validation, dynamic difficulty, queries, and persistence.
- `demo.py`: presentation/demo script.

## Rubric coverage

The two required queries are `sessions_attended_by()` and `attendees_in_session()`. Additional queries are `registered_not_in_session()` and `registration_status()`. Difficulty is recalculated every 10 mined blocks using a 10-second target per block, with a minimum difficulty of 1. The demo prints the difficulty history and validation result.

## Security notes

This is a teaching model, not production blockchain software. RSA keys are generated for demonstration, JSON wallet storage is not encrypted, and the chain is local rather than distributed. Real systems need encrypted key storage, access control, consensus, replay protection, and operational key management.

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