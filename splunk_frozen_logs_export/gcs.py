"""
GCS (Google Cloud Storage) integration for reading Splunk journal files.

This module provides utilities for:
- Listing journal files in GCS buckets
- Streaming journal files from GCS
- Batch processing multiple journals
"""

from google.cloud import storage
from typing import Iterator, List, Optional, Tuple
import io
import logging
from pathlib import Path

from .journal import JournalDecoder
from .event import Event

logger = logging.getLogger(__name__)


class GCSJournalReader:
    """Read and process Splunk journal files from Google Cloud Storage."""
    
    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize GCS client.
        
        Args:
            project_id: GCP project ID (optional, uses default credentials)
        """
        self.client = storage.Client(project=project_id)
        logger.info(f"Initialized GCS client for project: {project_id or 'default'}")
    
    def list_journal_files(self, bucket_name: str, prefix: str = "") -> List[Tuple[str, int]]:
        """
        List all journal files in a GCS bucket.
        
        Args:
            bucket_name: Name of the GCS bucket
            prefix: Optional prefix to filter files (e.g., "frozen/")
            
        Returns:
            List of tuples (blob_path, size_bytes)
        """
        bucket = self.client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        journal_files = []
        for blob in blobs:
            # Look for journal.zst or journal files
            if blob.name.endswith('journal.zst') or blob.name.endswith('/journal'):
                journal_files.append((blob.name, blob.size))
                logger.debug(f"Found journal: {blob.name} ({blob.size} bytes)")
        
        logger.info(f"Found {len(journal_files)} journal files in gs://{bucket_name}/{prefix}")
        return journal_files
    
    def open_journal_from_gcs(self, bucket_name: str, blob_path: str) -> JournalDecoder:
        """
        Open and decode a journal file from GCS.
        
        Args:
            bucket_name: Name of the GCS bucket
            blob_path: Path to the journal file in the bucket
            
        Returns:
            JournalDecoder instance ready for iteration
            
        Example:
            >>> reader = GCSJournalReader()
            >>> decoder = reader.open_journal_from_gcs("my-bucket", "frozen/db/bucket1/rawdata/journal.zst")
            >>> for event in decoder:
            ...     print(event.message_string())
        """
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        logger.info(f"Downloading journal from gs://{bucket_name}/{blob_path}")
        
        # Download to memory
        journal_data = blob.download_as_bytes()
        logger.info(f"Downloaded {len(journal_data)} bytes")
        
        # Create a file-like object
        journal_file = io.BytesIO(journal_data)
        
        # Determine if it's compressed based on file extension
        is_compressed = blob_path.endswith('.zst')
        
        # For now, save to temp file for JournalDecoder
        # TODO: Modify JournalDecoder to accept file-like objects
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zst' if is_compressed else '') as tmp:
            tmp.write(journal_data)
            tmp_path = tmp.name
        
        # Create a temporary bucket directory structure
        temp_bucket = Path(tmp_path).parent / "temp_bucket"
        temp_bucket.mkdir(exist_ok=True)
        rawdata_dir = temp_bucket / "rawdata"
        rawdata_dir.mkdir(exist_ok=True)
        
        # Move file to expected location
        final_path = rawdata_dir / ("journal.zst" if is_compressed else "journal")
        Path(tmp_path).rename(final_path)
        
        return JournalDecoder(str(temp_bucket))
    
    def process_bucket(
        self,
        bucket_name: str,
        prefix: str = "",
        output_format: str = "jsonl",
        output_bucket: Optional[str] = None,
        output_prefix: str = "decoded/"
    ) -> int:
        """
        Process all journal files in a GCS bucket.
        
        Args:
            bucket_name: Source bucket containing journal files
            prefix: Prefix to filter journal files
            output_format: Output format ("jsonl" or "json")
            output_bucket: Destination bucket for output (if None, uses source bucket)
            output_prefix: Prefix for output files
            
        Returns:
            Total number of events processed
        """
        journal_files = self.list_journal_files(bucket_name, prefix)
        total_events = 0
        
        output_bucket = output_bucket or bucket_name
        
        for blob_path, size in journal_files:
            logger.info(f"Processing {blob_path} ({size} bytes)")
            
            try:
                decoder = self.open_journal_from_gcs(bucket_name, blob_path)
                
                # Collect events
                events_from_journal = 0
                for event in decoder:
                    # Serialize event to dict
                    event_dict = {
                        "host": decoder.host,
                        "source": decoder.source,
                        "sourcetype": decoder.source_type,
                        "index_time": event.index_time,
                        "message": event.message_string(),
                        "stream_id": event.stream_id,
                        "stream_offset": event.stream_offset
                    }
                    
                    if output_format == "console":
                        # Print to stdout for Cloud Run Jobs debugging
                        print(json.dumps(event_dict))
                    elif output_format in ["jsonl", "json"]:
                        # Collect for batch writing to GCS
                        if 'events' not in locals():
                            events = []
                        events.append(event_dict)
                    
                    events_from_journal += 1
                
                total_events += events_from_journal
                logger.info(f"Decoded {events_from_journal} events from {blob_path}")
                
                # Write output for GCS formats
                if output_format in ["json", "jsonl"] and 'events' in locals() and events:
                    self._write_to_gcs(events, output_bucket, blob_path, output_prefix, output_format)
                
            except Exception as e:
                logger.error(f"Error processing {blob_path}: {e}")
                continue
        
        logger.info(f"Processed {len(journal_files)} journals, {total_events} total events")
        return total_events
    
    def _write_to_gcs(
        self,
        events: List[dict],
        bucket_name: str,
        source_path: str,
        output_prefix: str,
        output_format: str
    ):
        """Write events to GCS in specified format."""
        import json
        
        # Generate output path
        source_name = Path(source_path).parent.parent.name  # Get bucket directory name
        output_path = f"{output_prefix}{source_name}.{output_format}"
        
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(output_path)
        
        if output_format == "jsonl":
            # JSON Lines format
            output = "\n".join(json.dumps(event) for event in events)
        else:
            # JSON array format
            output = json.dumps(events, indent=2)
        
        blob.upload_from_string(output, content_type="application/json")
        logger.info(f"Wrote {len(events)} events to gs://{bucket_name}/{output_path}")


def list_buckets_in_gcs(bucket_name: str, prefix: str = "frozen/") -> List[str]:
    """
    List all Splunk bucket directories in GCS.
    
    Args:
        bucket_name: GCS bucket name
        prefix: Prefix where frozen buckets are stored
        
    Returns:
        List of bucket directory paths
    """
    reader = GCSJournalReader()
    bucket = reader.client.bucket(bucket_name)
    
    # List all blobs with the prefix
    blobs = bucket.list_blobs(prefix=prefix, delimiter='/')
    
    # Get unique bucket directories
    buckets = set()
    for blob in blobs:
        # Extract bucket directory from path like "frozen/db/bucket_name/rawdata/journal.zst"
        parts = blob.name.split('/')
        if len(parts) >= 3:
            bucket_dir = '/'.join(parts[:3])  # frozen/db/bucket_name
            buckets.add(bucket_dir)
    
    return sorted(list(buckets))
