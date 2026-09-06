// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title VerificationRegistry
 * @dev Simple, tamper-evident registry for storing SHA-256 verification record hashes
 *      and associated metadata on Ethereum Sepolia.
 */
contract VerificationRegistry {
    struct VerificationEntry {
        bytes32 recordHash;
        string metadata;
        uint256 timestamp;
        address submitter;
    }

    VerificationEntry[] public verifications;
    mapping(bytes32 => uint256[]) private hashToVerificationIds;

    event VerificationSubmitted(
        address indexed submitter,
        bytes32 indexed recordHash,
        uint256 timestamp,
        uint256 indexed id
    );

    /**
     * @notice Submits a verification record hash and metadata string.
     * @param recordHash The SHA-256 hash of the canonical verification JSON record.
     * @param metadata Non-sensitive metadata string (e.g. source URL or match status).
     * @return id The index of the newly stored verification entry.
     */
    function submitVerification(
        bytes32 recordHash,
        string calldata metadata
    ) external returns (uint256 id) {
        require(recordHash != bytes32(0), "Invalid record hash");

        id = verifications.length;
        verifications.push(VerificationEntry({
            recordHash: recordHash,
            metadata: metadata,
            timestamp: block.timestamp,
            submitter: msg.sender
        }));

        hashToVerificationIds[recordHash].push(id);

        emit VerificationSubmitted(msg.sender, recordHash, block.timestamp, id);
    }

    /**
     * @notice Retrieves the total number of recorded verifications.
     */
    function getVerificationCount() external view returns (uint256) {
        return verifications.length;
    }

    /**
     * @notice Retrieves a specific verification entry by ID.
     */
    function getVerification(uint256 id) external view returns (
        bytes32 recordHash,
        string memory metadata,
        uint256 timestamp,
        address submitter
    ) {
        require(id < verifications.length, "Index out of bounds");
        VerificationEntry storage entry = verifications[id];
        return (entry.recordHash, entry.metadata, entry.timestamp, entry.submitter);
    }

    /**
     * @notice Returns all entry IDs associated with a specific record hash.
     */
    function getVerificationIdsByHash(bytes32 recordHash) external view returns (uint256[] memory) {
        return hashToVerificationIds[recordHash];
    }
}
