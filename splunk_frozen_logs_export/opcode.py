"""
Opcode definitions and decoder registry for Splunk journal format.
"""

from enum import IntEnum
from typing import Protocol, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .journal import JournalDecoder
    from .reader import CountedReader


class Opcode(IntEnum):
    """Journal file opcodes."""
    NOP = 0
    OLDSTYLE_EVENT = 1
    OLDSTYLE_EVENT_WITH_HASH = 2
    NEW_HOST = 3
    NEW_SOURCE = 4
    NEW_SOURCE_TYPE = 5
    NEW_STRING = 6
    DELETE = 8
    SPLUNK_PRIVATE = 9
    HEADER = 10
    HASH_SLICE = 11


class Decoder(Protocol):
    """Protocol for opcode decoders."""
    
    def decode(self, jd: 'JournalDecoder', reader: 'CountedReader', opcode: int) -> None:
        """
        Decode data for this opcode.
        
        Args:
            jd: The journal decoder instance
            reader: The counted reader
            opcode: The opcode byte
        """
        ...


def get_decoder(opcode: Opcode) -> Optional['Decoder']:
    """
    Get the decoder for a specific opcode.
    
    Args:
        opcode: The opcode to get a decoder for
        
    Returns:
        Decoder instance or None if no specific decoder exists
    """
    # Import here to avoid circular imports
    from . import decoder as dec
    
    decoders = {
        Opcode.HEADER: dec.HeaderDecoder(),
        Opcode.SPLUNK_PRIVATE: dec.SplunkPrivateDecoder(),
        Opcode.NEW_HOST: dec.StringFieldDecoder(Opcode.NEW_HOST),
        Opcode.NEW_SOURCE: dec.StringFieldDecoder(Opcode.NEW_SOURCE),
        Opcode.NEW_SOURCE_TYPE: dec.StringFieldDecoder(Opcode.NEW_SOURCE_TYPE),
        Opcode.NEW_STRING: dec.StringFieldDecoder(Opcode.NEW_STRING),
        Opcode.OLDSTYLE_EVENT: dec.EventDecoder(),
        Opcode.OLDSTYLE_EVENT_WITH_HASH: dec.EventDecoder(),
        Opcode.NOP: None,
    }
    
    return decoders.get(opcode)
