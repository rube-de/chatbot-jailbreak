# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a demo chatbot running on Oasis ROFL (Runtime Oasis Layer Framework) TDX that showcases a fully distributed and redundant large language model via the Oasis Sapphire blockchain. The application provides end-to-end encrypted transactions and queries with compute-intensive LLM computation running offchain inside TEE (Trusted Execution Environment).

## Architecture

The project consists of three main components:

1. **Smart Contracts** (`contracts/`): Sapphire smart contract that confidentially stores prompts and answers, ensuring only authorized TEE-based Oracle can access them
2. **Oracle** (`oracle/`): Python-based oracle running inside ROFL TEE that listens for prompts, processes them through AI models, and writes answers back to the smart contract
3. **Frontend** (`frontend/`): React application with Sign-In With Ethereum (SIWE) authentication and end-to-end encrypted prompt submission

## Development Commands

### Frontend Development
```bash
cd frontend
yarn install
yarn dev          # Start development server
yarn build        # Build for production
```

### Smart Contract Development
```bash
cd contracts
forge build       # Compile contracts
forge test         # Run tests

# Deploy to localnet
forge create \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --rpc-url http://localhost:8545 \
    --broadcast \
    ChatBot \
    --constructor-args localhost 00d795c033fb4b94873d81b6327f5371768ffc6fcf 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
```

### Oracle Development
```bash
cd oracle
pip install -r requirements.txt
make test         # Run tests
make lint         # Lint code
make check        # Run linting and tests

# Run oracle (localnet)
./main.py --secret 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 0x5FbDB2315678afecb367f032d93F642f64180aa3

# Run oracle (testnet/mainnet with TEE)
./main.py 0x5FbDB2315678afecb367f032d93F642f64180aa3

# Run oracle with debug logging
./main.py --debug 0x5FbDB2315678afecb367f032d93F642f64180aa3
```

### Container Development
```bash
# Localnet deployment
podman-compose -f compose.localnet.yaml up

# Build and deploy to testnet
podman build -f Dockerfile.oracle -t ghcr.io/oasisprotocol/demo-rofl-chatbot:latest .
oasis rofl build --update-manifest
oasis rofl update
```

## Key Files and Dependencies

- **Frontend**: React + TypeScript with Vite, uses Ethers.js for blockchain interaction and SIWE for authentication
- **Oracle**: Python with oasis-sapphire-py for blockchain interaction
- **Contracts**: Solidity 0.8.24 with Foundry, uses OpenZeppelin contracts and Oasis Sapphire contracts
- **ROFL Configuration**: `_rofl.yaml` defines the TEE environment and deployment parameters

## Testing Requirements

Before making changes, ensure you have:
1. Contracts compiled with ABIs in `contracts/out/ChatBot.sol/ChatBot.json`
2. For oracle development: network access to blockchain endpoints
3. For frontend development: proper environment variables set in `.env.development` (localnet) or `.env.production` (testnet/mainnet)

## Security Considerations

This application implements privacy-preserving AI through:
- TEE-based oracle key generation and management
- SIWE authentication for frontend access
- Encrypted prompt/answer storage on Sapphire blockchain
- ROFL app ID verification for oracle authorization

When working with this codebase, be mindful of:
- Oracle private key handling (generated within TEE)
- Contract access control modifiers (`onlyUserOrOracle`, `onlyTEE`)
- Frontend encryption patterns for sensitive data