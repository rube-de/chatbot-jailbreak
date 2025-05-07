// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
pragma solidity ^0.8.24;

import {Subcall} from "@oasisprotocol/sapphire-contracts/contracts/Subcall.sol";
import {SiweAuth} from "@oasisprotocol/sapphire-contracts/contracts/auth/SiweAuth.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

struct Answer {
    uint256 promptId;
    string answer;
}

contract ChatBot is SiweAuth, Ownable {
contract ChatBot is SiweAuth, Ownable {
    mapping(address => string[]) private _prompts;
    mapping(address => Answer[]) private _answers;

    address public oracle;    // Oracle address running inside TEE.
    bytes21 public roflAppID; // Allowed app ID within TEE for managing allowed oracle address.

    address public gaslessProxyAddress;
    string private systemPrompt;

    event PromptSubmitted(address indexed sender);
    event AnswerSubmitted(address indexed sender);

    error InvalidPromptId();
    error PromptAlreadyAnswered();
    error UnauthorizedUserOrOracle();
    error UnauthorizedOracle();
    error NotOwnerOrOracle();
    error ChatBot__UnauthorizedProxy();

    modifier onlyGaslessProxy() {
        if (msg.sender != gaslessProxyAddress) {
            revert ChatBot__UnauthorizedProxy();
        }
        _;
    }

    // Sets up a chat bot smart contract.
    // @param domain is used for SIWE login on the frontend.
    // @param inRoflAppID is the attested ROFL app that is allowed to call setOracle().
    // @param inOracle only for testing, not attested; set the oracle address for accessing prompts.
    // @param initialOwner The initial owner of this contract.
    constructor(
        string memory domain,
        bytes21 inRoflAppID,
        address inOracle,
        address initialOwner
    ) SiweAuth(domain) Ownable(initialOwner) {
        roflAppID = inRoflAppID;
        oracle = inOracle;
    }

    function setGaslessProxy(address proxy) external onlyOwner {
        gaslessProxyAddress = proxy;
    }

    // For the user: checks whether authToken is a valid SIWE token
    // corresponding to the requested address.
    // For the oracle: checks whether the transaction or query was signed by the
    // oracle's private key accessible only within TEE.
    modifier onlyUserOrOracle(bytes memory authToken, address addr) {
        if (msg.sender != addr && msg.sender != oracle) {
            address msgSender = authMsgSender(authToken);
            if (msgSender != addr) {
                revert UnauthorizedUserOrOracle(); // Existing error, suitable here
            }
        }
        _;
    }

    /// @dev Throws if called by any account other than the owner or the oracle.
    modifier onlyOwnerOrOracle() {
        if (msg.sender != owner() && msg.sender != oracle) {
            revert NotOwnerOrOracle();
        }
        _;
    }

    // Checks whether the transaction or query was signed by the oracle's
    // private key accessible only within TEE.
    modifier onlyOracle() {
        if (msg.sender != oracle) {
            revert UnauthorizedOracle(); // Existing error, suitable here
        }
        _;
    }

    // Checks whether the transaction was signed by the ROFL's app key inside
    // TEE.
    modifier onlyTEE(bytes21 appId) {
        Subcall.roflEnsureAuthorizedOrigin(appId);
        _;
    }

    // Append the new prompt and request answer.
    // Called by the user via gasless proxy.
    function appendPrompt(address user, string memory prompt) external onlyGaslessProxy {
        _prompts[user].push(prompt);
        emit PromptSubmitted(user);
    }

    // Clears the conversation.
    // Called by the user.
    function clearPrompt() external {
        delete _prompts[msg.sender];
        delete _answers[msg.sender];
    }

    function getPromptsCount(bytes memory authToken, address addr)
        external view
        onlyUserOrOracle(authToken, addr)
        returns (uint256)
    {
        return _prompts[addr].length;
    }

    // Returns all prompts for a given user address.
    // Called by the user in the frontend and by the oracle to generate the answer.
    function getPrompts(bytes memory authToken, address addr)
        external view
        onlyUserOrOracle(authToken, addr)
        returns (string[] memory)
    {
        return _prompts[addr];
    }

    // Returns all answers for a given user address.
    // Called by the user.
    function getAnswers(bytes memory authToken, address addr)
        external view
        onlyUserOrOracle(authToken, addr)
        returns (Answer[] memory)
    {
        return _answers[addr];
    }

    // Sets the oracle address that will be allowed to read prompts and submit answers.
    // This setter can only be called within the ROFL TEE and the keypair
    // corresponding to the address should never leave TEE.
    function setOracle(address addr) external onlyTEE(roflAppID) {
        oracle = addr;
    }

    // Submits the answer to the prompt for a given user address.
    // Called by the oracle within TEE.
    function submitAnswer(string memory answer, uint256 promptId, address addr) external onlyOracle {
        if (promptId >= _prompts[addr].length) {
            revert InvalidPromptId();
        }
        if (_answers[addr].length > 0 && _answers[addr][_answers[addr].length - 1].promptId >= promptId) {
            revert PromptAlreadyAnswered();
        }
        _answers[addr].push(Answer({promptId: promptId, answer: answer}));
        emit AnswerSubmitted(addr);
    }

    /// @notice Sets the system prompt for the chatbot.
    /// @dev Can only be called by the owner.
    /// @param _newPrompt The new system prompt string.
    function setSystemPrompt(string memory _newPrompt) external onlyOwner {
        systemPrompt = _newPrompt;
    }

    /// @notice Gets the current system prompt.
    /// @dev Can only be called by the owner or the oracle.
    /// @return The current system prompt string.
    function getSystemPrompt() external view onlyOwnerOrOracle returns (string memory) {
        return systemPrompt;
    }
}
