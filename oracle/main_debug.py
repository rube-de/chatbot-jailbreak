#!/usr/bin/env python3

import argparse
import os
import sys
import traceback
import time # Added for timestamp

print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] main.py v0.1.23 starting...", flush=True)

# Import required modules. If any fail, the script will exit with an ImportError.
print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Importing src.ChatBotOracle...", flush=True)
from src.ChatBotOracle import ChatBotOracle
print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Importing src.RoflUtility...", flush=True)
from src.RoflUtility import RoflUtility
print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Imports successful.", flush=True)


def main():
    """
    Main method for the ChatBot Oracle service.
    Parses arguments, initializes utilities, and runs the oracle.
    """
    parser = argparse.ArgumentParser(description="Oasis Sapphire ChatBot Oracle Service.")

    parser.add_argument(
        "contract_address",
        type=str,
        help="Address of the deployed ChatBot smart contract."
    )

    parser.add_argument(
        "--network",
        help="Network name or RPC URL (e.g., sapphire, sapphire-testnet, wss://testnet.sapphire.oasis.io/ws)",
        default="sapphire-testnet", # Default to testnet
    )

    parser.add_argument(
        "--kms",
        help="Override ROFL's appd service URL or socket path (e.g., /run/rofl-appd.sock)",
        default="", # Default uses RoflUtility.ROFL_SOCKET_PATH
    )

    parser.add_argument(
        "--key-id",
        help="The key ID used by ROFL KMS to identify the oracle's signing key.",
        default="chatbot-oracle", # Default key ID
    )

    parser.add_argument(
        "--secret",
        help="Provide the oracle's private key directly (hex format, 0x...). Use for local testing ONLY.",
        required=False, # Not required if using ROFL KMS
    )

    arguments = parser.parse_args()

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting ChatBot Oracle service.", flush=True)
    print(f"  Contract Address: {arguments.contract_address}", flush=True)
    print(f"  Network: {arguments.network}", flush=True)
    print(f"  ROFL KMS URL/Socket: {'Default (' + RoflUtility.ROFL_SOCKET_PATH + ')' if not arguments.kms else arguments.kms}", flush=True)
    print(f"  ROFL Key ID: {arguments.key_id}", flush=True)
    print(f"  Secret Provided: {'Yes' if arguments.secret else 'No (will fetch from KMS)'}", flush=True)


    # Get OpenRouter API Key from environment variable
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: OPENROUTER_API_KEY environment variable not set.", flush=True)
        sys.exit(1) # Exit if the key is not found
    else:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] OpenRouter API Key loaded from environment.", flush=True)

    secret = None
    rofl_utility = None
    try:
        # Initialize RoflUtility - needed for fetching key if secret not provided
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Initializing RoflUtility...", flush=True)
        rofl_utility = RoflUtility(arguments.kms)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] RoflUtility initialized.", flush=True)

        # Determine the secret key to use
        if arguments.secret:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Using provided secret key.", flush=True)
            secret = arguments.secret
            # Basic validation for provided secret
            if not isinstance(secret, str) or not secret.startswith('0x'):
                 print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Provided secret key is not a valid hex string starting with 0x.", flush=True)
                 sys.exit(1)
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] No secret provided, fetching key '{arguments.key_id}' from ROFL KMS...", flush=True)
            fetched_secret_raw = rofl_utility.fetch_key(arguments.key_id)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] DEBUG: Fetched secret type: {type(fetched_secret_raw)}, value (raw): '{fetched_secret_raw}'", flush=True)

            # Validate the fetched secret *before* adding prefix
            if not fetched_secret_raw or not isinstance(fetched_secret_raw, str):
                 print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to obtain a valid secret key string from KMS.", flush=True)
                 sys.exit(1)

            # --- FIX: Prepend '0x' to the fetched key ---
            secret = "0x" + fetched_secret_raw
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] DEBUG: Prepended '0x' to secret: '{secret}'", flush=True)
            # --- END FIX ---

            # Validate the secret *after* adding the prefix
            if not secret.startswith('0x'): # This check should always pass now, but keep for safety
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Internal error - secret key does not start with 0x after prepending. Value: '{secret}'", flush=True)
                sys.exit(1)
            # You might add a length check too if desired (e.g., len(secret) == 66 for a 32-byte key)

            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Secret key fetched successfully from ROFL KMS and formatted.", flush=True)


        # Instantiate and run the fully functional ChatBotOracle
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Instantiating ChatBotOracle...", flush=True)
        chatBotOracle = ChatBotOracle(
            arguments.contract_address,
            arguments.network,
            openrouter_api_key,
            rofl_utility, # Pass the utility instance
            secret        # Pass the formatted secret key (with 0x)
        )
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ChatBotOracle instantiated. Starting run loop...", flush=True)
        chatBotOracle.run() # Start the main oracle logic

    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] FATAL ERROR in main execution: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1) # Exit on fatal error

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] main function finished (Oracle run loop exited).", flush=True)

if __name__ == '__main__':
    main()
