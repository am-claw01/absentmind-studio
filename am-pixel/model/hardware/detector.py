"""
Hardware detection utility — ALL device references route through here.
See am-pixel/SPEC.md §3.1, §14 and CONSTITUTION.md Rule 3.

Detection hierarchy:
  1. NVIDIA GPU  → CUDA  (fastest; preferred for training)
  2. AMD GPU     → ROCm  (PyTorch-supported; near-equivalent performance)
  3. Apple Silicon → MPS  (Metal Performance Shaders)
  4. Other GPU   → OpenCL via PyTorch extensions
  5. No GPU      → CPU   (inference usable; training at Phase 4 scale = months)

NEVER use the string "cuda" directly in any other script.
Always call get_device() or get_device_info() from this module.
"""
from __future__ import annotations

import json
import time
import logging
from pathlib import Path
from typing import Optional

import torch

logger = logging.getLogger(__name__)

# Path to hardware log — relative to this file's location
_AM_PIXEL = Path(__file__).resolve().parent.parent.parent
HARDWARE_LOG = _AM_PIXEL / "logs" / "hardware.log"


def get_device() -> torch.device:
    """
    Return the best available torch.device following the Constitution Rule 3
    detection hierarchy. This is the single source of truth for device selection.
    No other script should hardcode 'cuda' — always call this.
    """
    if torch.cuda.is_available():
        return torch.device("cuda")

    # ROCm surfaces as 'cuda' in PyTorch — check vendor
    # If CUDA is available and GPU vendor is AMD, it's ROCm
    # (already handled above since ROCm uses the same torch.cuda API)

    # MPS: Apple Silicon
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")

    # CPU fallback
    return torch.device("cpu")


def get_backend_name(device: Optional[torch.device] = None) -> str:
    """Return a human-readable backend name string."""
    d = device or get_device()
    if d.type == "cuda":
        # Distinguish CUDA (NVIDIA) from ROCm (AMD)
        try:
            gpu_name = torch.cuda.get_device_name(0)
            if "AMD" in gpu_name or "Radeon" in gpu_name or "gfx" in gpu_name.lower():
                return "ROCm"
            return "CUDA"
        except Exception:
            return "CUDA"
    if d.type == "mps":
        return "MPS"
    return "CPU"


def get_device_info() -> dict:
    """
    Return a dict with all hardware information.
    Used to populate hardware.log.
    """
    device = get_device()
    backend = get_backend_name(device)

    info: dict = {
        "device_type": device.type,
        "backend": backend,
        "gpu_model": "N/A",
        "vram_gb": "N/A",
        "baseline_tokens_per_sec": None,
    }

    if device.type == "cuda":
        try:
            info["gpu_model"] = torch.cuda.get_device_name(0)
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            info["vram_gb"] = round(vram_bytes / (1024 ** 3), 1)
        except Exception as e:
            logger.warning("Could not read CUDA device properties: %s", e)
    elif device.type == "mps":
        import platform
        info["gpu_model"] = f"Apple Silicon ({platform.processor()})"
        info["vram_gb"] = "Unified memory"

    return info


def run_baseline_speed_test(device: torch.device, sprite_w: int = 16, sprite_h: int = 16) -> float:
    """
    Measure baseline inference speed: tokens/sec on a 16×16 sprite forward pass.
    Uses a tiny single-layer transformer to simulate the generation step.
    Returns tokens per second.
    """
    seq_len = sprite_w * sprite_h  # 256 for 16x16
    vocab_size = 256
    d_model = 64
    n_heads = 4
    n_layers = 1

    model = torch.nn.TransformerDecoder(
        torch.nn.TransformerDecoderLayer(d_model, n_heads, dim_feedforward=128, batch_first=True),
        num_layers=n_layers,
    ).to(device)
    embedding = torch.nn.Embedding(vocab_size, d_model).to(device)

    tokens = torch.randint(0, vocab_size, (1, seq_len), device=device)
    memory = torch.zeros(1, 1, d_model, device=device)

    # Warm-up
    with torch.no_grad():
        emb = embedding(tokens)
        model(emb, memory)

    # Timed run
    n_runs = 5
    start = time.perf_counter()
    with torch.no_grad():
        for _ in range(n_runs):
            emb = embedding(tokens)
            model(emb, memory)
    elapsed = time.perf_counter() - start

    total_tokens = seq_len * n_runs
    tokens_per_sec = total_tokens / elapsed
    return round(tokens_per_sec, 1)


def main() -> None:
    """
    Run hardware detection, log results to logs/hardware.log.
    Called once during Phase 0 initialization.
    """
    logging.basicConfig(level=logging.INFO)

    print("=== AM Pixel Hardware Detection ===")
    device = get_device()
    info = get_device_info()

    print(f"Backend:   {info['backend']}")
    print(f"GPU model: {info['gpu_model']}")
    print(f"VRAM:      {info['vram_gb']}")

    print("Running baseline inference speed test (16×16 sprite)...")
    try:
        tokens_per_sec = run_baseline_speed_test(device)
        info["baseline_tokens_per_sec"] = tokens_per_sec
        print(f"Baseline:  {tokens_per_sec} tokens/sec")
    except Exception as e:
        print(f"Speed test failed: {e}")
        tokens_per_sec = 0.0

    # Determine Phase 4 training tier estimate based on detected backend
    # NOTE: micro-benchmark token speed is not a reliable proxy at this model size;
    # tier is determined by backend type (from Constitution Rule 3 detection hierarchy).
    tier_note = ""
    backend_for_tier = info["backend"]
    if backend_for_tier in ("CUDA", "ROCm"):
        tier_note = "GPU tier (CUDA/ROCm) — Phase 4 training: 1–7 days estimated (depends on VRAM)"
    elif backend_for_tier == "MPS":
        tier_note = "Apple Silicon tier — Phase 4 training: 1–4 weeks estimated"
    else:
        tier_note = "CPU tier — Phase 4 training: MONTHS estimated. CLOUD GPU REQUIRED for Phase 4."

    print(f"Phase 4 estimate: {tier_note}")

    # Write hardware.log
    HARDWARE_LOG.parent.mkdir(parents=True, exist_ok=True)
    log_content = f"""# hardware.log — populated by model/hardware/detector.py during Phase 0
# CHANGE-030: Phase 4 tier estimate included.

Backend: {info['backend']}
GPU Model: {info['gpu_model']}
VRAM: {info['vram_gb']} GB
Baseline inference speed: {info['baseline_tokens_per_sec']} tokens/sec (16×16 sprite forward pass)
Phase 4 training estimate: {tier_note}
Detection timestamp: {__import__('datetime').datetime.now().isoformat()}
"""
    HARDWARE_LOG.write_text(log_content, encoding="utf-8")
    print(f"\nResults written to: {HARDWARE_LOG}")
    print("=== Detection complete ===")


if __name__ == "__main__":
    main()
