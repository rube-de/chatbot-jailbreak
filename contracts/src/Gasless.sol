// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { encryptCallData } from "@oasisprotocol/sapphire-contracts/contracts/CalldataEncryption.sol";
import { EIP155Signer } from "@oasisprotocol/sapphire-contracts/contracts/EIP155Signer.sol";
import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";
import { Sapphire } from "@oasisprotocol/sapphire-contracts/contracts/Sapphire.sol";

struct EthereumKeypair {
    address addr;
    bytes32 secret;
    uint64 nonce;
}

/// @title Gasless Proxy Contract (On-Chain Key Generation)
/// @notice Enables gasless transactions and admin-controlled withdrawals using an internal signer.
contract Gasless is Ownable {
    EthereumKeypair private kp;

    event SignerInitialized(address indexed signerAddress);
    event TransactionProxied(address indexed target, address indexed originalUser, bool success);
    event SignerFunded(address indexed funder, uint256 amount);
    event WithdrawalTxCreated(address indexed owner, uint256 amount);
    
    // Custom errors for Gasless
    error Gasless__RandomBytesLengthError(uint256 actual, uint256 expected);
    error Gasless__InitialFundingTransferFailed();
    error Gasless__FundingAmountZero();
    error Gasless__SignerNotInitialized();
    error Gasless__SignerFundingTransferFailed();
    error Gasless__CallerNotSignerAddress();
    error Gasless__NonceTooLow(uint64 provided, uint64 current);


    /// @notice Initializes Ownable, generates the internal signing keypair, and funds the signer address with any value sent on deployment.
    constructor(address initialOwner) Ownable(initialOwner) payable {
        bytes memory rand = Sapphire.randomBytes(32, abi.encodePacked("GaslessProxySeed"));
        if (rand.length != 32) revert Gasless__RandomBytesLengthError(rand.length, 32);

        (bytes memory publicKey, bytes memory secretKey) = Sapphire.generateSigningKeyPair(
            Sapphire.SigningAlg.Ed25519Pure,
            rand
        );
        // Derive an Ethereum-compatible address from the Ed25519 public key
        address signerAddr = address(uint160(uint256(keccak256(publicKey))));
        bytes32 signerSecret;
        assembly {
            signerSecret := mload(add(secretKey, 32))
        }
        kp = EthereumKeypair({
            addr: signerAddr,
            secret: signerSecret,
            nonce: 0
        });
        emit SignerInitialized(signerAddr);

        if (msg.value > 0) {
            (bool success, ) = payable(kp.addr).call{value: msg.value}("");
            if (!success) revert Gasless__InitialFundingTransferFailed();
            emit SignerFunded(msg.sender, msg.value);
        }
    }

    receive() external payable {
        if (msg.value == 0) revert Gasless__FundingAmountZero();
        if (kp.addr == address(0)) revert Gasless__SignerNotInitialized();
        (bool success, ) = payable(kp.addr).call{value: msg.value}("");
        if (!success) revert Gasless__SignerFundingTransferFailed();
        emit SignerFunded(msg.sender, msg.value);
    }

    /// @notice Allows anyone to send funds directly to the internal signer address.
    function fundSigner() external payable {
        if (msg.value == 0) revert Gasless__FundingAmountZero();
        if (kp.addr == address(0)) revert Gasless__SignerNotInitialized();
        (bool success, ) = payable(kp.addr).call{value: msg.value}("");
        if (!success) revert Gasless__SignerFundingTransferFailed();
        emit SignerFunded(msg.sender, msg.value);
    }

    /// @notice Creates a raw, signed Ethereum transaction to call the proxy function.
    function makeProxyTx(
        address userAddress,
        address targetContract,
        bytes memory targetCallData
    ) external view returns (bytes memory output) {
        if (kp.addr == address(0)) revert Gasless__SignerNotInitialized();

        bytes memory proxyCallData = abi.encode(userAddress, targetContract, targetCallData);

        EIP155Signer.EthTx memory tx = EIP155Signer.EthTx({
            nonce: kp.nonce,
            gasPrice: 100_000_000_000,
            gasLimit: 500000,
            to: address(this),
            value: 0,
            data: encryptCallData(abi.encodeCall(this.proxy, (proxyCallData))),
            chainId: block.chainid
        });

        return EIP155Signer.sign(kp.addr, kp.secret, tx);
    }

    /// @notice Executes the target contract call.
    function proxy(bytes memory data) external payable {
        if (msg.sender != kp.addr) revert Gasless__CallerNotSignerAddress();

        (address userAddress, address targetContract, bytes memory targetCallData) = abi.decode(
            data,
            (address, address, bytes)
        );

        (bool success, bytes memory returnData) = targetContract.call(targetCallData);

        emit TransactionProxied(targetContract, userAddress, success);

        if (!success) {
            assembly {
                revert(add(returnData, 32), mload(returnData))
            }
        }
        kp.nonce += 1;
    }

    /// @notice Creates a raw, signed transaction to withdraw funds FROM the signer address TO the owner.
    /// @dev Callable only by the owner. The owner must manually submit the returned transaction bytes.
    /// @param amount The amount of ROSE (in wei) to withdraw from the signer address.
    /// @param gasPrice The gas price (in wei) to use for the withdrawal transaction.
    /// @param nonce The nonce to use for the withdrawal transaction (must match signer's current nonce).
    /// @return signedTxData The RLP-encoded signed withdrawal transaction bytes.
    function createWithdrawalTx(uint256 amount, uint256 gasPrice, uint64 nonce)
        external
        onlyOwner
        returns (bytes memory signedTxData)
    {
        require(kp.addr != address(0), "Gasless: Signer not initialized");
        require(nonce >= kp.nonce, "Gasless: Provided nonce too low");

        EIP155Signer.EthTx memory withdrawalTx = EIP155Signer.EthTx({
            nonce: nonce,
            gasPrice: gasPrice,
            gasLimit: 21000,
            to: owner(),
            value: amount,
            data: bytes(""),
            chainId: block.chainid
        });

        signedTxData = EIP155Signer.sign(kp.addr, kp.secret, withdrawalTx);
        emit WithdrawalTxCreated(owner(), amount);
    }

    /// @notice Returns the address of the internally generated signer (where funds should be sent).
    function getSignerAddress() external view returns (address) {
        return kp.addr;
    }

    /// @notice Returns the current nonce of the signer keypair.
    function getNonce() external view returns (uint64) {
        return kp.nonce;
    }


}
