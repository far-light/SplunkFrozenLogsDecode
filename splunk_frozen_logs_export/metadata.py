"""
Metadata type definitions and parser for Splunk journal format.
"""

from dataclasses import dataclass
from typing import Tuple
from . import varint


@dataclass
class RawdataMetaKeyItemType:
    """Metadata type information."""
    representation: int
    extra_ints_needed: int
    
    def is_float_type(self) -> bool:
        """Check if this is a floating point type."""
        return (self.representation & 0x2) != 0


# Metadata type constants
RMKI_TYPE_STRING = RawdataMetaKeyItemType(0, 1)
RMKI_TYPE_FLOAT32 = RawdataMetaKeyItemType(2, 1)
RMKI_TYPE_FLOAT32_SIGFIGS = RawdataMetaKeyItemType(3, 2)
RMKI_TYPE_OFFSET_LEN = RawdataMetaKeyItemType(4, 2)
RMKI_TYPE_FLOAT32_PRECISION = RawdataMetaKeyItemType(6, 2)
RMKI_TYPE_FLOAT32_SIGFIGS_PRECISION = RawdataMetaKeyItemType(7, 3)
RMKI_TYPE_UNSIGNED = RawdataMetaKeyItemType(8, 1)
RMKI_TYPE_SIGNED = RawdataMetaKeyItemType(9, 1)
RMKI_TYPE_FLOAT64 = RawdataMetaKeyItemType(10, 1)
RMKI_TYPE_FLOAT64_SIGFIGS = RawdataMetaKeyItemType(11, 2)
RMKI_TYPE_OFFSET_LEN_WENCODING = RawdataMetaKeyItemType(12, 3)
RMKI_TYPE_FLOAT64_PRECISION = RawdataMetaKeyItemType(14, 2)
RMKI_TYPE_FLOAT64_SIGFIGS_PRECISION = RawdataMetaKeyItemType(15, 0)

VALUES_IN_ORDER = [
    RMKI_TYPE_STRING,
    RawdataMetaKeyItemType(0, 0),  # placeholder
    RMKI_TYPE_FLOAT32,
    RMKI_TYPE_FLOAT32_SIGFIGS,
    RMKI_TYPE_OFFSET_LEN,
    RawdataMetaKeyItemType(0, 0),  # placeholder
    RMKI_TYPE_FLOAT32_PRECISION,
    RMKI_TYPE_FLOAT32_SIGFIGS_PRECISION,
    RMKI_TYPE_UNSIGNED,
    RMKI_TYPE_SIGNED,
    RMKI_TYPE_FLOAT64,
    RMKI_TYPE_FLOAT64_SIGFIGS,
    RMKI_TYPE_OFFSET_LEN_WENCODING,
    RawdataMetaKeyItemType(0, 0),  # placeholder
    RMKI_TYPE_FLOAT64_PRECISION,
    RMKI_TYPE_FLOAT64_SIGFIGS_PRECISION,
]


def get_type_from_combined(v: int) -> RawdataMetaKeyItemType:
    """Get metadata type from combined value."""
    return VALUES_IN_ORDER[v & 0xF]


def read_metadata(peek: bytes, opcode: int) -> int:
    """
    Read metadata from a peeked buffer.
    
    Args:
        peek: Peeked byte buffer
        opcode: The event opcode
        
    Returns:
        Number of bytes consumed
        
    Raises:
        ValueError: If varint cannot be decoded
    """
    meta_key, n = varint.decode_uvarint(peek)
    if n < 0:
        raise ValueError("Cannot read varint for meta_key")
    peek_offset = n
    
    num_to_read = -1
    
    if opcode <= 2:
        meta_key <<= 3
        # TODO: Add metaKey
        num_to_read = 1
    else:
        if opcode < 36:
            meta_key <<= 2
        # TODO: Add metaKey
        
        t = get_type_from_combined(meta_key)
        num_to_read = t.extra_ints_needed
    
    for _ in range(num_to_read):
        long_val, n = varint.decode_varint(peek[peek_offset:])
        if n < 0:
            raise ValueError("Cannot read varint for metadata value")
        peek_offset += n
        # TODO: Add long_val
    
    return peek_offset
