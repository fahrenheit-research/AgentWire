"""
AgentWire v0.4 Champion Encoder (Optimized)
Beats TOON on raw size by using:
- String interning table
- Type sigils (1-byte type tags)
- Varint (LEB128) encoding for integers and lengths
- Compact binary body (no JSON, no quotes, no colons for primitives)

This is the production-grade reference that closes the gap mentioned in the May 2026 benchmark report.
"""

import struct
from typing import Any, Dict, List, Tuple
from .envelope import MessageEnvelope


# ---------------- Varint (unsigned LEB128) helpers ----------------

def _write_varint(value: int) -> bytes:
    """Encode unsigned integer as LEB128 varint."""
    if value < 0:
        raise ValueError("Varint only supports unsigned integers")
    result = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            byte |= 0x80
        result.append(byte)
        if not value:
            break
    return bytes(result)


def _read_varint(data: bytes, offset: int) -> Tuple[int, int]:
    """Decode LEB128 varint, return (value, new_offset)."""
    result = 0
    shift = 0
    while True:
        if offset >= len(data):
            raise ValueError("Unexpected end of varint")
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        shift += 7
        if not (byte & 0x80):
            break
    return result, offset


# ---------------- Type sigils ----------------

TYPE_NULL   = 0x00
TYPE_FALSE  = 0x01
TYPE_TRUE   = 0x02
TYPE_INT    = 0x03   # followed by varint
TYPE_FLOAT  = 0x04   # followed by 8-byte double
TYPE_STR    = 0x05   # followed by varint (intern index)
TYPE_ARRAY  = 0x06   # followed by varint length, then N elements
TYPE_OBJECT = 0x07   # followed by varint keycount, then key indices + values


def _collect_strings(obj: Any, string_table: Dict[str, int]) -> None:
    """Recursively collect all strings for interning."""
    if isinstance(obj, str):
        if obj not in string_table:
            string_table[obj] = len(string_table)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k not in string_table:
                string_table[k] = len(string_table)
            _collect_strings(v, string_table)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _collect_strings(item, string_table)


def _encode_value(value: Any, string_table: Dict[str, int]) -> bytes:
    """Encode a single value using type sigils + varint + interning."""
    if value is None:
        return bytes([TYPE_NULL])
    if isinstance(value, bool):
        return bytes([TYPE_TRUE if value else TYPE_FALSE])
    if isinstance(value, int):
        return bytes([TYPE_INT]) + _write_varint(value)
    if isinstance(value, float):
        return bytes([TYPE_FLOAT]) + struct.pack("<d", value)
    if isinstance(value, str):
        idx = string_table[value]
        return bytes([TYPE_STR]) + _write_varint(idx)
    if isinstance(value, (list, tuple)):
        parts = [bytes([TYPE_ARRAY]), _write_varint(len(value))]
        for item in value:
            parts.append(_encode_value(item, string_table))
        return b"".join(parts)
    if isinstance(value, dict):
        keys = list(value.keys())
        parts = [bytes([TYPE_OBJECT]), _write_varint(len(keys))]
        for k in keys:
            idx = string_table[k]
            parts.append(_write_varint(idx))
            parts.append(_encode_value(value[k], string_table))
        return b"".join(parts)
    # Fallback for unsupported types -> treat as string
    s = str(value)
    idx = string_table.get(s, len(string_table))
    if s not in string_table:
        string_table[s] = idx
    return bytes([TYPE_STR]) + _write_varint(idx)


def encode_champion_v4(
    data: Dict[str, Any],
    envelope: MessageEnvelope = None,
    use_compression: bool = False,
    compression_algorithm: str = "zstd"
) -> bytes:
    """
    v0.4 Champion Binary encoder.
    Achieves TOON-beating density via interning + type sigils + varint.
    """
    from .compression import compress as compress_data

    env = envelope or MessageEnvelope(profile="champion-v4")
    env.profile = "champion-v4"

    # 1. Collect all strings for interning (keys + string values)
    string_table: Dict[str, int] = {}
    _collect_strings(data, string_table)
    interned_strings = sorted(string_table.items(), key=lambda x: x[1])
    interned_list = [s for s, _ in interned_strings]

    # 2. Build intern table section
    body_parts = []
    body_parts.append(_write_varint(len(interned_list)))  # count
    for s in interned_list:
        s_bytes = s.encode("utf-8")
        body_parts.append(_write_varint(len(s_bytes)))
        body_parts.append(s_bytes)

    # 3. Encode the actual data using the intern table
    encoded_data = _encode_value(data, string_table)
    body_parts.append(encoded_data)

    body_bytes = b"".join(body_parts)

    # 4. Header (still JSON for envelope compatibility + discovery)
    header = env.to_dict()
    header["v"] = 4
    header["interned"] = len(interned_list)
    header_bytes = __import__("json").dumps(header, separators=(",", ":")).encode("utf-8")

    if use_compression:
        body_bytes = compress_data(body_bytes, compression_algorithm)
        header["compressed"] = True
        header["compression"] = compression_algorithm
        header_bytes = __import__("json").dumps(header, separators=(",", ":")).encode("utf-8")

    # 5. Final packet (same envelope layout as v0.3 for compatibility)
    packet = (
        struct.pack(">I", len(header_bytes)) +
        header_bytes +
        struct.pack(">I", len(body_bytes)) +
        body_bytes
    )
    return packet


def decode_champion_v4(data: bytes) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Minimal decoder for v0.4 packets (for verification and round-trip testing).
    Returns (header, decoded_body)
    """
    import json
    offset = 0
    header_len = struct.unpack(">I", data[offset:offset+4])[0]
    offset += 4
    header = json.loads(data[offset:offset+header_len].decode("utf-8"))
    offset += header_len

    body_len = struct.unpack(">I", data[offset:offset+4])[0]
    offset += 4
    body = data[offset:offset+body_len]

    # Decompress if needed
    if header.get("compressed"):
        from .compression import decompress
        body = decompress(body, header.get("compression", "zstd"))

    # Parse intern table
    intern_count, offset = _read_varint(body, 0)
    intern_table = []
    for _ in range(intern_count):
        slen, offset = _read_varint(body, offset)
        s = body[offset:offset+slen].decode("utf-8")
        intern_table.append(s)
        offset += slen

    # Decode value (simplified recursive decoder)
    def _decode_value(b: bytes, o: int) -> Tuple[Any, int]:
        t = b[o]
        o += 1
        if t == TYPE_NULL:
            return None, o
        if t == TYPE_FALSE:
            return False, o
        if t == TYPE_TRUE:
            return True, o
        if t == TYPE_INT:
            v, o = _read_varint(b, o)
            return v, o
        if t == TYPE_FLOAT:
            v = struct.unpack("<d", b[o:o+8])[0]
            return v, o + 8
        if t == TYPE_STR:
            idx, o = _read_varint(b, o)
            return intern_table[idx], o
        if t == TYPE_ARRAY:
            length, o = _read_varint(b, o)
            arr = []
            for _ in range(length):
                val, o = _decode_value(b, o)
                arr.append(val)
            return arr, o
        if t == TYPE_OBJECT:
            keycount, o = _read_varint(b, o)
            obj = {}
            for _ in range(keycount):
                kidx, o = _read_varint(b, o)
                key = intern_table[kidx]
                val, o = _decode_value(b, o)
                obj[key] = val
            return obj, o
        raise ValueError(f"Unknown type tag: {t}")

    decoded_body, _ = _decode_value(body, offset)
    return header, decoded_body
