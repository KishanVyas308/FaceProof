"""Layer 7: Ethereum Sepolia Blockchain Client using web3.py."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from web3 import Web3
from web3.exceptions import Web3Exception

from config.settings import (
    BASE_DIR,
    CONTRACT_ADDRESS,
    SEPOLIA_EXPLORER_TX_URL,
    SEPOLIA_RPC_URL,
    SIMULATE_BLOCKCHAIN,
    WALLET_PRIVATE_KEY
)
from utils.hashing import hex_to_bytes32, hash_string


class BlockchainError(Exception):
    """Base exception for blockchain interactions."""
    pass


class RPCConnectionError(BlockchainError):
    """Raised when Ethereum RPC is unreachable."""
    pass


class WalletConfigurationError(BlockchainError):
    """Raised when private key or wallet config is invalid."""
    pass


class InsufficientGasError(BlockchainError):
    """Raised when wallet does not have sufficient Sepolia ETH."""
    pass


class TransactionExecutionError(BlockchainError):
    """Raised when transaction execution or confirmation fails."""
    pass


def load_contract_spec() -> Tuple[str, list]:
    """Loads contract ABI and address from config/contract.json."""
    spec_path = BASE_DIR / "config" / "contract.json"
    if not spec_path.is_file():
        raise BlockchainError(f"Contract specification file not found: {spec_path}")

    with open(spec_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    abi = data.get("abi", [])
    address = CONTRACT_ADDRESS or data.get("default_address", "")
    return address, abi


class SepoliaClient:
    """Manages transactions and interactions with the VerificationRegistry contract on Sepolia."""

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        contract_address: Optional[str] = None,
        simulate: Optional[bool] = None
    ):
        self.rpc_url = rpc_url or SEPOLIA_RPC_URL
        self.private_key = private_key or WALLET_PRIVATE_KEY
        self.simulate = SIMULATE_BLOCKCHAIN if simulate is None else simulate

        address_from_spec, self.abi = load_contract_spec()
        self.contract_address = contract_address or address_from_spec

        self.w3: Optional[Web3] = None
        self.account = None

        if not self.simulate:
            self._initialize_web3()

    def _initialize_web3(self) -> None:
        if not self.rpc_url or "YOUR_API_KEY" in self.rpc_url:
            raise RPCConnectionError(
                "SEPOLIA_RPC_URL is not set or contains default placeholder. "
                "Set SEPOLIA_RPC_URL in .env or enable SIMULATE_BLOCKCHAIN=true for offline testing."
            )

        try:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 20}))
            if not self.w3.is_connected():
                raise RPCConnectionError(f"Cannot connect to Sepolia RPC endpoint: {self.rpc_url}")
        except Exception as e:
            raise RPCConnectionError(f"Failed to connect to Sepolia RPC: {e}")

        if not self.private_key or self.private_key.startswith("0x000000"):
            raise WalletConfigurationError(
                "WALLET_PRIVATE_KEY is not configured or uses placeholder. "
                "Please configure a dedicated testnet wallet private key in .env."
            )

        try:
            self.account = self.w3.eth.account.from_key(self.private_key)
        except Exception as e:
            raise WalletConfigurationError(f"Invalid private key format: {e}")

        if not self.contract_address or self.contract_address == "0x0000000000000000000000000000000000000000":
            raise BlockchainError(
                "CONTRACT_ADDRESS is not configured. Deploy contracts/VerificationRegistry.sol to Sepolia "
                "and set CONTRACT_ADDRESS in .env or config/contract.json."
            )

    def submit_record_hash(
        self,
        record_hash_hex: str,
        metadata_str: str = ""
    ) -> Tuple[str, str]:
        """
        Submits the SHA-256 verification record hash to the Sepolia smart contract.

        Returns:
            (tx_hash, explorer_url)
        """
        # If simulation mode is explicitly enabled
        if self.simulate:
            fake_tx_hash = "0x" + hash_string(f"sim_{record_hash_hex}_{metadata_str}")
            explorer_url = f"{SEPOLIA_EXPLORER_TX_URL}{fake_tx_hash}"
            return fake_tx_hash, explorer_url

        record_bytes32 = hex_to_bytes32(record_hash_hex)
        checksum_address = Web3.to_checksum_address(self.contract_address)
        contract = self.w3.eth.contract(address=checksum_address, abi=self.abi)

        # Check balance for gas
        try:
            balance = self.w3.eth.get_balance(self.account.address)
        except Exception as e:
            raise RPCConnectionError(f"Failed to fetch wallet balance: {e}")

        if balance == 0:
            raise InsufficientGasError(
                f"Wallet {self.account.address} has 0 Sepolia ETH. "
                "Please request testnet ETH from a Sepolia faucet (e.g. sepoliafaucet.com)."
            )

        # Build transaction
        try:
            nonce = self.w3.eth.get_transaction_count(self.account.address, "pending")
            chain_id = self.w3.eth.chain_id

            # Estimate gas or use default limit
            tx_data = contract.functions.submitVerification(
                record_bytes32,
                metadata_str
            ).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "chainId": chain_id,
            })

            # Check if estimated gas cost exceeds balance
            gas_price = self.w3.eth.gas_price
            estimated_cost = tx_data.get("gas", 100000) * gas_price
            if balance < estimated_cost:
                raise InsufficientGasError(
                    f"Insufficient Sepolia ETH for gas. Balance: {Web3.from_wei(balance, 'ether')} ETH, "
                    f"Required ~{Web3.from_wei(estimated_cost, 'ether')} ETH."
                )

            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx_data, private_key=self.private_key)

            # Broadcast transaction
            raw_tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = raw_tx_hash.hex()
            if not tx_hash.startswith("0x"):
                tx_hash = f"0x{tx_hash}"

            # Await confirmation receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(raw_tx_hash, timeout=180)

            if receipt.status != 1:
                raise TransactionExecutionError(f"Transaction reverted on Sepolia. Status={receipt.status}")

            explorer_url = f"{SEPOLIA_EXPLORER_TX_URL}{tx_hash}"
            return tx_hash, explorer_url

        except Web3Exception as we:
            raise TransactionExecutionError(f"Web3 transaction error: {we}")
        except Exception as e:
            if isinstance(e, (InsufficientGasError, RPCConnectionError, WalletConfigurationError)):
                raise
            raise TransactionExecutionError(f"Unexpected transaction failure: {e}")

    def lookup_transaction(self, tx_hash_hex: str) -> Dict[str, Any]:
        """
        Looks up an on-chain transaction receipt on Sepolia and decodes verification event if present.
        """
        if self.simulate:
            return {
                "tx_hash": tx_hash_hex,
                "status": "Simulated Success",
                "block_number": 9999999,
                "network": "Ethereum Sepolia (Simulated)"
            }

        if not self.w3:
            self._initialize_web3()

        try:
            tx = self.w3.eth.get_transaction(tx_hash_hex)
            receipt = self.w3.eth.get_transaction_receipt(tx_hash_hex)
            return {
                "tx_hash": tx_hash_hex,
                "from": tx["from"],
                "to": tx["to"],
                "block_number": receipt["blockNumber"],
                "status": "Confirmed (Success)" if receipt["status"] == 1 else "Reverted",
                "gas_used": receipt["gasUsed"],
                "explorer_url": f"{SEPOLIA_EXPLORER_TX_URL}{tx_hash_hex}"
            }
        except Exception as e:
            raise BlockchainError(f"Could not retrieve transaction {tx_hash_hex}: {e}")
