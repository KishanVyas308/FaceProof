"""Configuration settings for FaceProof."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base project directories
BASE_DIR = Path(__file__).resolve().parent.parent
TMP_DIR = BASE_DIR / "tmp"

# Pipeline parameters
PIPELINE_VERSION = "0.1.0"

# Face matching similarity threshold (Cosine similarity: 0.0 - 1.0)
# Note: ArcFace cosine similarities typically span 0.4 - 0.7 for valid matches.
# 0.45 is chosen as an experimentally validated prototype threshold.
MATCH_THRESHOLD = 0.45

# Allowed social media domains to consider for candidate posts
ALLOWED_DOMAINS = [
    "instagram.com",
    "facebook.com",
    "x.com",
    "twitter.com",
    "linkedin.com",
    "reddit.com",
    "tiktok.com",
    "youtube.com",
    "pinterest.com",
    "threads.net"
]

# API Keys & Blockchain Config
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "")
WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY", "")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")
SIMULATE_BLOCKCHAIN = os.getenv("SIMULATE_BLOCKCHAIN", "false").lower() in ("true", "1", "yes")

# Default explorer base URL
SEPOLIA_EXPLORER_TX_URL = "https://sepolia.etherscan.io/tx/"
