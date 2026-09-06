#!/usr/bin/env python3
"""
FaceProof — End-to-End Face ID + Blockchain Verification Pipeline.

Usage:
    python main.py --image path/to/image.jpg
    python main.py --webcam
    python main.py --lookup 0x<tx_hash>
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from blockchain.client import (
    BlockchainError,
    InsufficientGasError,
    RPCConnectionError,
    SepoliaClient,
    TransactionExecutionError,
    WalletConfigurationError,
)
from config.settings import (
    ALLOWED_DOMAINS,
    MATCH_THRESHOLD,
    PIPELINE_VERSION,
    SIMULATE_BLOCKCHAIN,
)
from face.encoder import (
    FaceDetectionError,
    NoFaceDetectedError,
    encode_face,
)
from face.input_handler import (
    ImageValidationError,
    capture_webcam_frame,
    setup_run_directory,
    validate_and_stage_image,
)
from matching.retrieval import retrieve_best_candidate_image
from matching.similarity import compare_faces
from reverse_search.serpapi_client import (
    SearchCandidate,
    SerpApiAuthError,
    SerpApiError,
    SerpApiQuotaExceededError,
    search_google_lens,
)
from utils.logging import PipelineLogger
from verification.record import (
    build_verification_record,
    save_verification_record,
)


def run_pipeline(
    image_path: Optional[str] = None,
    use_webcam: bool = False,
    simulate_blockchain: Optional[bool] = None,
    allow_demo: bool = False
) -> int:
    """
    Executes the 14-step FaceProof pipeline from input validation through Sepolia verification.
    """
    run_dir = setup_run_directory()
    summary_data = {
        "Pipeline Version": PIPELINE_VERSION,
        "Run Directory": str(run_dir),
        "Match Decision": "INCOMPLETE",
        "Similarity Score": "N/A",
        "Record Hash": "N/A",
        "Sepolia Tx Hash": "N/A"
    }

    try:
        # -------------------------------------------------------------
        # Step [1/14]: Input Image Loaded
        # -------------------------------------------------------------
        if use_webcam:
            PipelineLogger.info("Capturing frame from system webcam...")
            staged_path, input_sha256 = capture_webcam_frame(run_dir)
            input_name = "webcam_capture.jpg"
        elif image_path:
            staged_path, input_sha256 = validate_and_stage_image(image_path, run_dir)
            input_name = Path(image_path).name
        else:
            PipelineLogger.error("No image provided. Specify --image <path> or --webcam.")
            return 1

        PipelineLogger.step(1, f"Input image loaded: {input_name} (sha256: {input_sha256[:12]}...)")
        summary_data["Input SHA-256"] = input_sha256

        # -------------------------------------------------------------
        # Step [2/14]: Face Detection
        # -------------------------------------------------------------
        try:
            face_result = encode_face(
                staged_path,
                require_face=True,
                warn_callback=lambda msg: PipelineLogger.warn(msg)
            )
        except NoFaceDetectedError:
            PipelineLogger.error(
                "No face detected in input image. Ensure image has good lighting and a visible subject.",
                step_num=2
            )
            summary_data["Match Decision"] = "NO_FACE_IN_INPUT"
            PipelineLogger.summary_box("Pipeline Terminated Early", summary_data)
            return 1
        except FaceDetectionError as fde:
            PipelineLogger.error(f"Face detection engine error: {fde}", step_num=2)
            return 1

        PipelineLogger.step(
            2,
            f"Face detected: {face_result.face_count} face(s), det_score={face_result.det_score:.2f}"
        )

        # -------------------------------------------------------------
        # Step [3/14]: Face Embedding Generated
        # -------------------------------------------------------------
        embedding_dim = len(face_result.embedding)
        PipelineLogger.step(3, f"Face embedding generated ({embedding_dim}-d)")

        # -------------------------------------------------------------
        # Step [4/14]: Running Reverse Image Search
        # -------------------------------------------------------------
        PipelineLogger.step(4, "Running reverse image search via SerpApi (Google Lens)...")
        try:
            candidates = search_google_lens(staged_path, allow_demo_fallback=allow_demo)
        except SerpApiAuthError as auth_err:
            PipelineLogger.error(f"SerpApi authentication failure: {auth_err}", step_num=4)
            return 1
        except SerpApiQuotaExceededError as quota_err:
            PipelineLogger.error(f"SerpApi quota or rate limit exceeded: {quota_err}", step_num=4)
            return 1
        except SerpApiError as sapi_err:
            PipelineLogger.error(f"SerpApi query error: {sapi_err}", step_num=4)
            return 1

        # -------------------------------------------------------------
        # Step [5/14]: Candidate Found & Domain Filtered
        # -------------------------------------------------------------
        if not candidates:
            PipelineLogger.warn(
                f"No social-media matches returned by Google Lens for allowed domains: {', '.join(ALLOWED_DOMAINS[:4])}..."
            )
            # Record an honest 'no_candidate_found' outcome
            record = build_verification_record(
                input_image_sha256=input_sha256,
                match_status="no_candidate_found"
            )
            rec_file, _, rec_hash = save_verification_record(record, run_dir)
            PipelineLogger.step(5, "No candidate match found on indexed social media platforms.")
            PipelineLogger.step(10, f"Verification record built ({rec_file.name})")
            PipelineLogger.step(11, f"Record hash: {rec_hash}")
            summary_data["Match Decision"] = "NO_CANDIDATE_FOUND"
            summary_data["Record Hash"] = rec_hash
            PipelineLogger.summary_box("FaceProof Result Summary", summary_data)
            return 0

        top_candidate = candidates[0]
        PipelineLogger.step(
            5,
            f"Candidate found: {top_candidate.source_url} (domain: {top_candidate.domain})"
        )
        summary_data["Candidate URL"] = top_candidate.source_url

        # -------------------------------------------------------------
        # Step [6/14]: Candidate Image Retrieved
        # -------------------------------------------------------------
        retrieved = retrieve_best_candidate_image(
            candidates,
            run_dir,
            demo_image_fallback=staged_path if allow_demo else None
        )
        if not retrieved:
            PipelineLogger.warn(
                "Candidate post found but image content was inaccessible (private/login wall/deleted)."
            )
            record = build_verification_record(
                input_image_sha256=input_sha256,
                candidate_source_url=top_candidate.source_url,
                match_status="candidate_unavailable"
            )
            rec_file, _, rec_hash = save_verification_record(record, run_dir)
            PipelineLogger.step(6, "Candidate image unavailable.")
            PipelineLogger.step(10, f"Verification record built ({rec_file.name})")
            PipelineLogger.step(11, f"Record hash: {rec_hash}")
            summary_data["Match Decision"] = "CANDIDATE_UNAVAILABLE"
            summary_data["Record Hash"] = rec_hash
            PipelineLogger.summary_box("FaceProof Result Summary", summary_data)
            return 0

        PipelineLogger.step(
            6,
            f"Candidate image retrieved (sha256: {retrieved.image_sha256[:12]}...)"
        )
        summary_data["Candidate SHA-256"] = retrieved.image_sha256

        # -------------------------------------------------------------
        # Step [7/14]: Candidate Face Detected
        # -------------------------------------------------------------
        similarity_res = compare_faces(
            face_result,
            retrieved.local_image_path,
            threshold=MATCH_THRESHOLD,
            warn_callback=lambda msg: PipelineLogger.warn(msg)
        )

        face_count_desc = (
            f"{similarity_res.candidate_face_count} face(s)"
            if similarity_res.candidate_face_count > 0
            else "0 faces"
        )
        PipelineLogger.step(7, f"Candidate face detected: {face_count_desc}")

        # -------------------------------------------------------------
        # Step [8/14]: Similarity Computed
        # -------------------------------------------------------------
        sim_str = (
            f"{similarity_res.similarity_score:.2f}"
            if similarity_res.similarity_score is not None
            else "None"
        )
        PipelineLogger.step(8, f"Similarity computed: {sim_str}")
        summary_data["Similarity Score"] = sim_str

        # -------------------------------------------------------------
        # Step [9/14]: Match Decision
        # -------------------------------------------------------------
        decision_label = "MATCH" if similarity_res.is_match else "NO MATCH"
        PipelineLogger.step(9, f"Decision: {decision_label} (threshold={MATCH_THRESHOLD:.2f})")
        summary_data["Match Decision"] = decision_label

        # -------------------------------------------------------------
        # Step [10/14]: Verification Record Built
        # -------------------------------------------------------------
        match_status_val = "match" if similarity_res.is_match else "no_match"
        record = build_verification_record(
            input_image_sha256=input_sha256,
            candidate_image_sha256=retrieved.image_sha256,
            candidate_source_url=retrieved.candidate.source_url,
            similarity_score=similarity_res.similarity_score,
            match_status=match_status_val
        )
        rec_file, _, rec_hash = save_verification_record(record, run_dir)
        PipelineLogger.step(10, f"Verification record built ({rec_file.name})")

        # -------------------------------------------------------------
        # Step [11/14]: Record Hash
        # -------------------------------------------------------------
        PipelineLogger.step(11, f"Record hash: {rec_hash}")
        summary_data["Record Hash"] = rec_hash

        # -------------------------------------------------------------
        # Step [12/14]: Submitting Transaction to Sepolia
        # -------------------------------------------------------------
        PipelineLogger.step(12, "Submitting transaction to Sepolia...")
        try:
            client = SepoliaClient(simulate=simulate_blockchain)
            metadata_summary = f"status={match_status_val}|url={retrieved.candidate.source_url[:100]}"
            tx_hash, explorer_url = client.submit_record_hash(rec_hash, metadata_summary)
        except RPCConnectionError as rpc_err:
            PipelineLogger.error(f"Sepolia RPC error: {rpc_err}", step_num=12)
            PipelineLogger.info("Tip: Check SEPOLIA_RPC_URL in .env, or use --simulate flag to dry run.")
            return 1
        except WalletConfigurationError as wall_err:
            PipelineLogger.error(f"Wallet configuration error: {wall_err}", step_num=12)
            PipelineLogger.info("Tip: Configure a valid testnet private key in WALLET_PRIVATE_KEY in .env.")
            return 1
        except InsufficientGasError as gas_err:
            PipelineLogger.error(f"Gas failure: {gas_err}", step_num=12)
            PipelineLogger.info("Tip: Request free Sepolia test ETH from sepoliafaucet.com.")
            return 1
        except TransactionExecutionError as tx_err:
            PipelineLogger.error(f"Transaction submission error: {tx_err}", step_num=12)
            return 1
        except BlockchainError as b_err:
            PipelineLogger.error(f"Blockchain failure: {b_err}", step_num=12)
            return 1

        # -------------------------------------------------------------
        # Step [13/14]: Transaction Confirmed
        # -------------------------------------------------------------
        PipelineLogger.step(13, f"Transaction confirmed: {tx_hash}")
        summary_data["Sepolia Tx Hash"] = tx_hash

        # -------------------------------------------------------------
        # Step [14/14]: Verification Complete
        # -------------------------------------------------------------
        PipelineLogger.step(14, f"Verification complete. View: {explorer_url}")
        summary_data["Explorer URL"] = explorer_url

        PipelineLogger.summary_box("FaceProof Verification Success", summary_data)
        return 0

    except ImageValidationError as ive:
        PipelineLogger.error(f"Input validation failure: {ive}", step_num=1)
        return 1
    except Exception as exc:
        PipelineLogger.error(f"Unexpected pipeline exception: {exc}")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FaceProof — Face ID + Sepolia Blockchain Verification Pipeline"
    )
    parser.add_argument(
        "--image",
        type=str,
        help="Path to input photo containing a face (jpg, jpeg, png, webp)"
    )
    parser.add_argument(
        "--webcam",
        action="store_true",
        help="Capture an image directly from the system webcam"
    )
    parser.add_argument(
        "--lookup",
        type=str,
        help="Lookup an on-chain transaction receipt by its Sepolia transaction hash"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run blockchain submission in simulated mode (useful for offline testing or without Sepolia gas)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in offline demo evaluation mode (simulates both reverse search candidate and blockchain)"
    )

    args = parser.parse_args()

    if args.lookup:
        try:
            client = SepoliaClient(simulate=args.simulate or args.demo or SIMULATE_BLOCKCHAIN)
            result = client.lookup_transaction(args.lookup)
            PipelineLogger.summary_box("On-Chain Verification Lookup", result)
            sys.exit(0)
        except Exception as e:
            PipelineLogger.error(f"Lookup failed: {e}")
            sys.exit(1)

    if not args.image and not args.webcam:
        parser.print_help()
        sys.exit(1)

    exit_code = run_pipeline(
        image_path=args.image,
        use_webcam=args.webcam,
        simulate_blockchain=args.simulate or args.demo or (SIMULATE_BLOCKCHAIN if not args.simulate else True),
        allow_demo=args.demo
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
