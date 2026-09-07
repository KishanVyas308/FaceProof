# FaceProof — Face ID + Blockchain Verification

FaceProof is an end-to-end visual verification pipeline that detects and encodes a face from an input photo, finds a real matching social media post via genuine reverse-image search, and writes that match to a blockchain as a tamper-evident, verifiable record.

---

## Demonstration Video

**[Watch the full end-to-end continuous run on YouTube](https://youtu.be/demo-video-link-placeholder)**

---

## Problem Statement

When a face appears across public social media, proving where it was posted currently relies on manual reverse searches and screenshots that are easily faked, disputed, or deleted. Conventional search tools also stop at visual links without performing deep facial verification to confirm whether the faces genuinely match. Furthermore, there is no decentralized, tamper-evident way to permanently record that a match was discovered at a specific point in time. FaceProof solves this by automating real-time facial verification and anchoring an immutable, cryptographic proof of the match directly onto the blockchain.

## Solution Summary

**FaceProof** solves this challenge by building an autonomous, end-to-end CLI pipeline that bridges deep-learning face recognition, live reverse-image search, and decentralized blockchain verification:

- ✦ **Face Detection & Encoding**: Detects faces from an input photo (or live webcam frame) and extracts a 512-dimensional L2-normalized embedding vector using pretrained deep-learning models (InsightFace SCRFD + ArcFace).
- ✦ **Genuine Reverse-Image Search**: Executes live, un-hardcoded visual reverse-image searches across the web via the SerpApi Google Lens engine, filtering candidates to recognized social media platforms (Instagram, X/Twitter, Facebook, LinkedIn, Reddit, TikTok, YouTube).
- ✦ **Candidate Verification & Matching**: Downloads candidate post images, detects faces in candidate media, and computes cosine similarity against an empirical decision threshold (`MATCH_THRESHOLD = 0.45`) to confirm genuine identity alignment.
- ✦ **Tamper-Evident Blockchain Registry**: Generates a canonical, deterministic verification record (including image hashes, match status, similarity confidence, and source URL), computes its 32-byte SHA-256 cryptographic digest, and submits it to a Solidity smart contract (`VerificationRegistry`) deployed on the **Ethereum Sepolia** testnet.
- ✦ **Privacy-Preserving Proof-of-Existence**: Biometric vector embeddings and raw images remain strictly local; only cryptographic checksums and minimal provenance metadata are stored on-chain, preventing permanent biometric exposure while enabling mathematical third-party auditability on Etherscan.
- ✦ **Self-Contained CLI Pipeline**: Requires no web hosting or UI server; executes cleanly in the terminal with real-time step-by-step progress logging (`[1/14]` through `[14/14]`), unit test coverage, and offline simulation fallback.

---

## Architecture

```
[ Input Photo / Camera Frame ]
            │
            ▼
┌───────────────────────────────────────────────┐
│ Layer 1: Input / Camera Validation            │
│  - PIL Header Verification & Staging          │
│  - Compute Input SHA-256                      │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ Layer 2: Face Detection & Encoding            │
│  - Pretrained InsightFace (buffalo_l/ArcFace) │
│  - Extract 512-d L2-Normalized Embedding      │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ Layer 3: Genuine Reverse Image Search         │
│  - SerpApi Google Lens Engine                 │
│  - Live visual match discovery                │
│  - Filter to social media allowlist           │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ Layer 4: Candidate Image Retrieval (Top-3)    │
│  - Direct image & thumbnail download          │
│  - Multi-candidate fallback & wall bypass     │
│  - Compute Candidate SHA-256                  │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ Layer 5: Multi-Candidate Similarity Ranking   │
│  - Candidate face detection & embedding       │
│  - Cosine similarity: dot(A, B) / (||A||*||B||)│
│  - Select best match vs MATCH_THRESHOLD (0.45)│
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ Layer 6: Verification Record Hashing          │
│  - Canonical deterministic JSON serialization │
│  - Compute 32-byte SHA-256 fingerprint        │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ Layer 7: Blockchain Registry (Sepolia)        │
│  - Submit recordHash + metadata to registry   │
│  - Immutable transaction receipt on-chain     │
└───────────────────────────────────────────────┘
```

---

## Full Pipeline Description (14-Step Execution Flow)

During execution, FaceProof outputs a step-by-step progress trace printed immediately in real time:

1. `[1/14]` **Input image loaded**: Validates image headers, stages working file to `./tmp/run_<timestamp>/input.jpg`, and computes its SHA-256 checksum.
2. `[2/14]` **Face detected**: Detects faces with RetinaFace / SCRFD; enforces zero-face and multi-face policies (selects primary subject with largest bounding box).
3. `[3/14]` **Face embedding generated**: Extracts 512-dimensional ArcFace vector and applies L2 normalization.
4. `[4/14]` **Running reverse image search**: Submits image to SerpApi's Google Lens engine for genuine visual search.
5. `[5/14]` **Candidate found**: Filters visual matches against allowed social-media platforms (Instagram, X/Twitter, Facebook, LinkedIn, Reddit, TikTok, etc.).
6. `[6/14]` **Candidate image retrieved**: Downloads images for top candidates (evaluating up to 3 accessible candidates) with automated thumbnail fallback.
7. `[7/14]` **Candidate face detected**: Runs detection on candidate images; supports multi-face candidate posts.
8. `[8/14]` **Similarity computed**: Calculates cosine similarity across candidates and selects highest-similarity match.
9. `[9/14]` **Decision**: Compares score against `MATCH_THRESHOLD` (0.45) to determine MATCH or NO MATCH.
10. `[10/14]` **Verification record built**: Constructs structured metadata JSON excluding sensitive raw biometrics.
11. `[11/14]` **Record hash**: Deterministically serializes record (sorted keys, compact separators) and computes SHA-256 digest.
12. `[12/14]` **Submitting transaction to Sepolia**: Builds, signs, and broadcasts transaction to `VerificationRegistry` contract.
13. `[13/14]` **Transaction confirmed**: Awaits on-chain confirmation receipt on Ethereum Sepolia testnet.
14. `[14/14]` **Verification complete**: Formats direct Sepolia Etherscan transaction link for independent verification.

---

## Tech Stack

- **Machine Learning / Vision**: InsightFace (`buffalo_l` pretrained pack), ONNX Runtime, OpenCV, Pillow, NumPy
- **Reverse Image Search**: SerpApi (Google Lens Engine API)
- **Smart Contract**: Solidity (`^0.8.20`), Remix IDE, MetaMask
- **Blockchain Network**: Ethereum Sepolia Testnet
- **Web3 Integration**: `web3.py`, `eth-account`
- **Testing & Environment**: `pytest`, `python-dotenv`, `uv`

---

## Setup Instructions

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12 (Python 3.11 recommended)
- `uv` (recommended) or standard `pip`
- A SerpApi account and API key from [serpapi.com](https://serpapi.com)
- An Ethereum Sepolia RPC endpoint (from [Alchemy](https://alchemy.com) or public node `https://ethereum-sepolia-rpc.publicnode.com`)
- A dedicated testnet-only wallet holding Sepolia test ETH (obtain free from [sepoliafaucet.com](https://sepoliafaucet.com))

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Configure your environment keys in `.env`:
```ini
SERPAPI_KEY=your_live_serpapi_key
SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY
WALLET_PRIVATE_KEY=0xyour_dedicated_testnet_private_key
CONTRACT_ADDRESS=0xyour_deployed_verification_registry_address
SIMULATE_BLOCKCHAIN=false
```

### 3. Installation
Using `uv`:
```bash
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```
Or using standard `pip`:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Smart Contract Deployment

You can deploy the `VerificationRegistry` contract to Sepolia using our automated 1-click deploy script:
```bash
python scripts/deploy.py
```
*This script connects to Sepolia via your configured RPC and wallet, deploys [`contracts/VerificationRegistry.sol`](contracts/VerificationRegistry.sol), awaits confirmation, and automatically updates `.env` and [`config/contract.json`](config/contract.json) with the deployed contract address.*

Alternatively, deploy manually using [Remix IDE](https://remix.ethereum.org) by opening [`contracts/VerificationRegistry.sol`](contracts/VerificationRegistry.sol) with Injected Provider (MetaMask) on Sepolia, and paste the deployed address into `CONTRACT_ADDRESS` in `.env`.

---

## How to Run

### Standard File Verification
```bash
python main.py --image path/to/your_photo.jpg
```

### Webcam Capture Mode
```bash
python main.py --webcam
```

### Dry Run / Offline Simulation Mode
If running without live Sepolia testnet gas or evaluating offline:
```bash
python main.py --image path/to/your_photo.jpg --simulate
```

### Look Up an Existing Transaction on Sepolia
```bash
python main.py --lookup 0xYOUR_TRANSACTION_HASH
```

### Custom Match Threshold & Candidate Search Depth
You can adjust the similarity match sensitivity and candidate search depth:
```bash
python main.py --image path/to/photo.jpg --threshold 0.40 --max-candidates 10
```

### Running the Automated Test Suite
FaceProof includes unit and integration tests covering hashing determinism, similarity calculations, verification record serialization, input validation, and domain filtering:
```bash
pytest -v
```

---

## Example CLI Output

```
[1/14] Input image loaded: input.jpg (sha256: a1b2c3d4e5f6...)
[2/14] Face detected: 1 face, det_score=0.98
[3/14] Face embedding generated (512-d)
[4/14] Running reverse image search via SerpApi (Google Lens)...
[5/14] 5 candidate(s) found on allowed social platforms (evaluating top candidates)
[6/14] Candidate image retrieved: https://www.instagram.com/p/example/ (sha256: d4e5f6a1b2c3...)
[7/14] Candidate face detected: 1 face(s) (from candidate #1)
[8/14] Similarity computed: 0.71 (Confidence: 91.2%)
[9/14] Decision: MATCH (score=0.71 / 91.2%, threshold=0.45)
[10/14] Verification record built (verification_record.json)
[11/14] Record hash: 7f8e9d0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e
[12/14] Submitting transaction to Sepolia...
[13/14] Transaction confirmed: 0xabc123456789abcdef0123456789abcdef0123456789abcdef0123456789abcd
[14/14] Verification complete. View: https://sepolia.etherscan.io/tx/0xabc123456789abcdef0123456789abcdef0123456789abcdef0123456789abcd

=================================================================
                 FACEPROOF VERIFICATION SUCCESS                  
=================================================================
 Pipeline Version        : 0.1.0
 Run Directory           : /path/to/FaceProof-GOA/tmp/run_1725660000000
 Input SHA-256           : a1b2c3d4e5f6...
 Candidate URL           : https://www.instagram.com/p/example/
 Candidate SHA-256       : d4e5f6a1b2c3...
 Similarity Score        : 0.71 (Confidence: 91.2%)
 Match Confidence        : 91.2%
 Match Threshold         : 0.45 (75.0% Confidence)
 Match Decision          : MATCH
 Record Hash             : 7f8e9d0a1b2c...
 Sepolia Tx Hash         : 0xabc123456...
 Explorer URL            : https://sepolia.etherscan.io/tx/0xabc123...
=================================================================
```

---

## Smart Contract Details

- **Contract Name**: `VerificationRegistry`
- **Source Code**: [`contracts/VerificationRegistry.sol`](contracts/VerificationRegistry.sol)
- **Target Network**: Ethereum Sepolia Testnet (Chain ID: 11155111)
- **Functions**:
  - `submitVerification(bytes32 recordHash, string calldata metadata)`: Appends record hash, sender address, block timestamp, and lightweight non-biometric provenance metadata (status and candidate post URL); emits `VerificationSubmitted`.
  - `getVerificationCount()`: Returns total number of registered records.
  - `getVerification(uint256 id)`: Returns record details for a given record ID.
  - `getVerificationIdsByHash(bytes32 recordHash)`: Returns record IDs for a matching record hash.

---

## Blockchain Storage: Why Hashes, Not Raw Data

Storing raw biometric vectors (embeddings) or full-resolution photos on an immutable public ledger is a severe privacy violation and creates permanent, unrevocable surveillance risks. 

FaceProof implements **cryptographic proof-of-existence**:
1. All biometric calculations and 512-d face embeddings remain strictly in transient local memory and are never transmitted over the network or saved on-chain.
2. The verification record contains only non-sensitive structured metadata (`input_image_sha256`, `candidate_image_sha256`, `candidate_source_url`, `similarity_score`, `match_status`, `timestamp`).
3. The primary on-chain proof is the **32-byte SHA-256 cryptographic digest** of this canonical JSON, submitted to `VerificationRegistry.submitVerification()`.
4. A minimal, non-biometric provenance string (`status=<status>|url=<candidate_url>`) is passed to the contract's `metadata` parameter for fast lookup and transparency without exposing biometric data.
5. Anyone possessing the local verification JSON record can independently calculate its SHA-256 hash and verify that it matches the on-chain `recordHash` registered at that exact block number and timestamp.

---

## Known Limitations

1. **Face Recognition Model Variance**:
   - Extreme angles, low lighting, heavy occlusion (sunglasses, masks), or significant age gaps reduce cosine similarity.
   - `MATCH_THRESHOLD = 0.45` is an experimentally chosen prototype parameter; it is not a forensic or legal standard.
2. **Reverse Image Search Indexing & Rate Limits**:
   - Google Lens coverage depends on public web crawlers. Private accounts, ephemeral stories, and recent unindexed uploads will not return candidates.
   - Public figures and widely shared images surface readily; private individuals' newly taken photos typically return no visual matches.
   - SerpApi free tier has monthly query quotas.
3. **Platform Access Controls**:
   - Platforms that restrict automated downloads or require login walls may prevent downloading full-resolution candidate media; FaceProof uses thumbnail fallback and multi-candidate retrieval, and gracefully records `candidate_unavailable` if all sources are blocked.

---

## Privacy Considerations

- **No KYC / Identity Claims**: FaceProof tests visual and embedding similarity between two photos. It does **not** identify real-world legal identities.
- **On-Chain Provenance**: The on-chain metadata records only non-biometric post provenance (match status and truncated public post URL). Biometric embeddings and private user data are strictly excluded from on-chain transactions.
- **Credential Hygiene**: `.env` is gitignored. Private keys and API keys are never printed to console, written to logs, or committed to git.
- **Dedicated Testnet Wallet**: Only testnet wallets with zero mainnet funds should ever be used.

---

## Future Improvements

- **Broader Candidate Set Reranking**: Expand candidate retrieval beyond top-3 to larger candidate batches with parallel downloading.
- **ZK-proofs of Facial Similarity**: Zero-Knowledge proofs to cryptographically verify face matching on-chain without revealing candidate URLs.
- **Decentralized Storage Integration**: IPFS / Filecoin for decentralized verification record hosting.

---

## Hackathon Task Mapping Table

| Requirement | Implementation Component | File Reference | Pipeline Step |
|---|---|---|---|
| **Detect and encode a face** | RetinaFace / ArcFace L2-normalized 512-d embeddings | [`face/encoder.py`](face/encoder.py) | Steps `[2/14]`, `[3/14]` |
| **Find real matching post via genuine reverse-image search** | SerpApi Google Lens live visual match API call | [`reverse_search/serpapi_client.py`](reverse_search/serpapi_client.py) | Steps `[4/14]`, `[5/14]` |
| **Upload match data to blockchain** | Deterministic JSON hashing + Web3 Sepolia contract submission | [`verification/record.py`](verification/record.py) & [`blockchain/client.py`](blockchain/client.py) | Steps `[10/14]` – `[14/14]` |
| **No website or hosting needed** | Pure CLI application | [`main.py`](main.py) | End-to-end CLI |
| **Source on GitHub** | Clean structure, gitignored secrets, setup docs | Repository root | Entire codebase |
| **How to run** | Setup instructions, arguments, dry-run flags | [`README.md`](README.md) | Setup & Run sections |
| **Blockchain used + limitations** | Sepolia testnet details, gas considerations, privacy & model limits | [`README.md`](README.md) | Contract & Limitations sections |
| **Unedited end-to-end screen recording** | Step-by-step recording guide & checklist | [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) | Recording script |
