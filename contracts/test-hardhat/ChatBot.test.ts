import { expect } from "chai";
import { ethers } from "hardhat";
import { HardhatEthersSigner } from "@nomicfoundation/hardhat-ethers/signers";
import { ChatBot, Gasless } from "../typechain-types"; // Use generated types
import hre from "hardhat";

describe("ChatBot Gasless Tests", function () {
    let chatBot: ChatBot;
    let gaslessProxy: Gasless;
    let owner: HardhatEthersSigner;
    let user: HardhatEthersSigner;
    let oracle: HardhatEthersSigner;

    before(async function () {
        [owner, user, oracle] = await ethers.getSigners();

        // Deploy ChatBot
        chatBot = await hre.ethers.deployContract("ChatBot", [
            "example.com",
            "0x00ea3babcc43dd729557412e1544f41d6c4ae26524",
            oracle.address,
        ]);

        // console.log("ChatBot deployed to:", await chatBot.getAddress());

        // Deploy Gasless
        gaslessProxy = await hre.ethers.deployContract("Gasless", [owner]);
        // console.log("Gasless proxy deployed to:", await gaslessProxy.getAddress());

        // send some eth to gaslessProxy
        const tx = await owner.sendTransaction({
            to: gaslessProxy.getAddress(),
            value: ethers.parseEther("1"),
        });
        await tx.wait();

        // Set Gasless proxy in ChatBot
        await chatBot.connect(owner).setGaslessProxy(await gaslessProxy.getAddress());
        // console.log("Gasless proxy set.");
    });

    describe("appendPrompt (Gasless)", function () {
        it.only("Should allow gasless prompt submission via proxy", async function () {
            const prompt = "Hello from gasless!";
            const initialNonce = await gaslessProxy.getNonce();

            // Prepare calldata for ChatBot.appendPrompt(address,string)
            const callData = chatBot.interface.encodeFunctionData("appendPrompt", [user.address, prompt]);
            try {
            // Create signed tx using Gasless
            const signedTx = await gaslessProxy.makeProxyTx(user.address, await chatBot.getAddress(), callData); // Use getAddress()

            // Broadcast the signed tx to the RPC node
            // Note: In a real scenario, this would be broadcast by a relayer or frontend
            // Here we simulate broadcasting using ethers.provider.sendTransaction (ethers v6 syntax)
            
                await ethers.provider.send("eth_sendRawTransaction", [signedTx]);
            } catch (error) {
                console.error("Error sending raw transaction:", error);
            }

            // Assert prompt was added
            const prompts = await chatBot.getPrompts("", user.address);
            expect(prompts.length).to.equal(1);
            expect(prompts[0]).to.equal(prompt);

            // Assert nonce incremented
            expect(await gaslessProxy.getNonce()).to.equal(initialNonce + 1n); // Use BigInt for comparison
        });

        it("Should revert if appendPrompt is called directly (not from proxy)", async function () {
            const prompt = "Unauthorized attempt";
            // Direct call to appendPrompt should fail (not from proxy)
            await expect(chatBot.connect(user).appendPrompt(user.address, prompt)).to.be.revertedWithCustomError(
                chatBot,
                "ChatBot__UnauthorizedProxy"
            );
        });
    });

    describe("clearPrompt", function () {
        it("Should allow user to clear prompts", async function () {
            // Use gasless flow to append prompt first
            const prompt = "Prompt to clear";
            const callData = chatBot.interface.encodeFunctionData("appendPrompt", [user.address, prompt]);
            const signedTx = await gaslessProxy.makeProxyTx(user.address, await chatBot.getAddress(), callData); // Use getAddress()
            await ethers.provider.send("eth_sendRawTransaction", [signedTx]); // ethers v6 syntax

            // Clear prompts directly
            await chatBot.connect(user).clearPrompt();

            const prompts = await chatBot.getPrompts("", user.address);
            const answers = await chatBot.getAnswers("", user.address);
            expect(prompts.length).to.equal(0);
            expect(answers.length).to.equal(0);
        });
    });

    describe("submitAnswer", function () {
        it("Should allow oracle to submit answer", async function () {
            // Use gasless flow to append prompt first
            const prompt = "Prompt for answer";
            const callData = chatBot.interface.encodeFunctionData("appendPrompt", [user.address, prompt]);
            const signedTx = await gaslessProxy.makeProxyTx(user.address, await chatBot.getAddress(), callData); // Use getAddress()
            await ethers.provider.send("eth_sendRawTransaction", [signedTx]); // ethers v6 syntax

            const answerText = "Test answer";
            const promptId = 0;

            await chatBot.connect(oracle).submitAnswer(answerText, promptId, user.address);

            const answers = await chatBot.getAnswers("", user.address);
            expect(answers.length).to.equal(1);
            expect(answers[0].answer).to.equal(answerText);
            expect(answers[0].promptId).to.equal(promptId);

            // Should revert if prompt is already answered
            await expect(chatBot.connect(oracle).submitAnswer("Test answer too late", promptId, user.address)).to.be.revertedWithCustomError(
                chatBot,
                "PromptAlreadyAnswered"
            );
        });
    });

    describe("getPrompts", function () {
        it("Should revert unauthorized prompt access", async function () {
            const unauthorizedUser = ethers.Wallet.createRandom().address; // A random address not involved

            await expect(chatBot.connect(owner).getPrompts("", unauthorizedUser)).to.be.revertedWithCustomError(
                chatBot,
                "UnauthorizedUserOrOracle"
            );
        });
    });
});
