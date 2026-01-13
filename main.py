#!/usr/bin/env python3
"""
Splunk Frozen Logs Export Tool

Single-script utility to batch process Splunk journal files from Google Cloud Storage
and export them to BigQuery or destination GCS buckets.

Usage:
    export_logs.py <bucket> [options]

Examples:
    # Process all journals in a bucket and save as JSONL to another bucket
    python3 export_logs.py gs://splunk-logs/frozen --output-bucket gs://decoded-logs

    # Process and stream to BigQuery (Table schema auto-detected)
    python3 export_logs.py gs://splunk-logs/frozen --bq-table my-project.dataset.table
"""

import argparse
import logging
import sys
import re
from pathlib import Path
from urllib.parse import urlparse

# Ensure we can import our library
sys.path.insert(0, str(Path(__file__).parent))

from splunk_frozen_logs_export.gcs import GCSJournalReader

def parse_gcs_path(path: str) -> tuple[str, str]:
    """Parse gs://bucket/prefix path into (bucket, prefix)."""
    if not path.startswith("gs://"):
        # Assume it's just a bucket name if no protocol
        if "/" in path:
            parts = path.split("/", 1)
            return parts[0], parts[1]
        return path, ""
    
    parsed = urlparse(path)
    return parsed.netloc, parsed.path.lstrip("/")

def configure_logging(verbose: bool = False):
    """Set up logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Silence chatty libraries
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def main():
    parser = argparse.ArgumentParser(
        description="Export frozen Splunk logs from GCS to BigQuery or JSONL"
    )
    parser.add_argument(
        "source", 
        help="Source GCS path (e.g., gs://bucket/frozen/)"
    )
    parser.add_argument(
        "--output-bucket",
        help="Target GCS bucket for JSONL output"
    )
    parser.add_argument(
        "--output-prefix",
        default="decoded/",
        help="Prefix for output JSONL files (default: decoded/)"
    )
    parser.add_argument(
        "--project",
        help="GCP Project ID (optional, defaults to environment)"
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Print events to stdout instead of writing to GCS/BigQuery (for debugging)"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )

    args = parser.parse_args()
    configure_logging(args.verbose)
    logger = logging.getLogger("export_logs")

    # Parse source path
    source_bucket, source_prefix = parse_gcs_path(args.source)
    
    logger.info(f"Source: gs://{source_bucket}/{source_prefix}")
    
    # Determine output destination
    if args.output_bucket:
        dest_bucket, dest_prefix = parse_gcs_path(args.output_bucket)
        # Verify output bucket doesn't contain scheme
        if args.output_bucket.startswith("gs://"):
             dest_bucket = parse_gcs_path(args.output_bucket)[0]
        else:
             dest_bucket = args.output_bucket
             
        logger.info(f"Destination: gs://{dest_bucket}/{args.output_prefix}")
    else:
        # Default to same bucket if no output specified
        dest_bucket = source_bucket
        logger.info(f"Destination: gs://{dest_bucket}/{args.output_prefix}")

    import time
    start_time = time.time()
    
    try:
        reader = GCSJournalReader(project_id=args.project)
        

        total_events = reader.process_bucket(
            bucket_name=source_bucket,
            prefix=source_prefix,
            output_format="console" if args.console else "jsonl",
            output_bucket=dest_bucket,
            output_prefix=args.output_prefix
        )
        
        end_time = time.time()
        duration_seconds = end_time - start_time
        eps = total_events / duration_seconds if duration_seconds > 0 else 0
        
        logger.info("-" * 40)
        logger.info(f"PERFORMANCE REPORT")
        logger.info("-" * 40)
        logger.info(f"Total Events  : {total_events:,}")
        logger.info(f"Total Time    : {duration_seconds:.2f} seconds")
        logger.info(f"Processing EPS: {eps:,.2f} events/sec")
        logger.info("-" * 40)
    
    except Exception as e:
        logger.error(f"Job Failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
