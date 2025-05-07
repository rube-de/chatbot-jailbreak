// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import {Test, console} from "forge-std/Test.sol";
import {Answer, ChatBot} from "../src/ChatBot.sol";
import {Gasless} from "../src/Gasless.sol";
import {Subcall} from "@oasisprotocol/sapphire-contracts/contracts/Subcall.sol";

contract ChatBotTest is Test {
    ChatBot public chatBot;
    Gasless public gaslessProxy;
    address public user;
    address public _oracle;
    string public domain;

    function setUp() public {
        domain = "example.com";
        _oracle = address(0x123);
        user = address(0x456);
        bytes21 roflAppID = bytes21(0);
        chatBot = new ChatBot(domain, roflAppID, _oracle, user);

        // Deploy Gasless and set as proxy
        gaslessProxy = new Gasless{value: 1 ether}();
        vm.prank(chatBot.owner());
        chatBot.setGaslessProxy(address(gaslessProxy));
    }

    function test_appendPrompt_gasless() public {
        // Prepare calldata for ChatBot.appendPrompt(address,string)
        bytes memory callData = abi.encodeCall(chatBot.appendPrompt, (user, "Hello"));

        // Create signed tx using Gasless
        bytes memory proxyCallData = abi.encode(user, address(chatBot), callData);

        // Simulate the signer calling proxy
        address signer = gaslessProxy.getSignerAddress();
        vm.prank(signer);
        gaslessProxy.proxy(proxyCallData);

        // Assert prompt was added
        string[] memory prompts = chatBot.getPrompts("", user);
        assertEq(prompts.length, 1);
        assertEq(prompts[0], "Hello");

        // Assert nonce incremented
        assertEq(gaslessProxy.getNonce(), 1);
    }

    function test_clearPrompt() public {
        // Use gasless flow to append prompt
        bytes memory callData = abi.encodeCall(chatBot.appendPrompt, (user, "Hello"));
        bytes memory proxyCallData = abi.encode(user, address(chatBot), callData);
        address signer = gaslessProxy.getSignerAddress();
        vm.prank(signer);
        gaslessProxy.proxy(proxyCallData);

        vm.startPrank(user);
        chatBot.clearPrompt();
        string[] memory prompts = chatBot.getPrompts("", user);
        Answer[] memory answers = chatBot.getAnswers("", user);
        assertEq(prompts.length, 0);
        assertEq(answers.length, 0);
        vm.stopPrank();
    }

    function test_submitAnswer() public {
        // Use gasless flow to append prompt
        bytes memory callData = abi.encodeCall(chatBot.appendPrompt, (user, "Hello"));
        bytes memory proxyCallData = abi.encode(user, address(chatBot), callData);
        address signer = gaslessProxy.getSignerAddress();
        vm.prank(signer);
        gaslessProxy.proxy(proxyCallData);

        vm.startPrank(_oracle);
        chatBot.submitAnswer("Test answer", 0, user);
        Answer[] memory answers = chatBot.getAnswers("", user);
        assertEq(answers.length, 1);
        assertEq(answers[0].answer, "Test answer");
        assertEq(answers[0].promptId, 0);

        vm.expectRevert(ChatBot.PromptAlreadyAnswered.selector);
        chatBot.submitAnswer("Test answer too late", 0, user);
        vm.stopPrank();
    }

    function test_Revert_unauthorizedPromptAccess() public {
        vm.expectRevert(ChatBot.UnauthorizedUserOrOracle.selector);
        address unauthorizedUser = address(0);
        vm.startPrank(unauthorizedUser);
        chatBot.getPrompts("", user);
        vm.stopPrank();
    }

    function test_Revert_unauthorizedProxyCall() public {
        vm.expectRevert(ChatBot.ChatBot__UnauthorizedProxy.selector);
        // Direct call to appendPrompt should fail (not from proxy)
        chatBot.appendPrompt(user, "Unauthorized attempt");
    }
}
