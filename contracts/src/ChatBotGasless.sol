// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Subcall} from "@oasisprotocol/sapphire-contracts/contracts/Subcall.sol";
import {SiweAuth} from "@oasisprotocol/sapphire-contracts/contracts/auth/SiweAuth.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {encryptCallData} from "@oasisprotocol/sapphire-contracts/contracts/CalldataEncryption.sol";
import {EIP155Signer} from "@oasisprotocol/sapphire-contracts/contracts/EIP155Signer.sol";
import {EthereumUtils} from "@oasisprotocol/sapphire-contracts/contracts/EthereumUtils.sol";

struct Answer {
    uint256 promptId;
    string answer;
}

struct EthereumKeypair {
    address addr;
    bytes32 secretKey;
    uint64 nonce;
}

interface IChatBot {
    function _appendPrompt(address user, string calldata prompt) external;
}

contract ChatBotGasless is SiweAuth, Ownable {
    // --- State Variables ---
    mapping(address => string[]) private _prompts;
    mapping(address => Answer[]) private _answers;
    address public oracle;
    bytes21 public roflAppID;
    string private systemPrompt;

    EthereumKeypair private kp; // Internal signer keypair

    // --- Events ---
    event PromptSubmitted(address indexed sender);
    event AnswerSubmitted(address indexed sender);
    event SignerInitialized(address indexed signerAddress);
    event TransactionProxied(address indexed target, bool success);
    event ContractFunded(address indexed funder, uint256 amount);
    event WithdrawalCompleted(address indexed recipient, uint256 amount);

    // --- Errors from ChatBot ---
    error InvalidPromptId();
    error PromptAlreadyAnswered();
    error UnauthorizedUserOrOracle();
    error UnauthorizedUser();
    error UnauthorizedOracle();
    error NotOwnerOrOracle();

    error Gasless__FundingAmountZero();
    error Gasless__SignerNotInitialized();
    error Gasless__CallerNotSignerAddress();
    error ChatBotGasless__UserMismatch();
    error ChatBotGasless__ContractWithdrawFailed();
    error ChatBotGasless__InsufficientContractBalance();
    error UnexpectedTargetContract();
    error InvalidProxiedCallSelector();
    error ProxiedCallFailed();


    constructor(
        string memory domain,
        bytes21 inRoflAppID,
        address inOracle,
        address inOwner
    ) SiweAuth(domain) Ownable(inOwner) payable {
        roflAppID = inRoflAppID;
        oracle = inOracle;

        (address signerAddr, bytes32 secretKey) = EthereumUtils.generateKeypair();
        kp = EthereumKeypair({
            addr: signerAddr,
            secretKey: secretKey,
            nonce: 0
        });
        emit SignerInitialized(signerAddr);

        if (msg.value > 0) {
            emit ContractFunded(msg.sender, msg.value);
        }
    }


    // --- Modifiers ---
    modifier onlyUser(bytes memory authToken, address addr) {
        if (msg.sender != addr) {
            address msgSender = authMsgSender(authToken);
            if (msgSender != addr) {
                revert UnauthorizedUser();
            }
        }
        _;
    }

    modifier onlyUserOrOracle(bytes memory authToken, address addr) {
        if (msg.sender != addr && msg.sender != oracle) {
            address msgSender = authMsgSender(authToken);
            if (msgSender != addr) {
                revert UnauthorizedUserOrOracle();
            }
        }
        _;
    }

    modifier onlyOwnerOrOracle() {
        if (msg.sender != owner() && msg.sender != oracle) {
            revert NotOwnerOrOracle();
        }
        _;
    }

    modifier onlyOracle() {
        if (msg.sender != oracle) {
            revert UnauthorizedOracle();
        }
        _;
    }

    modifier onlyTEE(bytes21 appId) {
        Subcall.roflEnsureAuthorizedOrigin(appId);
        _;
    }

    // --- Receive Ether Function ---
    receive() external payable {
        if (msg.value == 0) revert Gasless__FundingAmountZero();
        emit ContractFunded(msg.sender, msg.value);
    }

    // --- Owner Withdrawal from Contract ---
    function withdraw(uint256 amount) external onlyOwner {
        if (amount == 0) revert Gasless__FundingAmountZero();
        if (address(this).balance < amount) revert ChatBotGasless__InsufficientContractBalance();
        (bool success, ) = owner().call{value: amount}("");
        if (!success) revert ChatBotGasless__ContractWithdrawFailed();
        emit WithdrawalCompleted(owner(), amount);
    }

    // --- Internal Prompt Logic ---
    function _appendPrompt(address user, string memory prompt) public {
        if (msg.sender != address(this)) revert Gasless__CallerNotSignerAddress();
        _prompts[user].push(prompt);
        emit PromptSubmitted(user);
    }

    // --- Gasless Transaction Preparation (View Function) ---
    function appendPromptGasless(bytes memory authToken, address userAddress, string memory prompt)
        external
        view
        onlyUser(authToken, userAddress)
        returns (bytes memory signedTxData)
    {
        address siweUser = authMsgSender(authToken);
        if (siweUser != userAddress) revert ChatBotGasless__UserMismatch();

        bytes memory callDataForAppend = abi.encodeWithSelector(
            // IChatBot._appendPrompt.selector,
            this._appendPrompt.selector,
            userAddress,
            prompt
        );

        // originalUser, targetContract, actionCallData
        bytes memory dataForProxyFunction = abi.encode(address(this), callDataForAppend);

        return EIP155Signer.sign(
            kp.addr,
            kp.secretKey,
            EIP155Signer.EthTx({
                nonce: kp.nonce,
                gasPrice: 100_000_000_000, // 100 gwei; consider making this configurable or dynamic
                gasLimit: 500_000,       // Generous limit; refine based on actual usage
                to: address(this),
                value: 0,
                data: encryptCallData(abi.encodeCall(this.proxy, (dataForProxyFunction))),
                // data: abi.encodeCall(this.proxy, (dataForProxyFunction)), // plain tx
                chainId: block.chainid
            })
        );
    }

    // --- Proxy Execution Function ---
    function proxy(bytes memory data) external payable {
        if (msg.sender != kp.addr) revert Gasless__CallerNotSignerAddress();

        (address target, bytes memory actionCallData) = abi.decode(
            data,
            (address, bytes)
        );

        if (target != address(this)) {
            revert UnexpectedTargetContract();
        }

        if (bytes4(actionCallData) != IChatBot._appendPrompt.selector) {
            revert InvalidProxiedCallSelector();
        }

        (bool success, ) = address(this).call{value: msg.value}(actionCallData); // Calls _appendPromptInternal

        emit TransactionProxied(target, success);

        if (!success) {
            revert ProxiedCallFailed();
        }
        kp.nonce += 1;
    }


    // --- Standard ChatBot Functions ---
    function clearPrompt(bytes memory authToken) external {
        address user = authMsgSender(authToken);
        // require(user != address(0), "Invalid user from token"); // Optional: Add if strict check for non-zero user is needed
        delete _prompts[user];
        delete _answers[user];
    }

    function getPromptsCount(bytes memory authToken, address addr)
        external view
        onlyUserOrOracle(authToken, addr)
        returns (uint256)
    {
        return _prompts[addr].length;
    }

    function getPrompts(bytes memory authToken, address addr)
        external view
        onlyUserOrOracle(authToken, addr)
        returns (string[] memory)
    {
        return _prompts[addr];
    }

    function getAnswers(bytes memory authToken, address addr)
        external view
        onlyUserOrOracle(authToken, addr)
        returns (Answer[] memory)
    {
        return _answers[addr];
    }

    function setOracle(address addr) external onlyTEE(roflAppID) {
        oracle = addr;
    }

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

    function setSystemPrompt(string memory _newPrompt) external onlyOwner {
        systemPrompt = _newPrompt;
    }

    function getSystemPrompt() external view onlyOwnerOrOracle returns (string memory) {
        return systemPrompt;
    }

    // --- Gasless Utility Functions ---
    function getSignerAddress() external view returns (address) {
        return kp.addr;
    }

    function getNonce() external view returns (uint64) {
        return kp.nonce;
    }
}
