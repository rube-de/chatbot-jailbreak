#!/usr/bin/env python3

import argparse
import os
import sys
import traceback
import time

def debug_print(message, debug_mode=False):
    """Print debug messages with timestamp if debug mode is enabled."""
    if debug_mode:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)

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
        default="sapphire-testnet",
    )

    parser.add_argument(
        "--kms",
        help="Override ROFL's appd service URL or socket path (e.g., /run/rofl-appd.sock)",
        default="",
    )

    parser.add_argument(
        "--key-id",
        help="The key ID used by ROFL KMS to identify the oracle's signing key.",
        default="chatbot-oracle",
    )

    parser.add_argument(
        "--secret",
        help="Provide the oracle's private key directly (hex format, 0x...). Use for local testing ONLY.",
        required=False,
    )

    parser.add_argument(
        "--debug",
        help="Enable debug logging with timestamps",
        action="store_true",
        default=False,
    )

    arguments = parser.parse_args()

    # Initialize debug mode
    debug_mode = arguments.debug

    debug_print("main.py starting...", debug_mode)

    # Import required modules with debug output
    debug_print("Importing src.ChatBotOracle...", debug_mode)
    try:
        from src.ChatBotOracle import ChatBotOracle
        debug_print("Importing src.RoflUtility...", debug_mode)
        from src.RoflUtility import RoflUtility
        debug_print("Imports successful.", debug_mode)
    except ImportError as e:
        print(f"ERROR: Failed to import required modules: {e}", flush=True)
        sys.exit(1)

    print(f"Starting ChatBot Oracle service. Using contract {arguments.contract_address} on {arguments.network}.")
    
    if debug_mode:
        debug_print("Starting ChatBot Oracle service.", debug_mode)
        debug_print(f"  Contract Address: {arguments.contract_address}", debug_mode)
        debug_print(f"  Network: {arguments.network}", debug_mode)
        debug_print(f"  ROFL KMS URL/Socket: {'Default' if not arguments.kms else arguments.kms}", debug_mode)
        debug_print(f"  ROFL Key ID: {arguments.key_id}", debug_mode)
        debug_print(f"  Secret Provided: {'Yes' if arguments.secret else 'No (will fetch from KMS)'}", debug_mode)

    # Get LLM provider configuration from environment variables
    llm_provider = os.getenv("LLM_PROVIDER", "openrouter").lower()
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    ollama_address = os.getenv("OLLAMA_ADDRESS")
    
    debug_print(f"LLM Provider: {llm_provider}", debug_mode)
    
    # Validate environment variable combinations
    if llm_provider == "openrouter":
        if not openrouter_api_key:
            print("ERROR: OPENROUTER_API_KEY environment variable required when LLM_PROVIDER=openrouter", flush=True)
            sys.exit(1)
        debug_print("OpenRouter API Key loaded from environment.", debug_mode)
    elif llm_provider == "ollama":
        if not ollama_address:
            print("ERROR: OLLAMA_ADDRESS environment variable required when LLM_PROVIDER=ollama", flush=True)
            sys.exit(1)
        debug_print(f"Ollama address loaded from environment: {ollama_address}", debug_mode)
    else:
        print(f"ERROR: Invalid LLM_PROVIDER='{llm_provider}'. Must be 'openrouter' or 'ollama'", flush=True)
        sys.exit(1)

    secret = None
    rofl_utility = None
    try:
        # Initialize RoflUtility
        debug_print("Initializing RoflUtility...", debug_mode)
        rofl_utility = RoflUtility(arguments.kms)
        debug_print("RoflUtility initialized.", debug_mode)

        # Determine the secret key to use
        if arguments.secret:
            debug_print("Using provided secret key.", debug_mode)
            secret = arguments.secret
            # Basic validation for provided secret
            if not isinstance(secret, str) or not secret.startswith('0x'):
                print("ERROR: Provided secret key is not a valid hex string starting with 0x.", flush=True)
                sys.exit(1)
        else:
            debug_print(f"No secret provided, fetching key '{arguments.key_id}' from ROFL KMS...", debug_mode)
            fetched_secret_raw = rofl_utility.fetch_key(arguments.key_id)
            debug_print(f"DEBUG: Fetched secret type: {type(fetched_secret_raw)}, value (raw): '{fetched_secret_raw}'", debug_mode)

            # Validate the fetched secret *before* adding prefix
            if not fetched_secret_raw or not isinstance(fetched_secret_raw, str):
                print("ERROR: Failed to obtain a valid secret key string from KMS.", flush=True)
                sys.exit(1)

            # Prepend '0x' to the fetched key if it doesn't already have it
            if not fetched_secret_raw.startswith('0x'):
                secret = "0x" + fetched_secret_raw
                debug_print(f"DEBUG: Prepended '0x' to secret: '{secret}'", debug_mode)
            else:
                secret = fetched_secret_raw
                debug_print(f"DEBUG: Secret already has '0x' prefix: '{secret}'", debug_mode)

            # Validate the secret *after* processing
            if not secret.startswith('0x'):
                print(f"ERROR: Internal error - secret key does not start with 0x after processing. Value: '{secret}'", flush=True)
                sys.exit(1)

            debug_print("Secret key fetched successfully from ROFL KMS and formatted.", debug_mode)

        # Instantiate and run the ChatBotOracle
        debug_print("Instantiating ChatBotOracle...", debug_mode)
        chatBotOracle = ChatBotOracle(
            arguments.contract_address,
            arguments.network,
            rofl_utility,
            secret,
            llm_provider,
            openrouter_api_key,
            ollama_address,
            debug_mode
        )
        debug_print("ChatBotOracle instantiated. Starting run loop...", debug_mode)
        chatBotOracle.run()

    except Exception as e:
        print(f"FATAL ERROR in main execution: {e}", flush=True)
        if debug_mode:
            traceback.print_exc()
        sys.exit(1)

    debug_print("main function finished (Oracle run loop exited).", debug_mode)

if __name__ == '__main__':
    main()