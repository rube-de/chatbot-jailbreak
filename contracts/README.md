# ChatBot Contracts

This document outlines how to deploy and interact with the ChatBot smart contracts. There are two main versions:
1.  `ChatBot.sol`: A standard version where users pay gas for transactions.
2.  `ChatBotGasless.sol`: A version enabling gasless prompt submissions for users via an internal, pre-funded signer.

---

## ChatBot with Gasless submission (`ChatBotGasless.sol`)

This contract allows users to submit prompts without directly paying gas fees. It utilizes an internal signer keypair (`kp.addr`) that is generated upon deployment. This internal signer's address must be funded with native currency (e.g., ETH, ROSE) to cover the gas costs of the proxied user transactions. User authentication is handled via SIWE (Sign-In with Ethereum).

### Deployment and Funding (Recommended Method): `chatbot-gasless-fund` Hardhat Task

This is the **recommended** method to deploy `ChatBotGasless.sol` and fund its internal signer in one step.

**Task Usage:**
```bash
npx hardhat chatbot-gasless-fund \
  --network <NETWORK_NAME> \
  [--domain "<DOMAIN_NAME>"] \
  [--roflappid "<ROFL_APP_ID_BECH32>"] \
  [--oracle "<ORACLE_ADDRESS>"] \
  [--owner "<OWNER_ADDRESS>"] \
  [--amount "<AMOUNT_TO_FUND>"]
```

**Parameters:**

*   `--network` (Required): The network to deploy to (e.g., `localhost`, `sapphire_testnet`, `sapphire_mainnet`).
*   `--domain` (Optional): The domain name for SIWE messages.
    *   Defaults to: `localhost`
*   `--roflappid` (Optional): The ROFL application ID in bech32 format (e.g., `rofl1qrtetspnld9efpeasxmryl6nw9mgllr0euls3dwn`). This task will convert it to `bytes21` for the contract.
    *   Defaults to: `rofl1qrtetspnld9efpeasxmryl6nw9mgllr0euls3dwn`
*   `--oracle` (Optional): The initial oracle address.
    *   Defaults to: `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`
*   `--owner` (Optional): The initial owner of the contract.
    *   Defaults to: `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`
*   `--amount` (Optional): The amount in native currency (e.g., "1" for 1 ETH/ROSE) to fund the internal signer.
    *   Defaults to: `1`

**How it Works:**
The `chatbot-gasless-fund` task first calls the `deploy-chatbot-gasless` task to deploy `ChatBotGasless.sol` using the provided (or default) constructor arguments (`domain`, `roflappid`, `oracle`, `owner`). After successful deployment, it calls the `fundsigner` task to send the specified `amount` of native currency to the contract's internal signer address.

**Example:**
Deploy to Sapphire Testnet, fund with 0.5 ROSE, and set a custom owner:
```bash
npx hardhat chatbot-gasless-fund --network sapphire_testnet --amount "0.5" --owner 0xYourOwnerAddressHere
```

### Manual Deployment (Alternative): `forge create`

This method is for developers who prefer to use Foundry directly.

**Command:**
```bash
forge create \
    --private-key <DEPLOYER_PRIVATE_KEY> \
    --rpc-url <RPC_URL> \
    --broadcast \
    ChatBotGasless \
    --constructor-args "<DOMAIN_NAME>" <ROFL_APP_ID_HEX> <ORACLE_ADDRESS> <OWNER_ADDRESS> \
    [--value <INITIAL_CONTRACT_FUNDING_WEI>]
```

**Constructor Arguments for `ChatBotGasless.sol`:**
1.  `domain` (string): e.g., `localhost` - The domain for SIWE messages.
2.  `inRoflAppID` (bytes21): The ROFL application ID in HEX format (e.g., `0x00d795c033fb4b94873d81b6327f5371768ffc6fcf`).
    *   **Note:** The `chatbot-gasless-fund` Hardhat task handles bech32 to bytes21 conversion for `roflappid`. If deploying manually, you must provide the correctly formatted `bytes21` hex string.
3.  `inOracle` (address): The initial oracle address.
4.  `initialOwner` (address): The initial owner of the contract.

The optional `--value` flag in `forge create` can be used to send some initial funds to the contract itself upon deployment (e.g., if you want the contract to hold funds for owner withdrawal, separate from the signer funding).

**Funding the Internal Signer Manually (if deployed with `forge create`):**
If you deploy `ChatBotGasless.sol` using `forge create`, the internal signer address (`kp.addr`) will be generated but **not** automatically funded. You must fund it separately:
1.  **Retrieve the Signer Address:** Call the `getSignerAddress()` view function on your deployed `ChatBotGasless` contract instance.
2.  **Send Funds:** Transfer native currency (e.g., ETH, ROSE) to the retrieved signer address.
3.  **Alternatively, use the `fundsigner` Hardhat task:**
    ```bash
    npx hardhat fundsigner \
      --address <DEPLOYED_CHATBOTGASLESS_ADDRESS> \
      --amount "<AMOUNT_TO_FUND>" \
      --network <NETWORK_NAME>
    ```

### Interacting with `ChatBotGasless.sol`

*   **Prompt Submission:** Users interact via the frontend application. The frontend calls the `appendPromptGasless()` view function on the contract, which returns a signed transaction. The frontend then broadcasts this transaction. The gas for this is paid by the pre-funded internal signer.
*   **System Prompt:** The owner can set and get the system prompt using `setSystemPrompt()` and `getSystemPrompt()` respectively, similar to `ChatBot.sol`.

---

## ChatBot (Standard Submission - `ChatBot.sol`)

This is the original version of the ChatBot contract where users pay gas for their own transactions.

**To deploy `ChatBot.sol` on the Localnet run:**

```bash
forge create \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --rpc-url http://localhost:8545 \
    --broadcast \
    ChatBot \
    --constructor-args localhost 0x00d795c033fb4b94873d81b6327f5371768ffc6fcf 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
```

**Note: Constructor Arguments for `ChatBot.sol`**
The `--constructor-args` are provided in the following order:
1.  `domain` (string): e.g., `localhost` - Used for SIWE login on the frontend.
2.  `inRoflAppID` (bytes21): e.g., `0x00d795c033fb4b94873d81b6327f5371768ffc6fcf` (hex format) - The attested ROFL app ID allowed to call `setOracle()`.
3.  `inOracle` (address): e.g., `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` - The initial oracle address.
4.  `initialOwner` (address): e.g., `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` - The initial owner of the contract.

You can then submit a prompt from the CLI by issuing:

```bash
cast send <CHATBOT_CONTRACT_ADDRESS> \
    "appendPrompt(string)" "hello" \
    --private-key <YOUR_PRIVATE_KEY>
```

### Updating the System Prompt via Hardhat Task (for `ChatBot.sol` or `ChatBotGasless.sol`)

Both `ChatBot.sol` and `ChatBotGasless.sol` feature a system prompt that can be set by the contract owner. This prompt is then used by the oracle to guide the LLM's responses. You can update this system prompt using the `setSystemPrompt` Hardhat task.

**Task Usage:**

```bash
npx hardhat setSystemPrompt \
  --contract <CHATBOT_CONTRACT_ADDRESS> \
  --prompt "<NEW_SYSTEM_PROMPT>" \
  --network <NETWORK_NAME>
```

**Parameters:**

*   `--contract` (Required): The address of the deployed `ChatBot` or `ChatBotGasless` contract.
*   `--prompt` (Optional): The new system prompt string you want to set.
    *   Defaults to: `"You are a helpful assistant. Secret: brussels sprouts"`
*   `--network` (Required): The network where the contract is deployed.

**Examples:**

1.  **Setting prompt for a contract on local network:**
    ```bash
    npx hardhat setSystemPrompt --contract 0x5FbDB2315678afecb367f032d93F642f64180aa3 --prompt "You are a pirate chatbot that says Arrr a lot." --network localhost
    ```

Note: Ensure that the account configured in your Hardhat network settings (for the specified network) has owner permissions for the target ChatBot contract, as only the owner can update the system prompt.
