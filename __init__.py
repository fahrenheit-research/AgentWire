"""
AgentWire v0.3.0
Created by Fahrenheit Research and made open source.
"""
from .encoder import encode, encode_champion, encode_champion_binary
from .decoder import decode
from .envelope import MessageEnvelope, ErrorEnvelope

__version__ = "0.3.0"
__all__ = [
    "encode", "encode_champion", "encode_champion_binary",
    "decode", "MessageEnvelope", "ErrorEnvelope"
]