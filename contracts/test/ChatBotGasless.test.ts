import { expect } from "chai";
import { ethers } from "hardhat";
import { HardhatEthersSigner } from "@nomicfoundation/hardhat-ethers/signers";
import { ChatBotGasless, ChatBotGasless__factory } from "../typechain"; // Changed path to be consistent with ChatBot.test.ts
import {
    wrapEthereumProvider,
    isCalldataEnveloped
} from '@oasisprotocol/sapphire-paratime';
import { SiweMessage } from 'siwe';
import { bech32 } from "bech32";

describe("ChatBotGasless", () => {
    let chatBotGasless: ChatBotGasless;
    let owner: HardhatEthersSigner;
    let user1: HardhatEthersSigner;
    let user2: HardhatEthersSigner;
    let oracleSigner: HardhatEthersSigner;
    let sapphireProvider: any; // Wrapped ethers provider
    const testDomain = "roflchatbot.test"; // Consistent domain for SIWE
    const roflAppId = "rofl1qrtetspnld9efpeasxmryl6nw9mgllr0euls3dwn"

    // Helper function to prepare SIWE Message string
    async function prepareSiweMessage(
        signer: HardhatEthersSigner,
        statement: string = "Sign in with Ethereum to the ROFL ChatBot."
    ): Promise<string> { // Returns the EIP-4361 message string
        const address = signer.address;
        const chainId = Number((await ethers.provider.getNetwork()).chainId);
        
        const siweParams: ConstructorParameters<typeof SiweMessage>[0] = {
            domain: testDomain,
            address,
            statement,
            uri: `https://${testDomain}`,
            version: '1',
            chainId,
            nonce: ethers.hexlify(ethers.randomBytes(32)), 
            issuedAt: new Date().toISOString(),
        };
        const siweMessage = new SiweMessage(siweParams);
        return siweMessage.prepareMessage();
    }

    // Helper to sign the SIWE message string
    async function signSiweMessage(message: string, signer: HardhatEthersSigner): Promise<{r: string, s: string, v: number}> {
        const flatSignature = await signer.signMessage(message);
        const sig = ethers.Signature.from(flatSignature);
        return { r: sig.r, s: sig.s, v: sig.v };
    }
    
    // Helper to perform login and get authToken
    async function loginAndGetAuthToken(signer: HardhatEthersSigner, statement?: string): Promise<string> {
        const siweMsgStr = await prepareSiweMessage(signer, statement);
        const signatureComps = await signSiweMessage(siweMsgStr, signer);
        return chatBotGasless.connect(signer).login(siweMsgStr, signatureComps);
    }


    before(async () => {
        [owner, user1, user2, oracleSigner] = await ethers.getSigners();

        const {prefix, words} = bech32.decode(roflAppId);
        if (prefix !== "rofl") {
          throw new Error(`Malformed ROFL app identifier: ${roflAppId}`);
        }
        const rawAppID = new Uint8Array(bech32.fromWords(words));

        // const chatBotGaslessFactory = await ethers.getContractFactory("ChatBotGasless");
        const chatBotGaslessFactory = new ChatBotGasless__factory(owner);
        chatBotGasless = await chatBotGaslessFactory.deploy(
            testDomain,
            rawAppID,
            oracleSigner.address,
            owner.address
        ); // Removed explicit cast, factory should provide correct type
        await chatBotGasless.waitForDeployment();
        console.log("ChatBotGasless deployed to:", await chatBotGasless.getAddress());

        sapphireProvider = wrapEthereumProvider(ethers.provider as any);

        // Fund the internal signer for gas costs of proxied transactions
        const internalSignerAddress = await chatBotGasless.getSignerAddress();
        await owner.sendTransaction({ to: internalSignerAddress, value: ethers.parseEther("1.0") });
    });

    describe("Deployment and Initialization", () => {
        it("Should set the correct owner", async () => {
            expect(await chatBotGasless.owner()).to.equal(owner.address);
        });

        it("Should set the correct oracle", async () => {
            expect(await chatBotGasless.oracle()).to.equal(oracleSigner.address);
        });

        it("Should generate a valid internal signer address", async () => {
            const signerAddr = await chatBotGasless.getSignerAddress();
            expect(signerAddr).to.not.equal(ethers.ZeroAddress);
            expect(ethers.isAddress(signerAddr)).to.be.true;
        });

        it("Should have an initial internal signer nonce of 0", async () => {
            expect(await chatBotGasless.getNonce()).to.equal(0);
        });

        it.skip("Should have its balance reflect ETH sent on deployment", async () => {
            const balance = await ethers.provider.getBalance(await chatBotGasless.getAddress());
            expect(balance).to.equal(ethers.parseEther("2.0"));
        });
    });

    describe("Contract Funding and Owner Withdrawal", () => {
        it("Should allow contract to receive ETH via receive()", async () => {
            const initialBalance = await ethers.provider.getBalance(await chatBotGasless.getAddress());
            const tx = await owner.sendTransaction({
                to: await chatBotGasless.getAddress(),
                value: ethers.parseEther("1.0")
            });
            await tx.wait();
            const finalBalance = await ethers.provider.getBalance(await chatBotGasless.getAddress());
            expect(finalBalance).to.equal(initialBalance + ethers.parseEther("1.0"));
            await expect(tx).to.emit(chatBotGasless, "ContractFunded").withArgs(owner.address, ethers.parseEther("1.0"));
        });

        it("Should allow owner to withdraw funds", async () => {
            const contractInitialBalance = await ethers.provider.getBalance(await chatBotGasless.getAddress());
            const ownerInitialBalance = await ethers.provider.getBalance(owner.address);
            const withdrawAmount = ethers.parseEther("0.5");

            const tx = await chatBotGasless.connect(owner).withdraw(withdrawAmount);
            const receipt = await tx.wait();
            const gasUsed = receipt!.gasUsed * receipt!.gasPrice!; 

            const contractFinalBalance = await ethers.provider.getBalance(await chatBotGasless.getAddress());
            const ownerFinalBalance = await ethers.provider.getBalance(owner.address);

            expect(contractFinalBalance).to.equal(contractInitialBalance - withdrawAmount);
            // Ensure all operands are BigInt for arithmetic safety
            expect(ownerFinalBalance).to.equal(BigInt(ownerInitialBalance) - BigInt(gasUsed) + BigInt(withdrawAmount)); 
            await expect(tx).to.emit(chatBotGasless, "WithdrawalCompleted").withArgs(owner.address, withdrawAmount);
        });

        it("Should revert if non-owner tries to withdraw", async () => {
            await expect(chatBotGasless.connect(user1).withdraw(ethers.parseEther("0.1")))
                .to.be.revertedWithCustomError(chatBotGasless, "OwnableUnauthorizedAccount")
                .withArgs(user1.address);
        });

        it("Should revert withdrawing zero amount", async () => {
            await expect(chatBotGasless.connect(owner).withdraw(0))
                .to.be.revertedWithCustomError(chatBotGasless, "Gasless__FundingAmountZero");
        });

        it("Should revert withdrawing more than contract balance", async () => {
            const excessiveAmount = ethers.parseEther("10.0"); // More than deployed with
            await expect(chatBotGasless.connect(owner).withdraw(excessiveAmount))
                .to.be.revertedWithCustomError(chatBotGasless, "ChatBotGasless__InsufficientContractBalance");
        });
    });

    describe.only("Gasless Prompt Submission via appendPromptGasless and proxy", () => {
        it("should allow a user to prepare a signed transaction using appendPromptGasless", async () => {
            const authToken = await loginAndGetAuthToken(user1);
            const prompt = "My Gasless Prompt";
            // console.log("Auth token:", authToken); 
            const signedTxData = await chatBotGasless.appendPromptGasless(authToken, user1.address, prompt);
            // console.log("Signed transaction data:", signedTxData);
            expect(signedTxData).to.be.a('string');
            expect(signedTxData.startsWith("0x")).to.be.true;
        });

        it.skip("should revert appendPromptGasless if authToken's user mismatches the provided userAddress", async () => {
            const authTokenUser1 = await loginAndGetAuthToken(user1); // user1 logs in
            const prompt = "Mismatch Prompt";
            // user1 uses their token but tries to act on behalf of user2
            await expect(chatBotGasless.connect(user1).appendPromptGasless(authTokenUser1, user2.address, prompt))
                .to.be.revertedWithCustomError(chatBotGasless, "ChatBotGasless__UserMismatch");
        });

        it("should successfully execute a gasless prompt submission", async () => {
            const prompt = "Hello Sapphire!";
            const authToken = await loginAndGetAuthToken(user1);
            const initialSignerNonce = await chatBotGasless.getNonce();

            const signedTxData = await chatBotGasless.appendPromptGasless(authToken, user1.address, prompt);
            
            console.log("broadcasting signed transaction...");
            const response = await sapphireProvider.broadcastTransaction(signedTxData);
            expect(isCalldataEnveloped(response.data)).to.be.true;
            // console.log("Response data:", response.data);
            await response.wait();
        
            // console.log("Transaction hash:", response.hash);
            const receipt = await sapphireProvider.getTransactionReceipt(response.hash);
            // console.log("Transaction receipt:", receipt);
            if (!receipt || receipt.status != 1) throw new Error('tx failed');

            await expect(response).to.emit(chatBotGasless, "PromptSubmitted").withArgs(user1.address);
            // Note: TransactionProxied event is emitted by the contract, need to listen for it from the transaction hash
            // This requires a bit more setup or checking logs if not directly asserted via `await expect(tx).to.emit(...)` on the sendTransaction result.
            // For simplicity, we'll check effects.

            const prompts = await chatBotGasless.connect(user1).getPrompts(authToken, user1.address);
            expect(prompts.length).to.equal(1);
            expect(prompts[0]).to.equal(prompt);

            expect(await chatBotGasless.getNonce()).to.equal(initialSignerNonce + 1n);
        });

    });

    describe("Standard ChatBot Functions (with SIWE and direct calls)", () => {
        it("clearPrompt should clear user's prompts with valid SIWE token", async () => {
            // 1. Add a prompt gaslessly
            const prompt1 = "Prompt to be cleared";
            const authTokenAdd = await loginAndGetAuthToken(user1);
            const signedTxAdd = await chatBotGasless.connect(user1).appendPromptGasless(authTokenAdd, user1.address, prompt1);
            const respAdd = await sapphireProvider.sendTransaction(signedTxAdd);
            await respAdd.wait();

            // 2. Clear prompts
            const authTokenClear = await loginAndGetAuthToken(user1, "Clearing my prompts.");
            
            // clearPrompt does not emit "PromptSubmitted". It has no custom event.
            // We will just check the effect.
            const txClear = await chatBotGasless.connect(user1).clearPrompt(authTokenClear);
            await txClear.wait();

            const promptsAfterClear = await chatBotGasless.connect(user1).getPrompts(authTokenClear, user1.address);
            expect(promptsAfterClear.length).to.equal(0);
            const answersAfterClear = await chatBotGasless.connect(user1).getAnswers(authTokenClear, user1.address);
            expect(answersAfterClear.length).to.equal(0);
        });
        
        it("setOracle should revert if called by non-TEE (e.g., owner)", async () => {
            await expect(chatBotGasless.connect(owner).setOracle(user2.address))
                .to.be.reverted; // Generic revert as onlyTEE is a raw Subcall check
        });

        it("submitAnswer should allow oracle and revert for others", async () => {
            // Add a prompt first
            const promptText = "Question for oracle";
            const authTokenUser = await loginAndGetAuthToken(user1);
            const signedTx = await chatBotGasless.connect(user1).appendPromptGasless(authTokenUser, user1.address, promptText);
            await (await sapphireProvider.sendTransaction(signedTx)).wait();

            const answerText = "Oracle's answer";
            await expect(chatBotGasless.connect(oracleSigner).submitAnswer(answerText, 0, user1.address))
                .to.emit(chatBotGasless, "AnswerSubmitted").withArgs(user1.address);

            const answers = await chatBotGasless.connect(oracleSigner).getAnswers("", user1.address); // Oracle uses empty auth
            expect(answers.length).to.equal(1);
            expect(answers[0].answer).to.equal(answerText);

            await expect(chatBotGasless.connect(user1).submitAnswer("User trying to answer", 0, user1.address))
                .to.be.revertedWithCustomError(chatBotGasless, "UnauthorizedOracle");
        });

        it("setSystemPrompt should allow owner and revert for others", async () => {
            const newSystemPrompt = "Be very helpful.";
            await expect(chatBotGasless.connect(owner).setSystemPrompt(newSystemPrompt)).to.not.be.reverted;
            // Oracle can get it, but not user1
            expect(await chatBotGasless.connect(oracleSigner).getSystemPrompt()).to.equal(newSystemPrompt); // No args


            await expect(chatBotGasless.connect(user1).setSystemPrompt("User system prompt"))
                .to.be.revertedWithCustomError(chatBotGasless, "OwnableUnauthorizedAccount")
                .withArgs(user1.address);
        });

        it("getSystemPrompt should allow owner/oracle and revert for others", async () => {
            await chatBotGasless.connect(owner).setSystemPrompt("Initial prompt");
            expect(await chatBotGasless.connect(owner).getSystemPrompt()).to.equal("Initial prompt"); // No args
            expect(await chatBotGasless.connect(oracleSigner).getSystemPrompt()).to.equal("Initial prompt"); // No args

            const authTokenUser1 = await loginAndGetAuthToken(user1); // User1 gets their token
            // getSystemPrompt is onlyOwnerOrOracle, does not take authToken for user check
            await expect(chatBotGasless.connect(user1).getSystemPrompt()) 
                .to.be.revertedWithCustomError(chatBotGasless, "NotOwnerOrOracle");
        });

        it("getPrompts should enforce user/oracle access", async () => {
            const authTokenUser1 = await loginAndGetAuthToken(user1); // User1 gets their token
            // user1 adds a prompt
            const signedTx = await chatBotGasless.connect(user1).appendPromptGasless(authTokenUser1, user1.address, "User1's prompt");
            await (await sapphireProvider.sendTransaction(signedTx)).wait();

            // User1 can get their own prompts
            await expect(chatBotGasless.connect(user1).getPrompts(authTokenUser1, user1.address)).to.not.be.reverted;
            
            // Owner can get user1's prompts (uses empty string for authToken as per SiweAuth.sol for special roles)
            await expect(chatBotGasless.connect(owner).getPrompts("", user1.address)).to.not.be.reverted;
            
            // Oracle can get user1's prompts (uses empty string for authToken)
            await expect(chatBotGasless.connect(oracleSigner).getPrompts("", user1.address)).to.not.be.reverted;

            // User2 cannot get user1's prompts
            const authTokenUser2 = await loginAndGetAuthToken(user2); // User2 gets their token
            await expect(chatBotGasless.connect(user2).getPrompts(authTokenUser2, user1.address)) // User2 uses their token
                .to.be.revertedWithCustomError(chatBotGasless, "UnauthorizedUserOrOracle");
        });
    });
});
