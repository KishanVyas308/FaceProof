"""Pipeline logging and console output utilities for FaceProof."""

import sys
from typing import Optional


class PipelineLogger:
    """Manages immediate, unbuffered numbered step console output for the 14-step pipeline."""

    TOTAL_STEPS = 14

    @staticmethod
    def step(step_num: int, message: str) -> None:
        """Prints a numbered step immediately and flushes stdout."""
        print(f"[{step_num}/{PipelineLogger.TOTAL_STEPS}] {message}", flush=True)

    @staticmethod
    def info(message: str) -> None:
        """Prints an informative line immediately."""
        print(f"       * {message}", flush=True)

    @staticmethod
    def warn(message: str) -> None:
        """Prints a warning line immediately."""
        print(f"       ! WARNING: {message}", flush=True)

    @staticmethod
    def error(message: str, step_num: Optional[int] = None) -> None:
        """Prints an error cleanly with human-readable diagnostic context."""
        prefix = f"[{step_num}/{PipelineLogger.TOTAL_STEPS}] " if step_num else ""
        print(f"\n{prefix}[ERROR] {message}\n", file=sys.stderr, flush=True)

    @staticmethod
    def summary_box(title: str, details: dict) -> None:
        """Prints a clean summary box."""
        width = 65
        print("\n" + "=" * width, flush=True)
        print(f" {title.upper().center(width - 2)} ", flush=True)
        print("=" * width, flush=True)
        for key, value in details.items():
            print(f" {key:<24}: {value}", flush=True)
        print("=" * width + "\n", flush=True)
