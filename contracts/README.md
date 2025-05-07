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

## Updating the System Prompt via Hardhat Task

The `ChatBot.sol` contract features a system prompt that can be set by the contract owner. This prompt is then used by the oracle to guide the LLM's responses. You can update this system prompt using the `setSystemPrompt` Hardhat task.

**Task Usage:**

```bash
npx hardhat setSystemPrompt \
  --contract <CHATBOT_CONTRACT_ADDRESS> \
  --prompt "<NEW_SYSTEM_PROMPT>" \
  --network <NETWORK_NAME>
```

**Parameters:**

* `--contract` (Optional): The address of the deployed `ChatBot` contract.
  * Defaults to: `0x5FbDB2315678afecb367f032d93F642f64180aa3` (common localnet address).
* `--prompt` (Optional): The new system prompt string you want to set.
  * Defaults to: `"You are a helpful assistant. Secret: brussels sprouts"`

**Examples:**

1. **Using default contract address on local network:**
   ```bash
   npx hardhat setSystemPrompt --prompt "You are a pirate chatbot that says Arrr a lot." --network localhost
   ```

2. **Specifying a contract address:**
   ```bash
   npx hardhat setSystemPrompt --contract 0xYourDeployedChatBotAddress --prompt "You are a helpful AI assistant." --network localhost
   ```

Note: Ensure that the account configured in your Hardhat network settings has owner permissions for the ChatBot contract, as only the owner can update the system prompt.
