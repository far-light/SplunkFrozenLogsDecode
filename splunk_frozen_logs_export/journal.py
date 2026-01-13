"""
Main journal decoder for Splunk journal files.
"""

import io
import os
import logging
from pathlib import Path
from typing import Iterator, Dict, List, Optional
from dataclasses import dataclass, field

import zstandard as zstd

from .reader import CountedReader
from .event import Event
from .opcode import Opcode, get_decoder

logger = logging.getLogger(__name__)


@dataclass
class DecoderState:
    """State maintained across journal decoding."""
    fields: Dict[int, List[str]] = field(default_factory=dict)
    base_time: int = 0
    active_host: int = 0
    active_source: int = 0
    active_source_type: int = 0


class JournalDecoder:
    """
    Decoder for Splunk journal files.
    
    Provides an iterator interface for reading events from a journal.
    """
    
    def __init__(self, path: str):
        """
        Initialize a journal decoder.
        
        Args:
            path: Path to the bucket directory containing rawdata/journal.zst
        """
        self.name = path
        self.reader = CountedReader(self._open_journal(path))
        self.state = DecoderState()
        self.event = Event()
        self.opcode = 0
        self._error: Optional[Exception] = None
    
    def _open_journal(self, path: str) -> io.BufferedReader:
        """
        Open and decompress a journal file.
        
        Args:
            path: Path to the bucket directory
            
        Returns:
            Buffered reader for the decompressed journal
            
        Raises:
            FileNotFoundError: If journal doesn't exist
        """
        journal_dir = Path(path) / "rawdata"
        
        # Try .zst first (compressed)
        journal_path = journal_dir / "journal.zst"
        if journal_path.exists():
            file_handle = open(journal_path, 'rb')
            dctx = zstd.ZstdDecompressor()
            decompressed = dctx.stream_reader(file_handle)
            return io.BufferedReader(decompressed, buffer_size=8 * 4096)
        
        # Try uncompressed journal
        journal_path = journal_dir / "journal"
        if journal_path.exists():
            file_handle = open(journal_path, 'rb')
            return io.BufferedReader(file_handle, buffer_size=8 * 4096)
        
        raise FileNotFoundError(f"Journal not found at {journal_dir}/journal.zst or {journal_dir}/journal")
    
    @property
    def host(self) -> str:
        """Get the current active host."""
        if self.state.active_host > 0:
            hosts = self.state.fields.get(Opcode.NEW_HOST, [])
            if self.state.active_host <= len(hosts):
                return hosts[self.state.active_host - 1]
        return ""
    
    @property
    def source(self) -> str:
        """Get the current active source."""
        if self.state.active_source > 0:
            sources = self.state.fields.get(Opcode.NEW_SOURCE, [])
            if self.state.active_source <= len(sources):
                return sources[self.state.active_source - 1]
        return ""
    
    @property
    def source_type(self) -> str:
        """Get the current active source type."""
        if self.state.active_source_type > 0:
            source_types = self.state.fields.get(Opcode.NEW_SOURCE_TYPE, [])
            if self.state.active_source_type <= len(source_types):
                return source_types[self.state.active_source_type - 1]
        return ""
    
    def _is_event_opcode(self, opcode: int) -> bool:
        """Check if an opcode represents an event."""
        return (
            opcode == Opcode.OLDSTYLE_EVENT or
            opcode == Opcode.OLDSTYLE_EVENT_WITH_HASH or
            (32 <= opcode <= 43)
        )
    
    def _decode_new_state(self, opcode: int) -> None:
        """
        Decode state change opcodes (17-31).
        
        These opcodes update active host, source, sourcetype, and base time.
        """
        from . import varint
        
        # Active host
        if opcode & 0x8:
            peek = self.reader.peek(10)
            self.state.active_host, n = varint.decode_uvarint(peek)
            if n < 0:
                raise ValueError("Cannot decode active_host")
            self.reader.discard(n)
        
        # Active source
        if opcode & 0x4:
            peek = self.reader.peek(10)
            self.state.active_source, n = varint.decode_uvarint(peek)
            if n < 0:
                raise ValueError("Cannot decode active_source")
            self.reader.discard(n)
        
        # Active source type
        if opcode & 0x2:
            peek = self.reader.peek(10)
            self.state.active_source_type, n = varint.decode_uvarint(peek)
            if n < 0:
                raise ValueError("Cannot decode active_source_type")
            self.reader.discard(n)
        
        # Base time
        if opcode & 0x1:
            import struct
            base_time_data = self.reader.read(4)
            self.state.base_time = struct.unpack('<i', base_time_data)[0]
    
    def _decode_next(self) -> None:
        """Decode the next opcode."""
        # Handle NOP (0x00) - just skip it
        if self.opcode == 0:
            return
        
        # Handle state change opcodes (17-31) first - these are not in the enum
        if 17 <= self.opcode <= 31:
            self._decode_new_state(self.opcode)
            return
        
        # Handle event opcodes (32-43) - also not all in the enum
        if self._is_event_opcode(self.opcode):
            from .decoder import EventDecoder
            EventDecoder().decode(self, self.reader, self.opcode)
            return
        
        # Try specific decoder for known opcodes
        try:
            decoder = get_decoder(Opcode(self.opcode))
            if decoder is not None:
                decoder.decode(self, self.reader, self.opcode)
                return
        except ValueError:
            # Opcode not in enum, will be caught below
            pass
        
        raise ValueError(f"Unknown opcode: 0x{self.opcode:02x}")
    
    def __iter__(self) -> Iterator[Event]:
        """Iterate over events in the journal."""
        return self
    
    def __next__(self) -> Event:
        """
        Get the next event from the journal.
        
        Returns:
            The next Event
            
        Raises:
            StopIteration: When end of journal is reached
        """
        while True:
            try:
                self.opcode = self.reader.read_byte()
                logger.debug(f"Read opcode: 0x{self.opcode:02x} at position {self.reader.pos-1}")
            except EOFError:
                logger.debug("End of file reached")
                raise StopIteration
            
            # Reset event if this is an event opcode
            if self._is_event_opcode(self.opcode):
                self.event.reset()
            
            try:
                self._decode_next()
            except Exception as e:
                import traceback
                logger.error(f"Error decoding opcode 0x{self.opcode:02x} at position {self.reader.pos}: {e}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                self._error = e
                raise StopIteration
            
            # If this was an event opcode, return the event
            if self._is_event_opcode(self.opcode):
                logger.debug(f"Returning event")
                return self.event
    
    def error(self) -> Optional[Exception]:
        """Get any error that occurred during decoding."""
        return self._error
