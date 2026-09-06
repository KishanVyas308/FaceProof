# Layer 15: Unedited Demo Recording Script

This document details the exact sequence for recording the unedited, continuous video demonstration required by the Hacker House Goa 2026 challenge.

> [!IMPORTANT]
> The recording must be **one continuous take** with no cuts or post-production editing. Start the screen recording before launching the command and finish after viewing the transaction on Sepolia Etherscan.

---

## Pre-Recording Checklist
- [ ] Ensure `.env` is populated with `SERPAPI_KEY`, `SEPOLIA_RPC_URL`, `WALLET_PRIVATE_KEY` (with Sepolia test ETH), and `CONTRACT_ADDRESS`.
- [ ] Verify test image exists (e.g. `tests/fixtures/sample_face.jpg` or a chosen public figure / test photo known to have an online social media presence).
- [ ] Open a clean browser window navigated to [sepolia.etherscan.io](https://sepolia.etherscan.io).
- [ ] Open a terminal window sized with high readability and legible font.

---

## Recording Sequence

### 1. Show Project Structure (5-10 seconds)
Show the clean file tree in terminal:
```bash
ls -la
```
Highlight key modules: `main.py`, `face/`, `reverse_search/`, `matching/`, `verification/`, `blockchain/`, `contracts/`.

### 2. Show the Input Image (5 seconds)
Briefly display or open the input photo to prove it is a real image containing a face.

### 3. Run the CLI Pipeline
In the terminal, run:
```bash
python main.py --image path/to/chosen_face.jpg
```

### 4. Progress Trace Validation (Live Console)
Let each step print live:
- **`[1/14]`**: Input image loaded & SHA-256 computed.
- **`[2/14]` – `[3/14]`**: Face detected (1 face, det_score) and 512-d ArcFace embedding generated.
- **`[4/14]`**: Reverse image search request sent live to SerpApi Google Lens.
- **`[5/14]`**: Live candidate discovered on a supported social-media platform (e.g., Instagram, X, or Reddit).
- **`[6/14]`**: Candidate image retrieved and SHA-256 computed.
- **`[7/14]` – `[8/14]`**: Candidate face detected and cosine similarity computed.
- **`[9/14]`**: Decision output (`MATCH` / `NO MATCH` vs threshold 0.45).
- **`[10/14]` – `[11/14]`**: Local `verification_record.json` generated and SHA-256 fingerprint displayed.
- **`[12/14]` – `[13/14]`**: Transaction signed and broadcast to Ethereum Sepolia; transaction receipt confirmed.
- **`[14/14]`**: Explorer URL displayed.

### 5. Inspect Candidate Post & Block Explorer
- Switch to the browser window and open the candidate URL printed in step `[5/14]` to demonstrate it is a real, live social-media post.
- Open the Sepolia block explorer link printed in step `[14/14]`.
- Show the transaction status (`Success`), timestamp, block number, and contract interaction.
- End the recording on this confirmed on-chain screen.
