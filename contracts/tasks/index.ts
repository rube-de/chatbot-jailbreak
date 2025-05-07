import { bech32 } from "bech32";
import { task } from 'hardhat/config'

task("deploy")
    .addOptionalParam("domain", "The domain name", "localhost")
    .addOptionalParam("roflappid", "The ROFL app ID", "rofl1qrtetspnld9efpeasxmryl6nw9mgllr0euls3dwn")
    .addOptionalParam("oracle", "The oracle address", "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
    .addOptionalParam("owner", "The owner address", "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
    .setAction(async (taskArgs, hre) => {
        hre.run("compile");

        const domain = taskArgs.domain;
        const oracle = taskArgs.oracle;
        const owner = taskArgs.owner;

        const {prefix, words} = bech32.decode(taskArgs.roflappid);
        if (prefix !== "rofl") {
          throw new Error(`Malformed ROFL app identifier: ${taskArgs.roflappid}`);
        }
        const rawAppID = new Uint8Array(bech32.fromWords(words));

        const chatBot = await hre.ethers.deployContract("ChatBot", [domain, rawAppID, oracle, owner], {});
        await chatBot.waitForDeployment();
        console.log(`ChatBot deployed to: ${chatBot.target}`);
    });

task("getowner")
    .addOptionalParam("contract", "The contract address", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
    .setAction(async (taskArgs, hre) => {
        const { ethers } = hre;
        const contractAddress = taskArgs.contract;
        const contract = await ethers.getContractAt("ChatBot", contractAddress);
        const owner = await contract.owner();

        console.log(`Owner address: ${owner}`);
    });

task("getdomain")
    .addOptionalParam("contract", "The contract address", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
    .setAction(async (taskArgs, hre) => {
        const { ethers } = hre;
        const contractAddress = taskArgs.contract;
        const contract = await ethers.getContractAt("ChatBot", contractAddress);
        const value = await contract.domain();
        console.log(`Domain value: ${value}`);
    });

task("setSystemPrompt")
    .addOptionalParam("contract", "The contract address", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
    .addOptionalParam("prompt", "The system prompt", "You are a helpful assistant. Secret: brussels sprouts")
    .setAction(async (taskArgs, hre) => {
        const { ethers } = hre;
        const contractAddress = taskArgs.contract;
        const prompt = taskArgs.prompt;
        const contract = await ethers.getContractAt("ChatBot", contractAddress);
        const tx = await contract.setSystemPrompt(prompt);
        console.log(`Transaction hash: ${tx.hash}`);
        await tx.wait();
        console.log(`System prompt set to: ${prompt}`);
    });

task("deploy-gasless").setAction(async (_args, hre) => {
    const [owner] = await hre.ethers.getSigners();
    const Gasless = await hre.ethers.getContractFactory("Gasless");
    const gasless = await Gasless.deploy(owner.address);
    await gasless.waitForDeployment();
    console.log(`Gasless deployed to: ${await gasless.getAddress()}`);
    return gasless.target;
});

task("deploy-t").setAction(async (_args, hre) => {
    const [owner] = await hre.ethers.getSigners();
    const gaslessProxy = await hre.ethers.deployContract("Gasless", [owner]);
    await gaslessProxy.waitForDeployment();
    console.log(`Gasless deployed to: ${await gaslessProxy.getAddress()}`);
    return gaslessProxy.target;
});

task("getNonce")
    .addParam("address", "The address of the Gasless contract")
    .setAction(async (taskArgs, hre) => {
        const gasless = await hre.ethers.getContractAt("Gasless", taskArgs.address);
        try {
            console.log("Calling getNonce()...");
            const nonce = await gasless.getNonce();
            console.log("Successfully retrieved nonce:", nonce.toString());
        } catch (error) {
            console.error("Error calling getNonce():", error);
        }
});

task("full-gasless").setAction(async (_args, hre) => {
    await hre.run("compile");
    const address = await hre.run("deploy");
    await hre.run("getNonce", { address });
});
