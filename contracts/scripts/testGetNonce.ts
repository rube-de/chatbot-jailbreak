import hre from "hardhat";
import { ethers } from "hardhat";
import { Gasless, Gasless__factory, ChatBot, ChatBot__factory } from "../typechain-types"; // Adjust path if needed

async function main() {
  console.log("deploying chatbot ..")
  let ChatBotFactory: ChatBot__factory = await ethers.getContractFactory("ChatBot");
  const chatBot: ChatBot = await(await ChatBotFactory.deploy(
    "localhost",
    "0x00ea3babcc43dd729557412e1544f41d6c4ae26524",
    "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
  )).waitForDeployment
  // const oracle = chatBot.getFunction("oracle()").staticCall();
  const oracle = await chatBot.oracle();
  console.log("oracle address:", oracle);
  console.log(`ChatBot deployed to: ${await chatBot.getAddress()}`);
  console.log("Deploying Gasless contract...");
  const GaslessContractFactory = await ethers.getContractFactory("Gasless");
  const gaslessProxy = await GaslessContractFactory.deploy({
    value: ethers.parseEther("1"),
  });
  console.log(`Gasless deployed to: ${await gaslessProxy.getAddress()}`);
  await gaslessProxy.waitForDeployment();
  // if (deployTx) {
  //   // In ethers v6, deploymentTransaction might be null if already deployed or attached
  //   // We need to wait for the transaction to be mined to ensure deployment is complete
  //   const receipt = await deployTx.wait();
  //   console.log(`Gasless deployed to: ${await gaslessProxy.getAddress()} in tx: ${receipt?.hash}`); // Use receipt.hash
  // } else {
  //    // If deploymentTransaction is null, it might mean we attached to an existing instance
  //    // or something unexpected happened. Let's log the address if available.
  //    try {
  //       const address = await gaslessProxy.getAddress();
  //       console.log(`Gasless already deployed or attached at: ${address}`);
  //    } catch (e) {
  //       console.error("Could not get deployment transaction or address!");
  //       return;
  //    }
  // }
  console.log(`Gasless deployed to: ${await gaslessProxy.getAddress()}`);
  const tst = await gaslessProxy.tst();
  console.log("tst:", tst);

  try {
    console.log("Calling getNonce()...");
    const nonce = await gaslessProxy.getNonce();
    console.log("Successfully retrieved nonce:", nonce.toString());
  } catch (error) {
    console.error("Error calling getNonce():", error);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
