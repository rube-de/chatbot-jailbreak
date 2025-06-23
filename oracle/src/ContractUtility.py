import time
import sys
import traceback
import json
from pathlib import Path

from web3 import Web3
from web3.middleware import SignAndSendRawMiddlewareBuilder
from eth_account import Account
from eth_account.signers.local import LocalAccount
from sapphirepy import sapphire


class ContractUtility:
    """
    Handles Web3 setup, contract loading, and Sapphire integration.
    """
    def __init__(self, network_name: str, secret: str, debug: bool = False):
        self.debug = debug
        self._debug_print(f"Initializing ContractUtility for network: {network_name}")
        self.network_name = network_name
        
        networks = {
            "sapphire": "https://sapphire.oasis.io",
            "sapphire-testnet": "https://testnet.sapphire.oasis.io",
            "sapphire-localnet": "http://host.docker.internal:8545",
        }
        self.network_url = networks.get(network_name, network_name)
        self._debug_print(f"Connecting to network URL: {self.network_url}")
        
        self.w3 = self.setup_web3_middleware(secret)
        if self.w3 and self.w3.is_connected():
            self._debug_print(f"Web3 connection successful to {self.network_url}")
        else:
            self._debug_print("WARNING: Web3 connection failed or not established in init.")

    def _debug_print(self, message: str):
        """Print debug messages with timestamp if debug mode is enabled."""
        if self.debug:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)

    def setup_web3_middleware(self, secret: str) -> Web3:
        """Sets up the Web3 instance with signing middleware and Sapphire encryption."""
        self._debug_print("Setting up Web3 middleware...")
        
        if not secret or not isinstance(secret, str) or not secret.startswith('0x'):
            error_msg = "Invalid or missing secret key."
            self._debug_print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)

        account: LocalAccount = None
        try:
            account = Account.from_key(secret)
            self._debug_print(f"Account loaded for address: {account.address}")
        except Exception as e:
            self._debug_print(f"ERROR: Failed to create account from secret: {e}")
            if self.debug:
                traceback.print_exc()
            raise

        provider = None
        try:
            if self.network_url.startswith("ws"):
                provider = Web3.WebsocketProvider(self.network_url)
            else:
                provider = Web3.HTTPProvider(self.network_url)
            self._debug_print("Web3 Provider initialized.")
        except Exception as e:
            self._debug_print(f"ERROR: Failed to initialize Web3 provider: {e}")
            if self.debug:
                traceback.print_exc()
            raise

        w3 = None
        try:
            w3 = Web3(provider)
            self._debug_print("Web3 object initialized.")
            if not w3.is_connected():
                self._debug_print("WARNING: Web3 object created but not connected.")
        except Exception as e:
            self._debug_print(f"ERROR: Failed to initialize Web3 object: {e}")
            if self.debug:
                traceback.print_exc()
            raise

        try:
            # First: Add signing middleware (must be before sapphire.wrap)
            self._debug_print("Adding signing middleware...")
            w3.middleware_onion.inject(SignAndSendRawMiddlewareBuilder.build(account), layer=0)
            
            # Then: Add Sapphire encryption middleware
            self._debug_print("Wrapping Web3 object with Sapphire middleware...")
            w3 = sapphire.wrap(w3, account)
            w3.eth.default_account = account.address
            self._debug_print(f"Web3 object wrapped and default account set to {account.address}")
            return w3
        except Exception as e:
            self._debug_print(f"ERROR: Failed to setup Web3 middleware: {e}")
            if self.debug:
                traceback.print_exc()
            raise

    @staticmethod
    def get_contract(contract_name: str) -> tuple[list, str]:
        """Fetches ABI and bytecode of the given contract from the contracts folder."""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Loading ABI/bytecode for contract: {contract_name}", flush=True)
        output_path = None
        try:
            # Use absolute Docker path for contracts
            contracts_out_dir = Path("/contracts/out")
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
        except FileNotFoundError:
            raise
        except Exception as e:
            path_str = str(output_path) if output_path else "unknown path"
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to load or parse contract data for {contract_name} from {path_str}: {e}", flush=True)
            traceback.print_exc()
            raise