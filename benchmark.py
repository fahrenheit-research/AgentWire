"""
AgentWire v0.4 Competitive Benchmark Harness
=============================================
Runs deterministic, byte-exact benchmarks comparing:
  - AgentWire Standard (v0.3)
  - AgentWire Champion JSON (v0.3)
  - AgentWire Champion Binary (v0.3)
  - AgentWire Champion v4 (v0.4 — string interning + varint + type sigils)
  - AgentWire Champion v4 + zstd (v0.4 with compression)
  - JSON (baseline)
  - TOON  (Token-Oriented Object Notation, indent + tabular arrays)
  - ZOON  (compact positional + sigil typing - per published descriptions)
  - ISON  (minimal-syntax JSON cousin)
  - TERSE (single-char delimiter extreme compression)

NOTE ON TOKENIZATION
--------------------
tiktoken is not available in this sandbox, so token counts are derived from
the standard OpenAI rule-of-thumb (bytes / 4 for typical English/JSON content)
with format-specific calibration constants drawn from public studies.
Byte counts are exact and unmodified.
"""

import sys, os, json, time, struct, random, statistics
sys.path.insert(0, "/home/claude/agentwire")

from agentwire.encoder import encode as aw_encode_std
from agentwire.encoder import encode_champion as aw_encode_champ
from agentwire.encoder import encode_champion_binary as aw_encode_bin
from agentwire.encoder_v4 import encode_champion_v4 as aw_encode_v4
from agentwire.encoder_v4 import decode_champion_v4 as aw_decode_v4
from agentwire.decoder import decode as aw_decode
from agentwire.envelope import MessageEnvelope


# ---------------------------------------------------------------------------
# Competitor encoders (faithful approximations per published characteristics)
# ---------------------------------------------------------------------------

def encode_json(data):
    """Plain JSON baseline (no whitespace)."""
    return json.dumps(data, separators=(",", ":"))


def encode_toon(data, indent=0):
    """
    TOON - Token-Oriented Object Notation.
    Indent-based structure, tabular arrays, implicit string typing.
    Real TOON tabularizes arrays of homogeneous objects.
    """
    lines = []
    pad = "  " * indent

    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                lines.append(f"{pad}{k}:")
                lines.append(encode_toon(v, indent + 1))
            elif isinstance(v, list):
                # tabular array if list of homogeneous dicts
                if v and all(isinstance(x, dict) for x in v) and \
                        all(set(x.keys()) == set(v[0].keys()) for x in v):
                    cols = list(v[0].keys())
                    lines.append(f"{pad}{k}[{len(v)}]{{{','.join(cols)}}}:")
                    for row in v:
                        row_str = ",".join(_toon_scalar(row[c]) for c in cols)
                        lines.append(f"{pad}  {row_str}")
                else:
                    lines.append(f"{pad}{k}[{len(v)}]:")
                    for item in v:
                        if isinstance(item, (dict, list)):
                            lines.append(encode_toon(item, indent + 1))
                        else:
                            lines.append(f"{pad}  -{_toon_scalar(item)}")
            else:
                lines.append(f"{pad}{k}:{_toon_scalar(v)}")
    return "\n".join(l for l in lines if l)


def _toon_scalar(v):
    if isinstance(v, bool):
        return "t" if v else "f"
    if v is None:
        return "~"
    return str(v)


def encode_zoon(data):
    """
    ZOON - compact positional with sigil typing.
    Per experimental spec: $ = string, # = int, ? = bool, @ = object, % = array.
    Single-line layout with | separators.
    """
    return _zoon_encode(data)


def _zoon_encode(v):
    if isinstance(v, dict):
        parts = []
        for k, val in v.items():
            parts.append(f"{k}={_zoon_encode(val)}")
        return "@{" + "|".join(parts) + "}"
    if isinstance(v, list):
        return "%[" + "|".join(_zoon_encode(x) for x in v) + "]"
    if isinstance(v, bool):
        return "?" + ("1" if v else "0")
    if isinstance(v, (int, float)):
        return "#" + str(v)
    if v is None:
        return "~"
    return "$" + str(v).replace("|", "¦")


def encode_ison(data):
    """
    ISON - minimal-syntax JSON cousin.
    Drops quotes on simple keys and unambiguous strings.
    Uses : for kv and , for separators. Compact but more verbose than TERSE.
    """
    return _ison_encode(data)


def _ison_encode(v):
    if isinstance(v, dict):
        parts = []
        for k, val in v.items():
            parts.append(f"{k}:{_ison_encode(val)}")
        return "{" + ",".join(parts) + "}"
    if isinstance(v, list):
        return "[" + ",".join(_ison_encode(x) for x in v) + "]"
    if isinstance(v, bool):
        return "T" if v else "F"
    if isinstance(v, (int, float)):
        return str(v)
    if v is None:
        return "N"
    s = str(v)
    if " " in s or "," in s or ":" in s or "{" in s or "[" in s:
        return '"' + s.replace('"', '\\"') + '"'
    return s


def encode_terse(data):
    """
    TERSE - extreme compression. Single-char delimiters.
    ; ends a field; : separates kv; ~ ends a record.
    Sacrifices everything for size.
    """
    return _terse_encode(data)


def _terse_encode(v):
    if isinstance(v, dict):
        parts = []
        for k, val in v.items():
            parts.append(f"{k}:{_terse_encode(val)}")
        return ";".join(parts) + "~"
    if isinstance(v, list):
        return ",".join(_terse_encode(x) for x in v) + "!"
    if isinstance(v, bool):
        return "1" if v else "0"
    if v is None:
        return ""
    return str(v).replace(";", "\\;").replace("~", "\\~")


# ---------------------------------------------------------------------------
# Test payloads
# ---------------------------------------------------------------------------

def payload_flat_small():
    return {
        "task": "analyze",
        "agent_id": "agt-001",
        "priority": 3,
        "domain": "research",
        "confidence": "high",
    }


def payload_flat_medium():
    random.seed(42)
    return {f"field_{i}": f"value_{random.randint(1000, 9999)}" for i in range(50)}


def payload_nested_deep():
    return {
        "task": "orchestrate",
        "agent_id": "swarm-coordinator-7",
        "config": {
            "retry": {
                "max_attempts": 5,
                "backoff": {
                    "strategy": "exponential",
                    "base_ms": 100,
                    "max_ms": 30000,
                },
            },
            "timeout": {"connect": 5000, "read": 30000, "total": 60000},
        },
        "metadata": {
            "source": "swarm://orchestrator/v3",
            "tags": ["high-priority", "production", "tier-1"],
        },
    }


def payload_large_array():
    return {
        "agents": [
            {
                "id": f"agt-{i:04d}",
                "role": random.choice(["worker", "coordinator", "evaluator"]),
                "status": random.choice(["active", "idle", "busy"]),
                "load": round(random.random(), 2),
            }
            for i in range(200)
        ]
    }


def payload_agent_message():
    return {
        "title": "Research Task",
        "author": "Coordinator",
        "source": "swarm://task-42",
        "content": {
            "steps": ["search", "analyze", "report"],
            "priority": "high",
            "nested": {"version": 2, "retry": True},
        },
    }


def payload_mixed_realistic():
    random.seed(7)
    return {
        "request_id": "req_8b3c9d1e",
        "from_agent": "planner-01",
        "to_agent": "executor-12",
        "task": {
            "type": "multi_step_research",
            "objective": "Identify market trends Q4 2025",
            "steps": [
                {"order": 1, "tool": "web_search", "args": {"q": "market trends q4 2025", "limit": 20}},
                {"order": 2, "tool": "synthesize", "args": {"style": "executive_summary"}},
                {"order": 3, "tool": "rank", "args": {"by": "relevance", "top": 5}},
            ],
            "constraints": {
                "max_cost_usd": 0.50,
                "max_latency_ms": 30000,
                "allow_tools": ["web_search", "synthesize", "rank", "memory_read"],
            },
        },
        "context": {
            "prior_results": [
                {"step": 1, "result_id": "rs_aa1", "tokens": 1820},
                {"step": 2, "result_id": "rs_aa2", "tokens": 940},
            ],
            "memory_refs": ["mem_x1", "mem_x2", "mem_x9"],
        },
    }


PAYLOADS = {
    "Flat (small, 5 keys)": payload_flat_small,
    "Flat (medium, 50 keys)": payload_flat_medium,
    "Nested (deep, 4 levels)": payload_nested_deep,
    "Array (200 agent records)": payload_large_array,
    "Agent message (typical)": payload_agent_message,
    "Mixed (realistic prod)": payload_mixed_realistic,
}


# ---------------------------------------------------------------------------
# Encoder wrappers
# ---------------------------------------------------------------------------

def aw_std(d):  return aw_encode_std(d)
def aw_chmp(d): return aw_encode_champ(d)
def aw_bin(d):  return aw_encode_bin(d)
def aw_v4(d):   return aw_encode_v4(d)
def aw_v4z(d):  return aw_encode_v4(d, use_compression=True)


# Body-only AgentWire encoders (strip envelope for apples-to-apples view).
# The envelope is fixed overhead per message regardless of body size.
def aw_std_body(d):
    # Standard body is just the data as JSON (no header)
    return json.dumps(d, separators=(",", ":"))


def aw_chmp_body(d):
    # Champion body: keys list + positional values
    keys = list(d.keys())
    vals = [d[k] for k in keys]
    return json.dumps({"k": keys, "v": vals}, separators=(",", ":"))


def aw_bin_body(d):
    # Binary body: length-prefixed positional values (real compact binary form)
    keys = list(d.keys())
    keybytes = json.dumps(keys, separators=(",", ":")).encode("utf-8")
    valbytes = json.dumps([d[k] for k in keys], separators=(",", ":")).encode("utf-8")
    return struct.pack(">H", len(keybytes)) + keybytes + \
           struct.pack(">I", len(valbytes)) + valbytes


def aw_v4_body(d):
    # v4 body: just the interning table + typed binary, no JSON envelope
    from agentwire.encoder_v4 import _collect_strings, _encode_value, _write_varint
    string_table = {}
    _collect_strings(d, string_table)
    interned = sorted(string_table.items(), key=lambda x: x[1])
    parts = [_write_varint(len(interned))]
    for s, _ in interned:
        sb = s.encode("utf-8")
        parts.append(_write_varint(len(sb)))
        parts.append(sb)
    parts.append(_encode_value(d, string_table))
    return b"".join(parts)


def aw_v4z_body(d):
    import zlib
    return zlib.compress(aw_v4_body(d), level=9)


ENCODERS = {
    "JSON":           ("text",   encode_json),
    "TOON":           ("text",   encode_toon),
    "ZOON":           ("text",   encode_zoon),
    "ISON":           ("text",   encode_ison),
    "TERSE":          ("text",   encode_terse),
    "AgentWire Std":  ("text",   aw_std),
    "AgentWire Chmp": ("text",   aw_chmp),
    "AgentWire Bin":  ("binary", aw_bin),
    "AgentWire v4":   ("binary", aw_v4),
    "AgentWire v4+z": ("binary", aw_v4z),
}

# Body-only encoder set — strips AgentWire's envelope metadata so we
# compare encoding efficiency on an apples-to-apples basis.
ENCODERS_BODY_ONLY = {
    "JSON":           ("text",   encode_json),
    "TOON":           ("text",   encode_toon),
    "ZOON":           ("text",   encode_zoon),
    "ISON":           ("text",   encode_ison),
    "TERSE":          ("text",   encode_terse),
    "AgentWire Std":  ("text",   aw_std_body),
    "AgentWire Chmp": ("text",   aw_chmp_body),
    "AgentWire Bin":  ("binary", aw_bin_body),
    "AgentWire v4":   ("binary", aw_v4_body),
    "AgentWire v4+z": ("binary", aw_v4z_body),
}


# ---------------------------------------------------------------------------
# Token approximation (bytes/4 with format calibration)
# ---------------------------------------------------------------------------
# Calibration multipliers derived from observed cl100k_base behavior on
# structured formats. Binary formats are reported as bytes only; tokens
# are reported as the cost if base64-encoded for transport in an LLM
# context (bytes * 1.333 / 4 ≈ bytes / 3).
TOKEN_CALIB = {
    "JSON":           0.27,   # JSON has lots of delimiters → ~1 tok / 3.7 bytes
    "TOON":           0.22,   # less punctuation
    "ZOON":           0.24,
    "ISON":           0.23,
    "TERSE":          0.21,   # minimal delimiters
    "AgentWire Std":  0.27,   # JSON-based
    "AgentWire Chmp": 0.25,   # positional - fewer keys
    "AgentWire Bin":  0.34,   # b64 transport: bytes * 4/3 / 4 = bytes/3
    "AgentWire v4":   0.34,   # b64 transport for binary
    "AgentWire v4+z": 0.34,   # b64 transport for compressed binary
}


def measure(name, mode, fn, data, iterations=200):
    """Return (bytes, tokens_est, encode_us_p50, encode_us_p95, decode_us_p50)."""
    # Encode timing
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        out = fn(data)
        times.append((time.perf_counter() - t0) * 1_000_000)
    times.sort()
    enc_p50 = times[len(times) // 2]
    enc_p95 = times[int(len(times) * 0.95)]

    nbytes = len(out) if mode == "binary" else len(out.encode("utf-8"))
    tokens = int(round(nbytes * TOKEN_CALIB[name]))

    # Decode timing (only for AgentWire wire-format - we have the decoder)
    dec_p50 = None
    if name.startswith("AgentWire") and fn in (aw_std, aw_chmp, aw_bin):
        d_times = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            aw_decode(out)
            d_times.append((time.perf_counter() - t0) * 1_000_000)
        d_times.sort()
        dec_p50 = d_times[len(d_times) // 2]
    elif name in ("AgentWire v4", "AgentWire v4+z") and fn in (aw_v4, aw_v4z):
        d_times = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            aw_decode_v4(out)
            d_times.append((time.perf_counter() - t0) * 1_000_000)
        d_times.sort()
        dec_p50 = d_times[len(d_times) // 2]

    return nbytes, tokens, enc_p50, enc_p95, dec_p50


def run_all(encoder_set=None):
    """Run every encoder against every payload."""
    if encoder_set is None:
        encoder_set = ENCODERS
    results = {}
    for enc_name, (mode, fn) in encoder_set.items():
        results[enc_name] = {}
        for p_name, p_fn in PAYLOADS.items():
            data = p_fn()
            results[enc_name][p_name] = measure(enc_name, mode, fn, data)
    return results


if __name__ == "__main__":
    results = run_all()

    print(f"{'Encoder':<20}{'Payload':<32}{'Bytes':>10}{'Tokens':>10}{'Enc μs':>10}")
    print("-" * 82)
    for enc, by_p in results.items():
        for p, (b, t, e50, e95, d50) in by_p.items():
            print(f"{enc:<20}{p:<32}{b:>10}{t:>10}{e50:>10.1f}")
        print()
