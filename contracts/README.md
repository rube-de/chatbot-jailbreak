# Chat bot contracts

To deploy on the Localnet run:

```bash
forge create \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --rpc-url http://localhost:8545 \
    --broadcast \
    ChatBot \
    --constructor-args localhost 00d795c033fb4b94873d81b6327f5371768ffc6fcf 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
```

**Note: Constructor Arguments**
The `--constructor-args` are provided in the following order:
1.  `domain` (string): e.g., `localhost` - Used for SIWE login on the frontend.
2.  `inRoflAppID` (bytes21): e.g., `00d795c033fb4b94873d81b6327f5371768ffc6fcf` - The attested ROFL app ID allowed to call `setOracle()`.
3.  `inOracle` (address): e.g., `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` - The initial oracle address.
4.  `initialOwner` (address): e.g., `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` - The initial owner of the contract.

You can then submit a prompt from the CLI by issuing:

```bash
cast send 0x5FbDB2315678afecb367f032d93F642f64180aa3 \
    "appendPrompt(string)" "hello" \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
```

---

## Updating the System Prompt via Script

The `ChatBot.sol` contract features a system prompt that can be set by the contract owner. This prompt is then used by the oracle to guide the LLM's responses. You can update this system prompt using the `SetSystemPrompt.s.sol` script.

**Script Location:** `contracts/script/SetSystemPrompt.s.sol`

**Environment Variables:**

The script uses the following environment variables. Set them in your shell before running the script:

*   `CHATBOT_CONTRACT_ADDRESS` (Optional): The address of the deployed `ChatBot` contract.
    *   Defaults to: `0x5FbDB2315678afecb367f032d93F642f64180aa3` (common localnet address).
*   `NEW_SYSTEM_PROMPT` (Optional): The new system prompt string you want to set.
    *   Defaults to: `"You are a helpful and concise AI assistant."`
*   `OWNER_PRIVATE_KEY` (Optional but **CRITICAL**): The private key of the account that owns the `ChatBot` contract.
    *   Defaults to: `0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80` (standard localnet testing key).
    *   **WARNING:** For any deployments on public testnets or mainnet, you **MUST** override this default by setting the `OWNER_PRIVATE_KEY` environment variable to the actual owner's private key. Using the default key on a live network is a significant security risk.
*   `RPC_URL` (Required for `--rpc-url` flag): The RPC URL of the network where the contract is deployed.

**Execution Command:**

1.  **Set Environment Variables (example):**
    ```bash
    export CHATBOT_CONTRACT_ADDRESS="0xYourDeployedChatBotAddress" # Or rely on default for local
    export NEW_SYSTEM_PROMPT="You are a pirate chatbot that says Arrr a lot."
    export OWNER_PRIVATE_KEY="0xYourActualOwnerPrivateKey" # CRITICAL for non-local
    export RPC_URL="http://localhost:8545" # Or your target network's RPC URL
    ```

2.  **Run the script:**
    ```bash
    forge script contracts/script/SetSystemPrompt.s.sol:SetSystemPrompt \
        --rpc-url $RPC_URL \
        --private-key $OWNER_PRIVATE_KEY \
        --broadcast
    ```
    *Note: The `--private-key $OWNER_PRIVATE_KEY` in the command line overrides the `vm.envUintOr("OWNER_PRIVATE_KEY", ...)` if you prefer to pass it directly instead of setting the env var for the key specifically for the `vm.startBroadcast()` call. However, the script is written to primarily use `vm.envUintOr`. For consistency with how the script reads it for `vm.startBroadcast`, ensure `OWNER_PRIVATE_KEY` is set as an environment variable.*

    If you want to rely on the script's internal defaults for `CHATBOT_CONTRACT_ADDRESS`, `NEW_SYSTEM_PROMPT`, and `OWNER_PRIVATE_KEY` (for local testing ONLY for the private key), you can simplify:
    ```bash
    export RPC_URL="http://localhost:8545"
    # Ensure OWNER_PRIVATE_KEY is set if not using the default, or if default is not desired.
    # export OWNER_PRIVATE_KEY="0xYourActualOwnerPrivateKey"


    forge script contracts/script/SetSystemPrompt.s.sol:SetSystemPrompt \
        --rpc-url $RPC_URL \
        --broadcast 
    # This relies on vm.env...Or("OWNER_PRIVATE_KEY", DEFAULT_OWNER_PRIVATE_KEY) for the broadcast.
    # For clarity and safety, explicitly setting OWNER_PRIVATE_KEY env var or using --private-key CLI arg is recommended for non-default keys.
    ```
