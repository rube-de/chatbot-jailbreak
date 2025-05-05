// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19; // Use an appropriate version

import {Script, console} from "forge-std/Script.sol";
import {ChatBot} from "../src/ChatBot.sol";

contract DeployChatBot is Script {
    function run() external {
        // --- Load Configuration ---
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        string memory siweDomain = vm.envString("SIWE_DOMAIN");
        string memory roflAppIdString = vm.envString("ROFL_APP_ID"); // Read as string (hex string expected, e.g., 0x...)
        address initialOracle = vm.envAddress("INITIAL_ORACLE_ADDRESS");

        // --- Validate Configuration ---
        if (deployerPrivateKey == 0) {
            revert("PRIVATE_KEY environment variable not set");
        }
        if (bytes(siweDomain).length == 0) {
            revert("SIWE_DOMAIN environment variable not set");
        }
        
        // --- Process ROFL App ID ---
        // Remove 0x prefix if present
        if (bytes(roflAppIdString).length >= 2 && bytes(roflAppIdString)[0] == "0" && bytes(roflAppIdString)[1] == "x") {
            // Create a new string without the 0x prefix
            bytes memory strBytes = bytes(roflAppIdString);
            bytes memory result = new bytes(strBytes.length - 2);
            for (uint i = 2; i < strBytes.length; i++) {
                result[i - 2] = strBytes[i];
            }
            roflAppIdString = string(result);
        }
        
        // Validate hex string length (should be 42 characters for 21 bytes)
        if (bytes(roflAppIdString).length != 42) {
            revert("ROFL_APP_ID must be exactly 42 hex characters (21 bytes)");
        }
        
        // Parse hex string to bytes
        bytes memory roflAppIdBytes = vm.parseBytes(string(abi.encodePacked("0x", roflAppIdString)));
        
        // Double-check parsed bytes length
        if (roflAppIdBytes.length != 21) {
            revert("ROFL_APP_ID parsed to incorrect byte length");
        }
        
        if (initialOracle == address(0)) {
            revert("INITIAL_ORACLE_ADDRESS environment variable not set");
        }

        // --- Convert bytes to bytes21 ---
        bytes21 roflAppId;
        assembly {
            // Add 0x20 (32 bytes) to skip the length field of the bytes array
            // Then load the bytes from that position. mload reads 32 bytes,
            // but assigning to bytes21 should truncate correctly.
            roflAppId := mload(add(roflAppIdBytes, 0x20))
        }


        // --- Deployment ---
        vm.startBroadcast(deployerPrivateKey);

        ChatBot chatBot = new ChatBot(siweDomain, roflAppId, initialOracle); // Pass bytes21

        vm.stopBroadcast();

        // --- Logging ---
        console.log("ChatBot contract deployed to:", address(chatBot));
        console.log("--- Constructor Arguments Used ---");
        console.log("  SIWE Domain:", siweDomain);
        console.logBytes21(roflAppId); // Log bytes21 correctly
        console.log("  Initial Oracle:", initialOracle);
        console.log("---------------------------------");
    }
}
