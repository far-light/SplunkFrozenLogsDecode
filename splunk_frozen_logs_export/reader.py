"""
Buffered reader with position tracking for journal parsing.
"""

import io
from typing import Optional


class CountedReader:
    """
    A buffered reader that tracks the current byte position.
    
    This is essential for calculating message lengths in the journal format,
    where lengths are specified relative to the current position.
    """
    
    def __init__(self, reader: io.BufferedReader, buffer_size: int = 8 * 4096):
        """
        Initialize a CountedReader.
        
        Args:
            reader: The underlying buffered reader
            buffer_size: Size of the read buffer (default: 32KB)
        """
        self.pos = 0
        self._reader = reader
        
    def peek(self, n: int) -> bytes:
        """
        Peek at the next n bytes without consuming them.
        
        Args:
            n: Number of bytes to peek
            
        Returns:
            Bytes peeked (may be less than n if EOF)
        """
        return self._reader.peek(n)[:n]
    
    def discard(self, n: int) -> int:
        """
        Discard n bytes from the buffer.
        
        Args:
            n: Number of bytes to discard
            
        Returns:
            Number of bytes actually discarded
        """
        discarded = len(self._reader.read(n))
        self.pos += discarded
        return discarded
    
    def read_byte(self) -> int:
        """
        Read a single byte.
        
        Returns:
            The byte value (0-255)
            
        Raises:
            EOFError: If at end of file
        """
        b = self._reader.read(1)
        if not b:
            raise EOFError("Unexpected end of file")
        self.pos += 1
        return b[0]
    
    def read(self, n: int) -> bytes:
        """
        Read exactly n bytes.
        
        Args:
            n: Number of bytes to read
            
        Returns:
            Bytes read
            
        Raises:
            EOFError: If unable to read n bytes
        """
        data = self._reader.read(n)
        if len(data) != n:
            raise EOFError(f"Expected {n} bytes, got {len(data)}")
        self.pos += n
        return data
