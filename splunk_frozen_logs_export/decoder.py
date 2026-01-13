"""
Specialized decoders for different Splunk journal opcodes.
"""

import struct
import logging
from typing import TYPE_CHECKING

from . import varint
from .metadata import read_metadata
from .event import HASH_SIZE

if TYPE_CHECKING:
    from .journal import JournalDecoder
    from .reader import CountedReader


logger = logging.getLogger(__name__)


class HeaderDecoder:
    """Decoder for journal header (Opcode.HEADER)."""
    
    def decode(self, jd: 'JournalDecoder', reader: 'CountedReader', opcode: int) -> None:
        """Decode journal header."""
        # Header structure: version (1 byte), align_bits (1 byte), base_index_time (4 bytes)
        header_data = reader.read(6)
        version, align_bits, base_index_time = struct.unpack('<BBI', header_data)
        
        logger.info(f"Journal {jd.name} - Version: {version}")
        align_mask = (1 << align_bits) - 1
        # TODO: Use align_mask


class SplunkPrivateDecoder:
    """Decoder for Splunk private data (Opcode.SPLUNK_PRIVATE)."""
    
    def decode(self, jd: 'JournalDecoder', reader: 'CountedReader', opcode: int) -> None:
        """Skip Splunk private data."""
        peek = reader.peek(10)
        length, n = varint.decode_uvarint(peek)
        if n < 0:
            raise ValueError("Cannot decode length for SPLUNK_PRIVATE")
        
        reader.discard(n)
        reader.discard(length)


class StringFieldDecoder:
    """Decoder for string fields (host, source, sourcetype, string)."""
    
    def __init__(self, field_opcode: int):
        """
        Initialize string field decoder.
        
        Args:
            field_opcode: The opcode this decoder handles
        """
        self.field_opcode = field_opcode
    
    def decode(self, jd: 'JournalDecoder', reader: 'CountedReader', opcode: int) -> None:
        """Decode a string field and add to state."""
        peek = reader.peek(10)
        length, n = varint.decode_uvarint(peek)
        if n < 0:
            raise ValueError("Cannot decode string length")
        
        reader.discard(n)
        string_data = reader.read(length)
        string_value = string_data.decode('utf-8', errors='replace')
        
        # Store in the appropriate field list
        if self.field_opcode not in jd.state.fields:
            jd.state.fields[self.field_opcode] = []
        jd.state.fields[self.field_opcode].append(string_value)


class EventDecoder:
    """Decoder for event data (Opcode.OLDSTYLE_EVENT*)."""
    
    def decode(self, jd: 'JournalDecoder', reader: 'CountedReader', opcode: int) -> None:
        """Decode event data - the most complex decoder."""
        # Read event metadata
        peek = reader.peek(8 * 10 + 8 + HASH_SIZE)  # Max varint size * fields + uint64 + hash
        peek_offset = 0
        
        # Message length
        jd.event.message_length, n = varint.decode_uvarint(peek[peek_offset:])
        peek_offset += n
        if n < 0:
            raise ValueError("Cannot decode message_length")
        
        # Add current position to message length
        jd.event.message_length += reader.pos + peek_offset
        
        # Extended storage length (if present)
        e_storage_len = 0
        jd.event.has_extended_storage = (opcode & 0x4) != 0
        if jd.event.has_extended_storage:
            jd.event.extended_storage_len, n = varint.decode_uvarint(peek[peek_offset:])
            peek_offset += n
            if n < 0:
                raise ValueError("Cannot decode extended_storage_len")
            e_storage_len = jd.event.extended_storage_len
        
        # Hash (if present)
        jd.event.has_hash = (opcode & 0x01) == 0
        if jd.event.has_hash:
            jd.event.hash = peek[peek_offset:peek_offset + HASH_SIZE]
            peek_offset += HASH_SIZE
        
        # Stream ID (uint64, little endian)
        jd.event.stream_id = struct.unpack('<Q', peek[peek_offset:peek_offset + 8])[0]
        peek_offset += 8
        
        # Stream offset
        jd.event.stream_offset, n = varint.decode_uvarint(peek[peek_offset:])
        peek_offset += n
        if n < 0:
            raise ValueError("Cannot decode stream_offset")
        
        # Stream sub-offset
        jd.event.stream_sub_offset, n = varint.decode_uvarint(peek[peek_offset:])
        peek_offset += n
        if n < 0:
            raise ValueError("Cannot decode stream_sub_offset")
        
        # Index time (signed varint + base time)
        index_time_delta, n = varint.decode_varint(peek[peek_offset:])
        peek_offset += n
        if n < 0:
            raise ValueError("Cannot decode index_time")
        jd.event.index_time = index_time_delta + jd.state.base_time
        
        # Sub-seconds
        jd.event.sub_seconds, n = varint.decode_uvarint(peek[peek_offset:])
        peek_offset += n
        if n < 0:
            raise ValueError("Cannot decode sub_seconds")
        
        # Metadata count
        jd.event.metadata_count, n = varint.decode_uvarint(peek[peek_offset:])
        peek_offset += n
        if n < 0:
            raise ValueError("Cannot decode metadata_count")
        
        # Discard what we've read
        reader.discard(peek_offset)
        
        # Read metadata entries
        if jd.event.metadata_count > 0:
            # Read metadata one at a time to avoid buffer issues
            for _ in range(jd.event.metadata_count):
                # Peek enough for one metadata entry (conservative estimate)
                metadata_peek = reader.peek(4 * 10)
                if len(metadata_peek) == 0:
                    raise ValueError("Unexpected end of stream while reading metadata")
                
                n = read_metadata(metadata_peek, opcode)
                reader.discard(n)
        
        # Extended storage (if present)
        if jd.event.has_extended_storage:
            e_storage = reader.read(e_storage_len)
            logger.error(f"Extended storage not fully implemented: {e_storage}")
        
        # Calculate actual message length
        jd.event.message_length = jd.event.message_length - reader.pos
        
        # Resize message buffer if needed
        if len(jd.event.message) < jd.event.message_length:
            # Allocate double the size to reduce reallocations
            jd.event.message = bytearray(jd.event.message_length * 2)
        
        # Read the actual message
        message_data = reader.read(jd.event.message_length)
        jd.event.message[:jd.event.message_length] = message_data
        
        # Include punctuation flag
        jd.event.include_punctuation = (opcode & 0x22) == 34
