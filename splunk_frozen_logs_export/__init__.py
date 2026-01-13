"""SplunkFrozenLogsExport - Tool for exporting frozen Splunk logs from GCS."""

from .journal import JournalDecoder
from .event import Event

# GCS integration (optional, requires google-cloud-storage)
try:
    from .gcs import GCSJournalReader, list_buckets_in_gcs
    from .bigquery import BigQueryStreamer
    __all__ = ['JournalDecoder', 'Event', 'GCSJournalReader', 'list_buckets_in_gcs', 'BigQueryStreamer']
except ImportError:
    __all__ = ['JournalDecoder', 'Event']

__version__ = "0.1.0"
