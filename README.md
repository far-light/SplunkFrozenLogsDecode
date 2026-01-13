# Splunk Frozen Logs Export

**On-demand decoder for Splunk frozen logs stored in Google Cloud Storage.**

Extract and analyze archived Splunk data by converting compressed `.zst` journals to human-readable JSONL format.

## Use Case

When Splunk archives data to "frozen" buckets in GCS, the logs are stored in a proprietary compressed binary format. This tool:
1.  Decodes those journals back to readable log events.
2.  Outputs to GCS as JSONL for download or further processing.
3.  Optionally loads to BigQuery for SQL-based investigation.

**Typical Workflow**: Investigate a security incident → Identify relevant frozen bucket → Decode → Analyze in BigQuery.

---

## Features

✅ **Decode Splunk journal files** - Supports both `.zst` compressed and uncompressed formats  
✅ **GCS Integration** - Process journals directly from Cloud Storage buckets  
✅ **JSONL Output** - Industry-standard format for log analysis  
✅ **BigQuery Ready** - Optional direct loading for SQL queries  
✅ **Flexible Execution** - Run locally or deploy to Cloud Run for faster processing

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure GCP Credentials
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### 3. Decode Logs to JSONL
```bash
# Decode a frozen bucket to temporary GCS storage
python3 export_logs.py gs://my-bucket/frozen/db_2024_01 \
  --output-bucket gs://temp-decoded \
  --output-prefix investigation-jan-2024/

# Result: JSONL files written to gs://temp-decoded/investigation-jan-2024/*.jsonl
```

### 4. Optional: Load to BigQuery
```bash
# Decode and load directly to BigQuery for SQL analysis
python3 export_logs.py gs://my-bucket/frozen/db_2024_01 \
  --bq-table my-project.splunk_logs.january_investigation

# Result: Data available for querying immediately
```

---

## GCP Prerequisites & Setup

### 1. Enable Required APIs
```bash
gcloud services enable storage.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable run.googleapis.com  # Optional: if using Cloud Run
```

### 2. Create Service Account
```bash
# Create service account
gcloud iam service-accounts create splunk-decoder \
  --display-name="Splunk Frozen Logs Decoder"

# Grant Storage permissions (read source, write output)
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:splunk-decoder@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:splunk-decoder@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Grant BigQuery permissions (optional, if loading to BQ)
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:splunk-decoder@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:splunk-decoder@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

# Download key for local use
gcloud iam service-accounts keys create ~/splunk-decoder-key.json \
  --iam-account=splunk-decoder@PROJECT_ID.iam.gserviceaccount.com
```

### 3. Create Output Bucket
```bash
# Create bucket for temporary JSONL output
gsutil mb -l us-central1 gs://PROJECT_ID-splunk-decoded

# Set lifecycle rule to auto-delete after 1 day
cat > lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [{
      "action": {"type": "Delete"},
      "condition": {"age": 1}
    }]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://PROJECT_ID-splunk-decoded
```

### 4. Create BigQuery Dataset (Optional)
```bash
bq mk --dataset --location=us-central1 PROJECT_ID:splunk_logs

# Enable physical storage billing (saves ~66% on costs)
bq update --physical_storage_billing PROJECT_ID:splunk_logs

# Optional: Set default table expiration (90 days)
bq update --default_table_expiration 7776000 PROJECT_ID:splunk_logs
```

### 5. Authenticate Locally
```bash
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/splunk-decoder-key.json"
```

---

## Command-Line Options

| Option | Description |
|--------|-------------|
| `source` | Source GCS path (e.g., `gs://bucket/frozen/db_*/`) |
| `--bq-table` | Target BigQuery table (e.g., `project.dataset.table`) |
| `--output-bucket` | Target GCS bucket for JSONL output |
| `--output-prefix` | Prefix for output files (default: `decoded/`) |
| `--project` | GCP Project ID (optional, auto-detected if not provided) |
| `-v, --verbose` | Enable verbose logging |

---

## GCS Bucket Structure

Expected structure for frozen Splunk logs in GCS:

```
gs://your-bucket/
└── frozen/
    └── db/
        ├── bucket_1234567890_1234567890_0/
        │   └── rawdata/
        │       └── journal.zst
        ├── bucket_1234567891_1234567891_1/
        │   └── rawdata/
        │       └── journal.zst
        └── ...
```

The tool automatically searches for `journal.zst` (compressed) or `journal` (uncompressed) files within the specified path.

---

## JSON Event Structure

Each decoded event contains:

```json
{
  "host": "host::server1",
  "source": "source::/var/log/app.log",
  "sourcetype": "sourcetype::app_log",
  "index_time": 1234567890,
  "message": "Log message content",
  "stream_id": 12345,
  "stream_offset": 0
}
```

---

## Performance Expectations

### Processing Speed
**Single Cloud Run Instance (1 vCPU):**
*   **Throughput**: ~38,400 events/second (~6.7 MB/s compressed input)
*   **Decompression Ratio**: ~5x expansion (1 TB → 5 TB JSONL)

### Estimated Processing Time
| Job Size | Single Instance | 10 Instances (If Urgent) |
|----------|----------------|--------------------------|
| 100 GB | ~4 hours | ~25 minutes |
| 1 TB | ~42 hours | ~4.2 hours |
| 5 TB | ~9 days | ~21 hours |

**Note**: Costs remain the same regardless of instance count (~$4.33 per TB). Use more instances if results are needed urgently.

---

## Cost Analysis

### Cost Per 1 TB Job

| Component | Economy (Batch Load) | Speed (Direct Streaming) |
|-----------|---------------------|--------------------------|
| **Compute** | ~$4.33 | ~$4.33 |
| **Temp Storage** | ~$3.33 (1 day retention) | $0 (bypassed) |
| **Ingestion** | **$0** (Batch Load) | ~$75 (Storage Write API) |
| **Total (One-Time)** | **~$7.66** | **~$79.33** |

**Monthly Storage (If Retained in BQ):**
*   **Physical Billing** (Recommended): **~$34/month** per TB of original compressed data.
*   **Logical Billing**: ~$100/month per TB (not recommended).

### Cost Optimization Recommendations
1.  **Use Economy Mode** (Batch Load) for all jobs. Saves $75/TB on ingestion.
2.  **Set GCS Lifecycle Rules**: Auto-delete temp JSONL files after 1 day.
3.  **Enable Physical Storage Billing** in BigQuery dataset settings.
4.  **Use Partitioned Tables**: Set table expiration (e.g., 90 days) for investigations.

### Example: Typical Investigation (500 GB)
*   **One-Time Processing**: 500 GB × $7.66 = **~$3.83**
*   **Monthly Storage** (if retained in BQ): **~$17/month**

**Note**: Most investigations are temporary. Delete BQ tables after analysis to avoid ongoing storage costs.

---

## Test Results

### Validation Test

**Test Command:**
```bash
python3 tests/test_all_journals.py
```

**Test Dataset**: 7 frozen buckets, 2.2 MB compressed input.

**Results:**
```
✅ Successfully decoded 12,809 events in 0.33 seconds

Throughput:
  Events/Second: ~38,400 EPS
  Data Rate: ~6.7 MB/s (compressed input)

Events by Host:
  host::e29271725e94: 12,809 events

Events by Sourcetype:
  sourcetype::test_log: 8,310 events
  sourcetype::xmlwindowseventlog: 4,499 events

Output Size: 11.3 MB JSONL
Expansion Ratio: 5.16x
```

### Sample Input → Output

**Input**: Binary compressed journal file (`journal.zst`)
```
00000000: 28b5 2ffd 2001 5d05 0080 0102 0308 3138  (./. .].......18
00000010: 3731 3333 3838 3939 0205 0332 3433 3506  71338899...24356
00000020: 0f2f 7661 722f 6c6f 672f 6170 702e 6c6f  ./var/log/app.lo
...
```

**Output**: Human-readable JSONL
```json
{"host":"host::server1","source":"source::/var/log/app.log","sourcetype":"sourcetype::access_log","index_time":1234567890,"message":"192.168.1.1 - - [01/Jan/2024:12:00:00 +0000] \"GET /api/status HTTP/1.1\" 200 1234","stream_id":12345,"stream_offset":0}
{"host":"host::server1","source":"source::/var/log/app.log","sourcetype":"sourcetype::access_log","index_time":1234567891,"message":"192.168.1.2 - - [01/Jan/2024:12:00:01 +0000] \"POST /api/data HTTP/1.1\" 201 567","stream_id":12345,"stream_offset":1}
```

### What the Tool Does

1.  **Finds** all `journal.zst` files in the specified GCS bucket path
2.  **Decompresses** each journal using zstandard
3.  **Parses** the proprietary Splunk binary format (opcodes, metadata, events)
4.  **Extracts** individual log events with their timestamps and metadata
5.  **Outputs** to industry-standard JSONL format for analysis

**Validation**: The decoder handles partial/corrupted journals gracefully by skipping them and continuing processing.

---

## Decoding Internals

How the tool processes Splunk journal files:

### 1. Decompression
Splunk stores frozen buckets in `zstandard` compressed blocks. The `JournalDecoder` initializes a `zstd.ZstdDecompressor` stream to read `journal.zst` files incrementally, handling large files without loading them entirely into memory.

### 2. Opcode Stream Parsing
The decoded stream is processed byte-by-byte as a sequence of **Opcodes**. The decoder maintains a **State Machine** (`DecoderState`) that tracks context across the stream.

| Opcode Range | Type | Purpose |
|--------------|------|---------||
| `0x00` | NOP | Skipped |
| `0x03` - `0x06` | New String | Defines a new Host, Source, or Sourcetype string and adds it to the state dictionary |
| `0x11` - `0x1F` | State Change | Updates the *Active* Host/Source/Sourcetype index or Base Timestamp |
| `0x20` - `0x2B` | Event | Actual log event data |

### 3. Event Extraction
When an Event Opcode is encountered, the `EventDecoder` parses the following variable-length structure:
1.  **Message Length** (Varint)
2.  **Extended Headers** (Optional)
3.  **Stream ID & Offset** (Tracking original position)
4.  **Index Time Delta** (Varint) - Added to the current `base_time` state
5.  **Metadata** (Key-Value pairs)
6.  **Raw Message Bytes**

The decoder combines the raw message with the current **Active State** (Host, Source, Sourcetype) to produce a complete, enriched Splunk event.

---

## Requirements

- Python 3.8+
- `zstandard>=0.22.0` - For decompression
- `google-cloud-storage>=2.10.0` - For GCS integration
- `google-cloud-bigquery>=3.11.0` - For BigQuery streaming

---

