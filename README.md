<div align="center">

# 🔌 AgentWire

### A compact wire protocol for agent-to-agent messaging

*Typed envelopes · positional & binary profiles · token-frugal serialization*

[![License: MIT](https://img.shields.io/badge/License-MIT-D4F23C?style=for-the-badge)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10+-1A1A1A?style=for-the-badge&logo=python&logoColor=D4F23C)
![Version 0.3](https://img.shields.io/badge/version-0.3.0-1A1A1A?style=for-the-badge)

**Created by [Fahrenheit Research](https://f-r.co)** · part of the [Agent Stack](https://github.com/fahrenheit-research)

</div>

---

## Why AgentWire

When agents talk to each other — and to LLMs — every repeated JSON key and every quote character is **tokens you pay for and latency you wait on**. AgentWire is a small, dependency-light serialization layer that keeps the *structure* of a message while shedding the bytes JSON wastes.

It carries a typed **envelope** (message ID, correlation ID, priority, TTL) alongside the payload, and lets you dial the trade-off between human-readability and wire size by picking an **encoding profile** — from plain JSON all the way down to interned binary.

## Encoding profiles

| Profile | Function | Shape | Best for |
| :-- | :-- | :-- | :-- |
| **Standard** | `encode` | Readable JSON: `{header, body}` | Debugging, logs, human inspection |
| **Champion (JSON)** | `encode_champion` | Positional — keys hoisted into the header, body is a values array | Repeated message schemas |
| **Champion Binary** | `encode_champion_binary` | Length-prefixed packet: `[hdr_len][hdr][body_len][body]` | Sockets, byte-counted transports |
| **Champion v4** | `encode_champion_v4` | String interning + LEB128 varints + 1-byte type sigils | Maximum size reduction |
| **Champion v4 + zstd** | v4 → `compression.compress` | v4 body run through compression | Largest / most repetitive payloads |

A single universal `decode()` round-trips all profiles — pass it a `str` or `bytes` and it dispatches on the header.

## Install

```bash
git clone https://github.com/fahrenheit-research/AgentWire.git
cd AgentWire
pip install -e .
```

AgentWire's core (standard / champion / binary / v4) is **pure standard-library Python** — no required dependencies. The benchmark and PDF report are optional extras.

## Quick start

```python
from agentwire import encode, decode, encode_champion, MessageEnvelope

msg = {"task": "summarize", "url": "https://f-r.co", "max_tokens": 256}

# Standard — readable
wire = encode(msg, MessageEnvelope(priority="high", ttl_seconds=30))
decode(wire)["body"]            # -> {"task": "summarize", "url": ..., "max_tokens": 256}

# Champion — positional, smaller on the wire
champ = encode_champion(msg)
decode(champ)["body"]           # round-trips back to the original dict
```

### Binary & v4

```python
from agentwire import encode_champion_binary, decode
from agentwire.encoder_v4 import encode_champion_v4, decode_champion_v4

packet = encode_champion_binary(msg)      # bytes
decode(packet)["body"]                    # universal decoder handles bytes

v4 = encode_champion_v4(msg)              # interned + varint + sigils
decode_champion_v4(v4)                    # dedicated v4 round-trip
```

### Envelopes

```python
from agentwire import MessageEnvelope, ErrorEnvelope

MessageEnvelope(
    priority="critical",        # critical | high | normal | background
    correlation_id="req-42",    # tie a reply back to its request
    ttl_seconds=15,             # drop if stale
)

ErrorEnvelope(code="RATE_LIMIT", message="slow down", retry_after=5)
```

## Benchmarks

A deterministic harness (`benchmark.py`) compares every AgentWire profile against **JSON, TOON, ZOON, ISON, and TERSE**, and `report.py` renders the results to a PDF.

```bash
pip install reportlab        # only needed for the PDF report
python benchmark.py
```

> **Methodology note:** byte counts are exact and byte-for-byte reproducible. Token figures are *estimated* (the standard ~bytes/4 heuristic with per-format calibration) because `tiktoken` isn't assumed present — treat token deltas as indicative, byte deltas as exact.

## Status

The serialization core — all five profiles, the envelopes, and the universal decoder — is implemented and round-trips today. `compression.py` currently uses `zlib` as a zero-dependency stand-in for `zstd` (the API is stable; swapping in real `zstd` doesn't change call sites).

---

<div align="center">

**⟨ ◇ ⟩ &nbsp; Fahrenheit Research** — building intelligence that acts.

[f-r.co](https://f-r.co) · MIT Licensed

</div>
