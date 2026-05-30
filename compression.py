"""Minimal compression shim for v0.4 encoder.
Real zstd would compress better; we use zlib here so the harness has zero new deps.
The compression ratio is what's measured; choice of algo is documented."""
import zlib

def compress(data: bytes, algorithm: str = "zstd") -> bytes:
    # zlib level 9 is a reasonable stand-in (slightly weaker than zstd-3,
    # but the dominant signal — "v4 body compresses well" — comes through).
    return zlib.compress(data, level=9)

def decompress(data: bytes, algorithm: str = "zstd") -> bytes:
    return zlib.decompress(data)
