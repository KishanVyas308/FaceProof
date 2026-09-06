# PROJECT_OVERVIEW.md — FaceProof (working name)

Hackathon: Hacker House Goa 2026
Challenge: "Face ID + Blockchain Verification"

This document is the team's development plan and implementation specification. It defines what gets built, in what order, and how each component connects to the next. It is not marketing copy — read it as a build checklist.

---

## LAYER 0 — Project Definition

### Problem we are solving
Given a photo of a face, there is no simple, tamper-evident way to record "this face was found to visually match a specific, publicly discoverable social-media post at this point in time." Manual reverse-image searching exists, but the result is not verifiable after the fact — screenshots can be edited, and there is no independent record of what was found or when.

### What the Hacker House task requires
1. Detect and encode a face from an input photo.
2. Find at least one real, matching social-media post using genuine reverse-image search (hardcoded results are disallowed).
3. Upload the match's data to a blockchain as a tamper-evident, verifiable record.
4. No website or hosting — the pipeline itself is judged.
5. Source code on GitHub with functionality, setup/run instructions, blockchain used, and known limitations documented.
6. An unedited screen recording of the full pipeline running end-to-end.

### What our system does
Takes one input image containing a face → detects and encodes the face → runs a genuine reverse-image search against that image → identifies a candidate social-media result → retrieves the candidate image where accessible → compares face embeddings → computes a similarity score and match decision → builds a verification record → hashes it → writes the hash and non-sensitive metadata to a Solidity smart contract on Ethereum Sepolia → returns the verification result plus the transaction hash.

### Explicitly out of scope
- [x] No web frontend or hosted service of any kind
- [x] No custom model training (pretrained models only)
- [x] No identity verification claims — this is a visual/face similarity tool, not a KYC or identity system
- [x] No bypassing of login walls, private accounts, or robots.txt restrictions to retrieve images
- [x] No storage of raw images or raw embeddings on-chain
- [x] No mainnet deployment — Sepolia testnet only
- [x] No mobile app

### Final expected output of the pipeline
A single CLI run that prints a step-by-step trace and ends with:
- Match decision (match / no match) and similarity score
- Candidate social-media URL
- Verification record JSON (saved locally)
- SHA-256 hash of that record
- Sepolia transaction hash
- A link/reference to view the transaction on a Sepolia block explorer

---

## LAYER 1 — Input / Camera Layer

### Decision
MVP supports **uploaded image file** as the primary path (`--image path/to/file.jpg`). Webcam capture is a "should have," not a blocker — reverse image search and blockchain integration are riskier and get priority. If time allows, add `--webcam` as an alternate input mode using OpenCV (`cv2.VideoCapture`) that captures one frame and reuses the same downstream pipeline.

### Tasks
- [x] Implement `--image <path>` CLI argument (required for MVP)
- [x] Implement optional `--webcam` flag (nice to have)
- [x] Validate file exists and is readable
- [x] Validate file is a supported format (jpg, jpeg, png) via file extension **and** actual image header check (e.g. `PIL.Image.open` + `verify()`), not extension alone
- [x] Reject corrupted/non-image files with a clear error message
- [x] Copy/save the validated input into a temporary working directory (e.g. `./tmp/run_<timestamp>/input.jpg`) so all later layers reference a stable path
- [x] Defer "no face" / "multiple face" handling to Layer 2 (this layer only validates that the file is a readable image, not that it contains a face)

### Input/Output of this layer
- **Input:** file path (CLI arg) or webcam frame
- **Output:** validated image file at a known temporary path, e.g. `tmp/run_<timestamp>/input.jpg`, plus its SHA-256 hash (compute here since we'll need it in Layer 6 anyway)

---

## LAYER 2 — Face Detection & Encoding Layer

This is **inference using a pretrained model**, not model training. InsightFace ships pretrained detection (RetinaFace/SCRFD) and recognition (ArcFace) models; we load and run them, we do not fine-tune or train anything.

### Tasks
- [x] Install `insightface` and `onnxruntime` (CPU build unless a judge machine/dev machine has CUDA available; document both paths)
- [x] Initialize `insightface.app.FaceAnalysis` with a standard pretrained pack (e.g. `buffalo_l`)
- [x] Configure ONNX Runtime providers (`CPUExecutionProvider` by default; `CUDAExecutionProvider` if available)
- [x] Run detection on the input image
- [x] Handle **zero faces detected** → return a structured error, do not proceed
- [x] Handle **multiple faces detected** → for MVP, select the largest bounding box (assume it's the primary subject) and log a warning that other faces were ignored
- [x] Extract the 512-d embedding vector for the selected face
- [x] Normalize the embedding (L2 normalization) if not already normalized by the model output, so cosine similarity is well-behaved
- [x] Wrap all of this in a single module: `face/encoder.py` with a function like `encode_face(image_path) -> FaceEncodingResult`
- [x] Define `FaceEncodingResult` as a small dataclass: `{embedding: np.ndarray, bbox: tuple, det_score: float, face_count: int}`

### Output structure (example)
```json
{
  "face_count": 1,
  "bbox": [123, 45, 340, 310],
  "det_score": 0.98,
  "embedding_dim": 512
}
```
The raw embedding array is kept in memory / local temp file only — never logged in full and never committed to git.

---

## LAYER 3 — Reverse Image Search Layer

### What "genuine reverse-image search" means (and why a normal search doesn't count)
A genuine reverse-image search sends the *actual image pixels* to a service that indexes images and returns pages where visually similar images appear. A normal text/keyword Google search, or a search seeded with the person's guessed name, does not satisfy this — it doesn't verify anything about the image itself. Hardcoding a known URL for a demo image is explicitly disallowed by the challenge and defeats the purpose of the requirement. This layer must make a live API call with the input image on every run and must work on images the developers have not pre-selected as "the demo image" (tested with at least one unseen image, see Layer 10).

### Tasks
- [x] Create a SerpApi account and obtain an API key
- [x] Store the key in `.env` as `SERPAPI_KEY`, load via `python-dotenv`
- [x] Implement `reverse_search/serpapi_client.py` calling SerpApi's Google Lens engine (`engine=google_lens`), submitting the input image (either via a public/temporary URL or SerpApi's upload mechanism — confirm which the account tier supports and document it)
- [x] Parse the JSON response: extract `visual_matches` (or equivalent field) — title, link, source/domain, thumbnail
- [x] Filter results to known social-media domains (e.g. instagram.com, facebook.com, x.com/twitter.com, linkedin.com, reddit.com, tiktok.com) — configurable allowlist in `config/`
- [x] Rank/select the top candidate (highest-ranked filtered result); keep the full filtered list available for fallback if the top candidate's image can't be retrieved (Layer 4)
- [x] Handle **no results** → structured "no candidate found" outcome, pipeline still completes and reports this honestly
- [x] Handle **API error / auth failure** → clear error, do not crash the whole pipeline uncaught
- [x] Handle **rate limit / quota exceeded** → detect the specific HTTP/response code SerpApi returns and surface it distinctly from a generic error
- [x] Log request metadata (timestamp, image hash, number of results) without logging the API key or full response body containing unnecessary data

### Documented limitations (goes in README too)
- SerpApi free/dev tier has a limited number of monthly searches — plan test runs accordingly
- Google Lens indexing coverage is not exhaustive; a real match may exist but not surface
- Public figures / widely-shared images are far more likely to return a hit than private individuals' photos — this is expected and should be acknowledged in the demo, not hidden

---

## LAYER 4 — Candidate Image Retrieval

### Tasks
- [x] Given a candidate result (URL + thumbnail from Layer 3), attempt to retrieve a usable image:
  - First try the thumbnail URL returned directly by SerpApi (fastest, most reliable, usually accessible)
  - If a higher-resolution direct image URL is available in the result payload, prefer it
- [x] Validate the retrieved content is actually an image (check content-type header and/or attempt to open with PIL) before passing it downstream
- [x] Save the retrieved image to the temp run directory
- [x] Handle **page/content inaccessible** (403, login wall, deleted post, private account) → fall back to the next candidate in the filtered list from Layer 3, if any; otherwise report "candidate found but image not retrievable"
- [x] Do **not** attempt to log in, scrape behind auth walls, or circumvent robots.txt / platform terms — if a match's source is inaccessible, that is a reportable outcome, not a problem to "solve" by bypassing access controls
- [x] Compute SHA-256 of the retrieved candidate image (needed for Layer 6)

### Output
- Path to a local candidate image file, its SHA-256, and the source URL — or an explicit "unavailable" status carried forward.

---

## LAYER 5 — Face Matching / Similarity Layer

### Data flow
```
Input embedding (512-d)
        |
        v
Candidate image --> InsightFace detect/encode --> Candidate embedding(s) (512-d each)
        |
        v
Cosine similarity(input_embedding, each candidate_embedding)
        |
        v
Take max similarity across candidate faces
        |
        v
Compare against threshold (e.g. 0.45, tunable — see note below)
        |
        v
Match / No-Match decision + similarity score
```

### Tasks
- [x] Run the same `face/encoder.py` module from Layer 2 on the candidate image (reuse code, don't duplicate)
- [x] Handle **candidate image has no detectable face** → report as "no match — no face in candidate image"
- [x] Handle **candidate image has multiple faces** → compute similarity against each detected face, keep the highest score, log how many faces were compared
- [x] Compute cosine similarity: `sim = dot(a, b) / (norm(a) * norm(b))`
- [x] Define a threshold constant in `config/settings.py` (e.g. `MATCH_THRESHOLD = 0.45` for ArcFace-style embeddings — exact value should be sanity-checked against a few test pairs, see Layer 10)
- [x] Document in code and README that **this threshold is an experimentally chosen prototype parameter**, not a validated forensic standard
- [x] Return `{similarity_score, is_match, candidate_face_count}`

### Explicitly state (in code comments, README, and CLI output)
A similarity score above threshold indicates the two face images are visually similar according to this model's embedding space. It does **not** prove the two images are the same real-world person, and it is not a substitute for identity verification.

---

## LAYER 6 — Verification Record Layer

### Tasks
- [x] Build a structured record containing only what's necessary:
  - `input_image_sha256`
  - `candidate_image_sha256` (or `null` if unavailable)
  - `candidate_source_url` (or `null`)
  - `similarity_score` (or `null` if no comparison was possible)
  - `match_status`: one of `"match"`, `"no_match"`, `"no_candidate_found"`, `"candidate_unavailable"`
  - `timestamp` (UTC, ISO 8601)
  - `pipeline_version` (a short git-commit-hash or version string)
- [x] Do **not** include the raw image, raw embedding vectors, or any name/identity claim in this record
- [x] Serialize the record deterministically — fixed key order, no extraneous whitespace (e.g. `json.dumps(record, sort_keys=True, separators=(",", ":"))`) so the hash is reproducible from the same data
- [x] Compute SHA-256 of the serialized record
- [x] Save the record locally as `verification_record.json` in the run's temp directory

### What the hash represents
The SHA-256 hash is a fixed-length fingerprint of the exact verification record (metadata + result), not of the face image or embedding itself. Anyone holding a copy of the record can recompute the hash and confirm it matches what was written to the blockchain, proving the record hasn't been altered after the fact.

### Example verification record
```json
{
  "input_image_sha256": "a1b2c3...",
  "candidate_image_sha256": "d4e5f6...",
  "candidate_source_url": "https://www.instagram.com/p/example/",
  "similarity_score": 0.71,
  "match_status": "match",
  "timestamp": "2026-09-06T10:15:00Z",
  "pipeline_version": "0.1.0"
}
```

---

## LAYER 7 — Smart Contract / Blockchain Layer

### Why blockchain, specifically
The point is **tamper-evidence and independent verifiability**: once the record hash is written to a public testnet, anyone can look up that transaction on a block explorer and confirm the exact hash value and timestamp were recorded at that point — without trusting our local files. A local JSON file alone can be silently edited after the fact; a confirmed on-chain transaction cannot.

### Why we store a hash, not raw data
Storing raw face images or embeddings on a public, permanent, append-only ledger would permanently expose biometric data with no way to delete or revoke it. Storing only a hash plus non-sensitive metadata gives tamper-evidence without putting sensitive data on a public ledger.

### Tasks — Contract
- [x] Write a minimal Solidity contract, e.g. `contracts/VerificationRegistry.sol`, storing per submission:
  - `bytes32 recordHash`
  - `string candidateSourceUrl` (or omit if length/gas is a concern — consider storing only the hash + timestamp on-chain and keeping the URL in the local JSON record, referenced by hash)
  - `uint256 timestamp` (or use `block.timestamp` at write time)
  - `address submitter` (implicit via `msg.sender`)
- [x] Implement a `submitVerification(bytes32 recordHash, string calldata metadata)` function that appends a new record and emits an event (e.g. `VerificationSubmitted(address indexed submitter, bytes32 recordHash, uint256 timestamp)`)
- [x] Implement a `getVerification(uint256 id)` or `getVerificationsBySubmitter(address)` read function
- [x] Keep the contract intentionally minimal — no upgradability, no access control beyond default `msg.sender` attribution, for hackathon scope

### Tasks — Deployment
- [x] Write and compile the contract in Remix
- [x] Configure MetaMask with a **dedicated hackathon/testnet-only wallet** (never a wallet holding real funds)
- [x] Switch MetaMask network to Sepolia
- [x] Obtain Sepolia test ETH from a public faucet
- [x] Deploy the contract via Remix + MetaMask
- [x] Save the deployed contract address and the compiled ABI JSON into `config/contract.json` (or similar) — this file is not secret and can be committed
- [x] Manually test `submitVerification` once via Remix's UI to confirm the contract behaves as expected before wiring up Python

### Tasks — Python integration
- [x] Install `web3.py`
- [x] Load RPC endpoint (e.g. an Infura/Alchemy Sepolia URL) from `.env` as `SEPOLIA_RPC_URL`
- [x] Load the dedicated wallet's private key from `.env` as `WALLET_PRIVATE_KEY` — **never commit this**
- [x] Load contract address + ABI from `config/contract.json`
- [x] Build, sign, and send the `submitVerification` transaction with `web3.py`
- [x] Wait for the transaction receipt (`web3.eth.wait_for_transaction_receipt`)
- [x] Print/save the transaction hash
- [x] Construct the Sepolia explorer URL for the transaction (e.g. `https://sepolia.etherscan.io/tx/<hash>`) for manual verification during the demo

---

## LAYER 8 — End-to-End Pipeline Layer

### Command
```
python main.py --image input.jpg
```

### CLI output design (so a judge can follow it live)
```
[1/14] Input image loaded: input.jpg (sha256: a1b2c3...)
[2/14] Face detected: 1 face, det_score=0.98
[3/14] Face embedding generated (512-d)
[4/14] Running reverse image search via SerpApi (Google Lens)...
[5/14] Candidate found: https://www.instagram.com/p/example/ (domain: instagram.com)
[6/14] Candidate image retrieved (sha256: d4e5f6...)
[7/14] Candidate face detected: 1 face
[8/14] Similarity computed: 0.71
[9/14] Decision: MATCH (threshold=0.45)
[10/14] Verification record built
[11/14] Record hash: 7f8e9d...
[12/14] Submitting transaction to Sepolia...
[13/14] Transaction confirmed: 0xabc123...
[14/14] Verification complete. View: https://sepolia.etherscan.io/tx/0xabc123...
```
Each numbered step should print immediately when reached (not buffered until the end) so a screen recording clearly shows live progress rather than a single dump at the end.

### Tasks
- [x] Implement `main.py` as the orchestrator: calls each layer's module in order, catches layer-specific exceptions, prints the numbered progress lines above
- [x] Ensure every layer function returns a small typed result object rather than raising uncaught exceptions for expected failure cases (no face, no candidate, etc.)
- [x] Ensure the final printed summary always appears, even on partial failure, explaining exactly which step stopped progress and why

---

## LAYER 9 — Error Handling

Checklist of conditions the pipeline must handle gracefully (print a clear reason, exit cleanly, no stack trace dumped to the judge):

- [x] No image provided
- [x] Invalid / corrupted image file
- [x] No face detected in input image
- [x] Multiple faces in input image (handled per Layer 2 policy, not a hard failure)
- [x] Reverse search returns zero results
- [x] SerpApi request/auth failure
- [x] SerpApi rate limit exceeded
- [x] Candidate social-media page inaccessible
- [x] Candidate image unavailable/undownloadable
- [x] Candidate image contains no face
- [x] Candidate image contains multiple faces (handled per Layer 5 policy)
- [x] Similarity below threshold (this is a valid outcome, not an error — report "no match")
- [x] Blockchain RPC endpoint unreachable
- [x] Wallet/signing failure (bad key, wrong network)
- [x] Insufficient Sepolia test ETH for gas
- [x] Transaction submitted but failed/reverted
- [x] Contract call reverts (bad ABI mismatch, wrong address, etc.)

Every one of these should map to a distinct, human-readable message — not a generic "an error occurred."

---

## LAYER 10 — Testing

### Test plan
- [x] Valid face image → expect successful detection and embedding
- [x] Same person, different photo → run full pipeline, sanity-check similarity is reasonably high if a candidate is found
- [x] Different person's image → confirm similarity is low / no false match
- [x] Image with multiple people → confirm the "largest face selected" policy behaves as expected
- [x] Image with no face (e.g. a landscape photo) → confirm clean "no face detected" error
- [x] Image with poor lighting → confirm detection either succeeds with a lower confidence score or fails gracefully
- [x] Reverse search using an image already known to exist publicly online → confirm a real candidate is returned (this is the critical "genuine search" proof)
- [x] Reverse search using an image that has no public online presence (e.g. a fresh personal photo never posted) → confirm "no candidate found" is handled and reported honestly
- [x] Blockchain transaction success path → confirm transaction hash returned and visible on Sepolia explorer
- [x] Blockchain failure path (e.g. deliberately misconfigure RPC URL) → confirm graceful error
- [x] Verification hash consistency → run the same record data twice, confirm identical hash output (determinism check)

### Priority before recording the final demo
Test, in this order, before touching the recording: (1) reverse image search actually returns real results on an unseen image, (2) face similarity computation on a known-match pair and a known-non-match pair, (3) a full successful blockchain submission with a viewable Sepolia transaction. These three are the load-bearing proof points for the challenge; everything else (CLI formatting, error messages) is polish.

---

## LAYER 11 — Security & Privacy

- [x] Never commit API keys, RPC URLs with embedded keys, or wallet credentials
- [x] Use `.env` for all secrets (`SERPAPI_KEY`, `SEPOLIA_RPC_URL`, `WALLET_PRIVATE_KEY`)
- [x] Add `.env` to `.gitignore`; commit only `.env.example` with placeholder values
- [x] Never expose the wallet private key or seed phrase in logs, console output, error messages, or the recording
- [x] Use a **dedicated hackathon/testnet-only wallet** holding only Sepolia test ETH — never a wallet with real funds
- [x] Never write raw face images or raw embeddings to the blockchain
- [x] Avoid storing or logging unnecessary personal data beyond what's needed for the verification record
- [x] Never state or imply that a similarity match proves real-world identity
- [x] Document, in the README, the known limitations of both face recognition (lighting, angle, age differences, dataset bias, threshold sensitivity) and reverse image search (indexing gaps, rate limits, platform accessibility restrictions)

---

## LAYER 12 — GitHub Repository

```
faceproof/
├── README.md
├── PROJECT_OVERVIEW.md
├── requirements.txt
├── .env.example
├── .gitignore
├── main.py
├── config/
│   ├── settings.py          # threshold, allowed domains, paths
│   └── contract.json        # deployed contract address + ABI (not secret)
├── face/
│   └── encoder.py           # Layer 2: detection + embedding
├── reverse_search/
│   └── serpapi_client.py    # Layer 3: SerpApi Google Lens integration
├── matching/
│   ├── retrieval.py         # Layer 4: candidate image retrieval
│   └── similarity.py        # Layer 5: cosine similarity + threshold logic
├── verification/
│   └── record.py            # Layer 6: record building + hashing
├── blockchain/
│   ├── client.py            # Layer 7: web3.py submission logic
│   └── VerificationRegistry.sol   # (or under contracts/, see below)
├── contracts/
│   └── VerificationRegistry.sol
├── utils/
│   ├── hashing.py           # SHA-256 helpers
│   └── logging.py           # structured console/log output for Layer 8
└── tests/
    ├── test_face_encoder.py
    ├── test_similarity.py
    ├── test_record_hash.py
    └── fixtures/             # sample test images (only images the team has rights to use)
```

- **README.md** — everything a judge needs to run and evaluate the project (Layer 13).
- **PROJECT_OVERVIEW.md** — this document.
- **config/** — non-secret configuration (thresholds, domain allowlist, deployed contract address/ABI).
- **face/** — all InsightFace detection/embedding logic, isolated so it can be unit tested independently.
- **reverse_search/** — SerpApi integration only; no face logic here.
- **matching/** — candidate retrieval and similarity comparison.
- **verification/** — record construction and hashing; no blockchain code here.
- **blockchain/** and **contracts/** — Solidity source and the Python web3.py client, kept separate from the ML code.
- **utils/** — small shared helpers (hashing, logging format) used across layers.
- **tests/** — unit tests per layer plus any fixture images the team has rights to use for testing.

---

## LAYER 13 — README.md Requirements

The final `README.md` must contain, in this order:
- [x] Project overview (what it is, one paragraph)
- [x] Problem statement
- [x] Solution summary
- [x] Architecture diagram (text/ASCII is fine)
- [x] Full pipeline description (the 14-step flow from Layer 8)
- [x] Tech stack list (InsightFace, ONNX Runtime, SerpApi, Solidity, Sepolia, web3.py, Remix, MetaMask)
- [x] Setup instructions
- [x] Required environment variables (names only, no real values)
- [x] Installation steps (`pip install -r requirements.txt`, etc.)
- [x] How to run (`python main.py --image input.jpg`)
- [x] Example CLI output (copy the block from Layer 8)
- [x] Smart contract details: contract name, deployed address, network (Sepolia), link to source
- [x] Blockchain explanation: what's stored on-chain and why (hash + metadata, not raw biometric data)
- [x] Known limitations (face recognition accuracy, reverse-search coverage/rate limits, threshold is a prototype value)
- [x] Privacy considerations (Layer 11 summary)
- [x] Future improvements (webcam capture, better candidate ranking, multi-candidate comparison, contract upgrades)
- [x] Hackathon task mapping table (see Layer 14)

---

## LAYER 14 — Final Hackathon Submission Checklist

| Requirement | Implementation |
|---|---|
| Detect and encode a face | `face/encoder.py`, called from `main.py` step [2]-[3] |
| Find a real matching social-media post via genuine reverse-image search | `reverse_search/serpapi_client.py`, called from `main.py` step [4]-[5] |
| Upload match data to blockchain | `verification/record.py` (hashing) + `blockchain/client.py` (submission), `main.py` steps [10]-[13] |
| No website or hosting needed | Entire system is a CLI (`main.py`); no server/frontend code exists in the repo |
| Source on GitHub | Repository structure per Layer 12 |
| How to run | README "How to run" section, Layer 13 |
| Blockchain used + limitations | README "Smart contract details" + "Known limitations" sections |
| Unedited end-to-end screen recording | Recording script, Layer 15 |

---

## LAYER 15 — Unedited Demo Recording Script

Recording must be one continuous take, starting before the command is run and ending after the transaction is confirmed. No cuts, no edited-together clips.

Recording sequence:
- [x] Briefly show the repository structure and key files (few seconds, not a full code read-through)
- [x] Show the chosen input image
- [x] Run `python main.py --image input.jpg` in a visible terminal
- [x] Show step [2]-[3]: face detected, embedding generated (console output)
- [x] Show step [4]: reverse image search request going out (console output, confirms it's a live call, not instant/hardcoded)
- [x] Show step [5]: the real returned candidate result (URL visible on screen)
- [x] Open the candidate social-media URL in a browser to show it's a real, live post (not staged)
- [x] Show step [6]-[7]: candidate image retrieved and face detected in it
- [x] Show step [8]-[9]: similarity score and match decision printed
- [x] Show step [10]-[11]: verification record JSON and its hash (open the local file briefly)
- [x] Show step [12]-[13]: blockchain transaction submitted and confirmed (console output with tx hash)
- [x] Open the Sepolia block explorer, paste in the transaction hash, show the confirmed transaction on-chain
- [x] End on the final CLI success output

---

## FINAL SECTION — One-Day Development Schedule

Riskiest external dependency (reverse image search) gets tested first, before any polish work.

### Must have (MVP — without these, the submission fails the challenge)
1. [x] Genuine reverse-image search returning a real result on at least one unseen test image (test this in the first 1-2 hours)
2. [x] Face detection + embedding (InsightFace) working on input and candidate images
3. [x] Face similarity computation with a defined threshold and match/no-match decision
4. [x] Verification record construction + SHA-256 hashing
5. [x] Solidity contract deployed to Sepolia, callable from Python via web3.py, producing a confirmed transaction
6. [x] Single end-to-end CLI command (`main.py`) chaining all of the above
7. [x] GitHub repo with README covering setup, run instructions, blockchain used, and limitations
8. [ ] One unedited end-to-end screen recording (to be performed by user/team with screen recorder)

### Should have
- [x] Graceful handling of every failure case listed in Layer 9
- [x] Fallback to next candidate if the top reverse-search result's image is unretrievable
- [x] Basic unit tests for face encoding, similarity, and hash determinism (Layer 10)
- [x] Webcam capture as an alternate input mode

### Nice to have
- [x] Comparing against multiple reverse-search candidates and reporting the best match rather than only the top result
- [x] Storing multiple candidate scores in the verification record for transparency
- [x] A simple lookup CLI command (`python main.py --lookup <tx_hash>`) that reads a record back from the contract

No frontend, no hosting, no unnecessary UI work — none of it counts toward the challenge requirements.

### Suggested timeline (single day, ~10-12 working hours)
- Hour 0-2: Environment setup, InsightFace working locally, SerpApi account created and a raw test call confirmed working on a real image
- Hour 2-4: Face encoding module complete and tested; reverse search module complete and tested end-to-end (this is the checkpoint — if this isn't working, escalate/adjust scope before going further)
- Hour 4-6: Candidate retrieval + similarity comparison working
- Hour 6-8: Solidity contract written, deployed to Sepolia, Python web3.py submission working with a real confirmed transaction
- Hour 8-9: Full `main.py` orchestration wired end-to-end
- Hour 9-10: Error handling pass, basic tests, README written
- Hour 10-11: Record the unedited demo (may take a couple of takes — budget time for this)
- Hour 11-12: Buffer / final GitHub cleanup and submission

---

## Definition of Done

- [x] `python main.py --image <path>` runs start to finish without unhandled exceptions on a valid test image
- [x] Reverse image search is a live API call every run — no hardcoded URLs or cached demo results anywhere in the code
- [x] At least one full run produces a real social-media candidate and a viewable candidate image
- [x] Face similarity score and match decision are computed and printed
- [x] Verification record is generated, saved locally, and hashed deterministically
- [x] A transaction is confirmed on Sepolia and viewable on a block explorer, containing the verification hash
- [x] No raw images, raw embeddings, private keys, or API keys appear in the git history
- [x] `.env.example` exists; `.env` is gitignored
- [x] README covers overview, setup, run instructions, tech stack, contract details, limitations, and privacy considerations
- [x] Task-mapping table (Layer 14) is filled in with real file references
- [ ] One continuous, unedited screen recording exists covering input through confirmed on-chain transaction (to be performed with screen recording software)
- [ ] Repository is public (or otherwise accessible to judges) on GitHub