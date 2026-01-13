"""
Event data structure for Splunk journal entries.
"""

from dataclasses import dataclass, field
from typing import Optional


HASH_SIZE = 20


@dataclass
class Event:
    """
    Represents a single event from a Splunk journal.
    
    Events contain the log message along with metadata about indexing,
    storage, and optional hash values.
    """
    
    message_length: int = 0
    has_extended_storage: bool = False
    extended_storage_len: int = 0
    has_hash: bool = False
    hash: bytes = field(default_factory=lambda: b'\x00' * HASH_SIZE)
    stream_id: int = 0
    stream_offset: int = 0
    stream_sub_offset: int = 0
    index_time: int = 0
    sub_seconds: int = 0
    metadata_count: int = 0
    message: bytearray = field(default_factory=bytearray)
    include_punctuation: bool = False
    
    def message_bytes(self) -> bytes:
        """Get the message as bytes."""
        return bytes(self.message[:self.message_length])
    
    def message_string(self) -> str:
        """Get the message as a UTF-8 string."""
        return self.message[:self.message_length].decode('utf-8', errors='replace')
    
    def reset(self) -> None:
        """Reset all fields for reuse."""
        self.message_length = 0
        self.has_extended_storage = False
        self.extended_storage_len = 0
        self.has_hash = False
        self.hash = b'\x00' * HASH_SIZE
        self.stream_id = 0
        self.stream_offset = 0
        self.stream_sub_offset = 0
        self.index_time = 0
        self.sub_seconds = 0
        self.metadata_count = 0
        self.message.clear()
        self.include_punctuation = False
    
    def __str__(self) -> str:
        """String representation of the event."""
        return (
            f"messageLength: {self.message_length} - "
            f"extendedStorageLen: {self.extended_storage_len} - "
            f"hash: {self.hash.hex()} - "
            f"streamID: {self.stream_id} - "
            f"streamOffset: {self.stream_offset} - "
            f"streamSubOffset: {self.stream_sub_offset} - "
            f"indexTime: {self.index_time} - "
            f"subSeconds: {self.sub_seconds} - "
            f"metadataCount: {self.metadata_count} - "
            f"message: {self.message_string()} - "
            f"includePunctuation: {self.include_punctuation}"
        )
