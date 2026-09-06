#!/usr/bin/env python3
"""
Deploy VerificationRegistry.sol directly to Ethereum Sepolia.
Reads WALLET_PRIVATE_KEY and SEPOLIA_RPC_URL from .env,
deploys the contract, and updates .env and config/contract.json automatically.
"""

import json
import re
import sys
from pathlib import Path
from web3 import Web3

from config.settings import BASE_DIR, SEPOLIA_RPC_URL, WALLET_PRIVATE_KEY


def deploy():
    print("=== VerificationRegistry 1-Click Deployer ===")

    if not SEPOLIA_RPC_URL or "YOUR_API_KEY" in SEPOLIA_RPC_URL:
        print("[ERROR] SEPOLIA_RPC_URL is not set in .env.")
        print("Set SEPOLIA_RPC_URL=https://ethereum-sepolia-rpc.publicnode.com in .env")
        sys.exit(1)

    if not WALLET_PRIVATE_KEY or WALLET_PRIVATE_KEY.startswith("0x000000"):
        print("[ERROR] WALLET_PRIVATE_KEY is not set in .env.")
        print("Set your funded MetaMask private key in .env first.")
        sys.exit(1)

    # Load contract spec
    spec_path = BASE_DIR / "config" / "contract.json"
    with open(spec_path, "r") as f:
        spec = json.load(f)

    abi = spec["abi"]
    bytecode = spec.get("bytecode")
    if not bytecode:
        print("[ERROR] Bytecode not found in config/contract.json.")
        sys.exit(1)

    # Connect to Sepolia
    print(f"Connecting to Sepolia RPC: {SEPOLIA_RPC_URL[:40]}...")
    w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
    if not w3.is_connected():
        print("[ERROR] Could not connect to RPC endpoint.")
        sys.exit(1)

    account = w3.eth.account.from_key(WALLET_PRIVATE_KEY)
    balance_wei = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance_wei, "ether")
    print(f"Deployer Wallet Address: {account.address}")
    print(f"Wallet Balance: {balance_eth:.4f} Sepolia ETH")

    if balance_wei == 0:
        print("[ERROR] Wallet has 0 Sepolia ETH. Please get free test ETH from sepoliafaucet.com.")
        sys.exit(1)

    print("\nBuilding contract deployment transaction...")
    ContractFactory = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(account.address, "pending")
    chain_id = w3.eth.chain_id

    tx_data = ContractFactory.constructor().build_transaction({
        "from": account.address,
        "nonce": nonce,
        "chainId": chain_id,
        "gasPrice": w3.eth.gas_price
    })

    print("Signing transaction with wallet private key...")
    signed_tx = w3.eth.account.sign_transaction(tx_data, private_key=WALLET_PRIVATE_KEY)

    print("Broadcasting transaction to Ethereum Sepolia...")
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_hash_hex = tx_hash.hex()
    if not tx_hash_hex.startswith("0x"):
        tx_hash_hex = f"0x{tx_hash_hex}"
    print(f"Transaction broadcast: https://sepolia.etherscan.io/tx/{tx_hash_hex}")
    print("Waiting for on-chain block confirmation (takes ~15s)...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt.status != 1:
        print("[ERROR] Deployment transaction reverted on-chain.")
        sys.exit(1)

    deployed_address = receipt.contractAddress
    print(f"\n=======================================================")
    print(f"SUCCESS! VerificationRegistry Deployed To:")
    print(f"{deployed_address}")
    print(f"View on Etherscan: https://sepolia.etherscan.io/address/{deployed_address}")
    print(f"=======================================================\n")

    # Update config/contract.json
    spec["default_address"] = deployed_address
    with open(spec_path, "w") as f:
        json.dump(spec, f, indent=2)
    print("Updated config/contract.json with deployed address.")

    # Update .env
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        content = env_path.read_text()
        if "CONTRACT_ADDRESS=" in content:
            new_content = re.sub(r"CONTRACT_ADDRESS=.*", f"CONTRACT_ADDRESS={deployed_address}", content)
        else:
            new_content = content + f"\nCONTRACT_ADDRESS={deployed_address}\n"
        env_path.write_text(new_content)
        print("Updated .env with CONTRACT_ADDRESS.")

    print("\nDeployment complete! You can now run:")
    print("python main.py --image image.png")


if __name__ == "__main__":
    deploy()
