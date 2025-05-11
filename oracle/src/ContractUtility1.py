import time
import sys
import traceback
import json
from pathlib import Path

from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
from sapphirepy import sapphire # Ensure this is installed in the ROFL env

print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ContractUtility.py loading...", flush=True)

class ContractUtility:
    """
    Handles Web3 setup, contract loading, and Sapphire integration.
    """
    def __init__(self, network_name: str, secret: str):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Initializing ContractUtility for network: {network_name}", flush=True)
        self.network_name = network_name
        self.w3 = self.setup_web3_middleware(secret)
        if self.w3 and self.w3.is_connected():
             print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Web3 connection successful to {getattr(self, 'network_url', 'N/A')}", flush=True) # Use getattr for safety
        else:
             print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WARNING: Web3 connection failed or not established in init.", flush=True)


    def setup_web3_middleware(self, secret: str) -> Web3:
        """Sets up the Web3 instance with Sapphire middleware."""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Setting up Web3 middleware...", flush=True)
        if not secret or not isinstance(secret, str) or not secret.startswith('0x'):
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Invalid or missing secret key.", flush=True)
            raise ValueError("Invalid or missing secret key.")

        account: LocalAccount = None
        try:
            account: LocalAccount = Account.from_key(secret)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Account loaded for address: {account.address}", flush=True)
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to create account from secret: {e}", flush=True)
            traceback.print_exc()
            raise

        # Define network URLs
        networks = {
            "sapphire": "https://sapphire.oasis.io",
            "sapphire-testnet": "https://testnet.sapphire.oasis.io",
            # "sapphire-localnet": "http://localhost:8545",
            "sapphire-localnet": "http://host.docker.internal:8545",
        }
        # Store network_url for later logging
        self.network_url = networks.get(self.network_name, self.network_name) # Use name as URL if not found
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Connecting to network URL: {self.network_url}", flush=True)

        provider = None
        try:
            if self.network_url.startswith("ws"):
                provider = Web3.WebsocketProvider(self.network_url)
            else:
                provider = Web3.HTTPProvider(self.network_url)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Web3 Provider initialized.", flush=True)
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to initialize Web3 provider: {e}", flush=True)
            traceback.print_exc()
            raise

        w3 = None
        try:
            w3 = Web3(provider)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Web3 object initialized.", flush=True)
            if not w3.is_connected():
                 print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WARNING: Web3 object created but not connected.", flush=True)
        except Exception as e:
             print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to initialize Web3 object: {e}", flush=True)
             traceback.print_exc()
             raise

        try:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Wrapping Web3 object with Sapphire middleware...", flush=True)
            w3 = sapphire.wrap(w3, account)
            w3.eth.default_account = account.address # Set default account for transactions
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Web3 object wrapped and default account set to {account.address}", flush=True)
            return w3
        except Exception as e:
             print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to wrap Web3 object with Sapphire: {e}", flush=True)
             traceback.print_exc()
             raise

    @staticmethod
    def get_contract(contract_name: str) -> tuple[list, str]:
        """Fetches ABI and bytecode of the given contract from the contracts folder."""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Loading ABI/bytecode for contract: {contract_name}", flush=True)
        output_path = None # Initialize path variable
        try:
            # --- FIX: Point to the absolute path /contracts/out/... based on Dockerfile ---
            # The WORKDIR is /oracle, but contracts are copied to /contracts
            contracts_out_dir = Path("/contracts/out") # Use absolute path
            # --- END FIX ---

            output_path = (contracts_out_dir / f"{contract_name}.sol" / f"{contract_name}.json").resolve()
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Attempting to load contract JSON from: {output_path}", flush=True)

            if not output_path.exists():
                 error_msg = (
                     f"Contract JSON file not found at expected path: {output_path}. "
                     f"Ensure the contract artifact was compiled and copied to /contracts/out in the final image."
                 )
                 print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {error_msg}", flush=True)
                 raise FileNotFoundError(error_msg)

            with open(output_path, "r") as file:
                contract_data = json.load(file)

            abi = contract_data.get("abi")
            bytecode = contract_data.get("bytecode", {}).get("object")

            if not abi:
                 print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: ABI not found in contract JSON file: {output_path}", flush=True)
                 raise ValueError(f"ABI not found in {output_path}")

            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ABI/bytecode loaded successfully for {contract_name}", flush=True)
            return abi, bytecode
        except FileNotFoundError: # Catch specific error to avoid redundant logging
             raise # Re-raise the FileNotFoundError with the improved message
        except Exception as e:
            # Log other potential errors like JSON parsing issues
            path_str = str(output_path) if output_path else "unknown path"
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to load or parse contract data for {contract_name} from {path_str}: {e}", flush=True)
            traceback.print_exc()
            raise

print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ContractUtility.py loaded.", flush=True)
