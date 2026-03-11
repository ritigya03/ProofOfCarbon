"""
tools/blockchain.py — On-chain interaction with VerificationRegistry contract.

Provides helpers to:
  • log_verification_to_chain()  — write a new record (Stage 5 of the pipeline)
  • read_records_from_chain()    — paginated read for /audits endpoint
  • read_record_from_chain()     — single record by ID

Uses Python web3.py and the contract ABI from deployed.json.
Falls back gracefully when blockchain env vars are not configured.
"""

import json
import logging
import os
import pathlib
from typing import Optional

from web3 import Web3

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent  # ProofOfCarbon/
_DEPLOYED_JSON = _ROOT / "blockchain" / "deployed.json"

# ── Risk-level mapping ────────────────────────────────────────────────────────

RISK_ENUM = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
RISK_ENUM_REVERSE = {v: k for k, v in RISK_ENUM.items()}

# ── Lazy singleton ────────────────────────────────────────────────────────────

_w3: Optional[Web3] = None
_contract = None
_account = None
_chain_id: Optional[int] = None


def _load_deployed_json() -> dict:
    """Read ABI + address from blockchain/deployed.json."""
    if not _DEPLOYED_JSON.exists():
        raise FileNotFoundError(f"deployed.json not found at {_DEPLOYED_JSON}")
    with open(_DEPLOYED_JSON, "r") as f:
        return json.load(f)


def _init():
    """Initialise Web3 connection, contract instance, and signer account."""
    global _w3, _contract, _account, _chain_id

    if _w3 is not None:
        return  # already initialised

    rpc_url = os.getenv("RPC_URL", "").strip()
    private_key = os.getenv("PRIVATE_KEY", "").strip()
    contract_addr = os.getenv("CONTRACT_ADDRESS", "").strip()

    if not rpc_url or not private_key or private_key.startswith("your_"):
        raise EnvironmentError(
            "Blockchain env vars not configured (RPC_URL / PRIVATE_KEY). "
            "Blockchain write will be skipped."
        )

    deployed = _load_deployed_json()
    abi = deployed["abi"]

    # Use CONTRACT_ADDRESS env var if set; otherwise fall back to deployed.json
    if not contract_addr or contract_addr.startswith("your_"):
        contract_addr = deployed["address"]

    _chain_id = deployed.get("chainId", 80002)

    _w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not _w3.is_connected():
        raise ConnectionError(f"Cannot connect to RPC at {rpc_url}")

    _contract = _w3.eth.contract(
        address=Web3.to_checksum_address(contract_addr),
        abi=abi,
    )

    _account = _w3.eth.account.from_key(private_key)
    logger.info(
        f"Blockchain ready — contract={contract_addr[:10]}…, "
        f"signer={_account.address[:10]}…, chain={_chain_id}"
    )


# ── Write: log verification ──────────────────────────────────────────────────


def log_verification_to_chain(
    project_name: str,
    company_name: str,
    trust_score: int,
    risk_level: str,
    ipfs_hash: str = "",
) -> dict:
    """
    Call VerificationRegistry.logVerification() on-chain.

    Returns:
        {
            "tx_hash": "0x...",
            "record_id": <int>,
            "block_number": <int>,
            "chain_id": <int>,
            "contract_address": "0x..."
        }

    Raises EnvironmentError if blockchain is not configured.
    """
    _init()

    risk_val = RISK_ENUM.get(risk_level.upper(), 1)  # default MEDIUM
    score = max(0, min(100, int(trust_score)))

    nonce = _w3.eth.get_transaction_count(_account.address)

    tx = _contract.functions.logVerification(
        project_name,
        company_name,
        score,
        risk_val,
        ipfs_hash,
    ).build_transaction(
        {
            "from": _account.address,
            "nonce": nonce,
            "chainId": _chain_id,
            "gas": 500_000,
            "maxFeePerGas": _w3.to_wei("35", "gwei"),
            "maxPriorityFeePerGas": _w3.to_wei("30", "gwei"),
        }
    )

    signed = _w3.eth.account.sign_transaction(tx, _account.key)
    tx_hash = _w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = _w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    # Decode the returned record ID from the transaction logs
    record_id = None
    try:
        logs = _contract.events.VerificationLogged().process_receipt(receipt)
        if logs:
            record_id = logs[0]["args"]["id"]
    except Exception:
        pass

    result = {
        "tx_hash": receipt.transactionHash.hex(),
        "record_id": record_id,
        "block_number": receipt.blockNumber,
        "chain_id": _chain_id,
        "contract_address": _contract.address,
    }
    logger.info(f"✅ On-chain verification logged: tx={result['tx_hash'][:16]}…")
    return result


# ── Read: fetch records ──────────────────────────────────────────────────────


def _init_readonly():
    """Light init — read-only, no private key required."""
    global _w3, _contract, _chain_id

    if _contract is not None:
        return

    rpc_url = os.getenv("RPC_URL", "https://rpc-amoy.polygon.technology").strip()
    deployed = _load_deployed_json()
    contract_addr = os.getenv("CONTRACT_ADDRESS", "").strip()
    if not contract_addr or contract_addr.startswith("your_"):
        contract_addr = deployed["address"]

    _chain_id = deployed.get("chainId", 80002)
    _w3 = Web3(Web3.HTTPProvider(rpc_url))
    _contract = _w3.eth.contract(
        address=Web3.to_checksum_address(contract_addr),
        abi=deployed["abi"],
    )


def read_total_records() -> int:
    """Return totalRecords() from the contract."""
    _init_readonly()
    return _contract.functions.totalRecords().call()


def read_records_from_chain(offset: int = 0, limit: int = 50) -> list[dict]:
    """
    Call getRecords(offset, limit) and return a list of dicts.
    """
    _init_readonly()
    raw = _contract.functions.getRecords(offset, limit).call()

    records = []
    for r in raw:
        records.append(
            {
                "id": r[0],
                "project_name": r[1],
                "company_name": r[2],
                "trust_score": r[3],
                "risk_level": RISK_ENUM_REVERSE.get(r[4], "MEDIUM"),
                "ipfs_hash": r[5],
                "verifier": r[6],
                "timestamp": r[7],
            }
        )
    return records


def read_record_from_chain(record_id: int) -> dict:
    """Fetch a single record by ID."""
    _init_readonly()
    r = _contract.functions.getRecord(record_id).call()
    return {
        "id": r[0],
        "project_name": r[1],
        "company_name": r[2],
        "trust_score": r[3],
        "risk_level": RISK_ENUM_REVERSE.get(r[4], "MEDIUM"),
        "ipfs_hash": r[5],
        "verifier": r[6],
        "timestamp": r[7],
    }
