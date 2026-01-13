"""
Optimized varint decoder for Splunk journal files.

Based on: https://www.dolthub.com/blog/2021-01-08-optimizing-varint-decoding/
"""

from typing import Tuple


def decode_uvarint(buf: bytes) -> Tuple[int, int]:
    """
    Decode an unsigned varint from a byte buffer.
    
    Args:
        buf: Byte buffer containing the varint
        
    Returns:
        Tuple of (decoded_value, bytes_consumed)
        Returns (0, -N) on error where N is the number of bytes read
    """
    if len(buf) < 1:
        return 0, -1
    
    b = buf[0]
    if b < 0x80:
        return b, 1
    
    if len(buf) < 2:
        return 0, -2
    x = b & 0x7f
    b = buf[1]
    if b < 0x80:
        return x | (b << 7), 2
    
    if len(buf) < 3:
        return 0, -3
    x |= (b & 0x7f) << 7
    b = buf[2]
    if b < 0x80:
        return x | (b << 14), 3
    
    if len(buf) < 4:
        return 0, -4
    x |= (b & 0x7f) << 14
    b = buf[3]
    if b < 0x80:
        return x | (b << 21), 4
    
    if len(buf) < 5:
        return 0, -5
    x |= (b & 0x7f) << 21
    b = buf[4]
    if b < 0x80:
        return x | (b << 28), 5
    
    if len(buf) < 6:
        return 0, -6
    x |= (b & 0x7f) << 28
    b = buf[5]
    if b < 0x80:
        return x | (b << 35), 6
    
    if len(buf) < 7:
        return 0, -7
    x |= (b & 0x7f) << 35
    b = buf[6]
    if b < 0x80:
        return x | (b << 42), 7
    
    if len(buf) < 8:
        return 0, -8
    x |= (b & 0x7f) << 42
    b = buf[7]
    if b < 0x80:
        return x | (b << 49), 8
    
    if len(buf) < 9:
        return 0, -9
    x |= (b & 0x7f) << 49
    b = buf[8]
    if b < 0x80:
        return x | (b << 56), 9
    
    if len(buf) < 10:
        return 0, -10
    x |= (b & 0x7f) << 56
    b = buf[9]
    if b < 0x80:
        return x | (b << 63), 10
    
    return 0, -10


def decode_varint(buf: bytes) -> Tuple[int, int]:
    """
    Decode a signed varint (zigzag encoded) from a byte buffer.
    
    Args:
        buf: Byte buffer containing the varint
        
    Returns:
        Tuple of (decoded_value, bytes_consumed)
    """
    ux, n = decode_uvarint(buf)
    x = ux >> 1
    if ux & 1:
        x = ~x
    return x, n
