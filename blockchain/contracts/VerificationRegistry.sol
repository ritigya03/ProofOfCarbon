// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/**
 * @title VerificationRegistry
 * @notice On-chain audit log for ProofOfCarbon AI verification results.
 *         Each record stores a project's trust score, risk level, and an
 *         IPFS hash pointing to the full AI-generated analysis report.
 * @dev Deployed on Polygon Amoy testnet.
 */
contract VerificationRegistry {

    // ── Enums ────────────────────────────────────────────────────────────────

    enum RiskLevel { LOW, MEDIUM, HIGH, CRITICAL }

    // ── Structs ──────────────────────────────────────────────────────────────

    struct VerificationRecord {
        uint256 id;             // Auto-incremented record ID
        string  projectName;    // Name of the carbon credit project
        string  companyName;    // Submitting company / entity
        uint8   trustScore;     // 0–100 AI-generated trust score
        RiskLevel riskLevel;    // LOW / MEDIUM / HIGH / CRITICAL
        string  ipfsHash;       // IPFS CID of full analysis JSON
        address verifier;       // Address that submitted the record
        uint256 timestamp;      // Block timestamp of submission
    }

    // ── State ────────────────────────────────────────────────────────────────

    uint256 private _nextId;

    /// @notice All verification records, indexed by ID (0-based)
    mapping(uint256 => VerificationRecord) public records;

    /// @notice Total number of records stored
    uint256 public totalRecords;

    // ── Events ───────────────────────────────────────────────────────────────

    event VerificationLogged(
        uint256 indexed id,
        string  projectName,
        string  companyName,
        uint8   trustScore,
        RiskLevel riskLevel,
        string  ipfsHash,
        address indexed verifier,
        uint256 timestamp
    );

    // ── Write ─────────────────────────────────────────────────────────────────

    /**
     * @notice Log a new verification result on-chain.
     * @param projectName  Name of the project being verified.
     * @param companyName  Name of the company that submitted the claim.
     * @param trustScore   AI trust score (0–100). Must be ≤ 100.
     * @param riskLevel    Risk classification (0=LOW, 1=MEDIUM, 2=HIGH, 3=CRITICAL).
     * @param ipfsHash     IPFS CID of the full analysis JSON report.
     * @return id          The ID assigned to this record.
     */
    function logVerification(
        string  calldata projectName,
        string  calldata companyName,
        uint8            trustScore,
        RiskLevel        riskLevel,
        string  calldata ipfsHash
    ) external returns (uint256 id) {
        require(trustScore <= 100, "Trust score must be 0-100");
        require(bytes(projectName).length > 0, "Project name required");

        id = _nextId++;

        records[id] = VerificationRecord({
            id:          id,
            projectName: projectName,
            companyName: companyName,
            trustScore:  trustScore,
            riskLevel:   riskLevel,
            ipfsHash:    ipfsHash,
            verifier:    msg.sender,
            timestamp:   block.timestamp
        });

        totalRecords++;

        emit VerificationLogged(
            id,
            projectName,
            companyName,
            trustScore,
            riskLevel,
            ipfsHash,
            msg.sender,
            block.timestamp
        );
    }

    // ── Read ──────────────────────────────────────────────────────────────────

    /**
     * @notice Fetch a single verification record by its ID.
     * @param id The record ID to retrieve.
     */
    function getRecord(uint256 id)
        external
        view
        returns (VerificationRecord memory)
    {
        require(id < totalRecords, "Record does not exist");
        return records[id];
    }

    /**
     * @notice Fetch all verification records (paginated).
     * @param offset  Starting index.
     * @param limit   Maximum number of records to return.
     * @return page   Array of VerificationRecord structs.
     */
    function getRecords(uint256 offset, uint256 limit)
        external
        view
        returns (VerificationRecord[] memory page)
    {
        if (offset >= totalRecords) return page;

        uint256 end = offset + limit;
        if (end > totalRecords) end = totalRecords;

        page = new VerificationRecord[](end - offset);
        for (uint256 i = offset; i < end; i++) {
            page[i - offset] = records[i];
        }
    }

    /**
     * @notice Fetch all records submitted by a specific address.
     * @param verifier  The address to filter by.
     */
    function getRecordsByVerifier(address verifier)
        external
        view
        returns (VerificationRecord[] memory)
    {
        uint256 count = 0;
        for (uint256 i = 0; i < totalRecords; i++) {
            if (records[i].verifier == verifier) count++;
        }

        VerificationRecord[] memory result = new VerificationRecord[](count);
        uint256 idx = 0;
        for (uint256 i = 0; i < totalRecords; i++) {
            if (records[i].verifier == verifier) {
                result[idx++] = records[i];
            }
        }
        return result;
    }
}
