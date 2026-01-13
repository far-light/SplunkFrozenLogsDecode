# User Manual

Complete guide for using the Splunk Frozen Logs Decoder to decode and analyze Splunk frozen logs stored in Google Cloud Storage.

---

## Overview

The Splunk Frozen Logs Decoder converts Splunk's proprietary frozen log format (compressed journal files) into industry-standard JSONL format for analysis.

**Key Features:**
- Decodes compressed `.zst` journal files
- Outputs searchable JSONL format
- Processes logs directly from GCS buckets
- Runs on-demand via Cloud Run Jobs
- Minimal cost execution model

---

## Quick Start

### Basic Workflow

1. **Identify frozen logs** in GCS bucket (e.g., `gs://frozen-logs/db_2024_01/`)
2. **Execute decoder job** pointing to frozen bucket
3. **Download decoded JSONL** from output bucket
4. **Analyze logs** using standard tools (jq, grep, BigQuery, etc.)

---

## Usage Methods

Choose based on your preference:
- **Method 1**: gcloud CLI (automation-friendly)
- **Method 2**: GCP Console UI (visual workflow)

---

## Method 1: Using gcloud CLI

### Prerequisites

Install and authenticate gcloud:
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Execute Decoder Job

**Basic usage:**
```bash
gcloud run jobs execute splunk-decoder \
  --args="gs://FROZEN_BUCKET/path,--output-bucket,gs://OUTPUT_BUCKET" \
  --region=REGION \
  --wait
```

**With custom output prefix:**
```bash
gcloud run jobs execute splunk-decoder \
  --args="gs://frozen-logs/db_2024_01,--output-bucket,gs://decoded-logs,--output-prefix,investigation/jan/" \
  --region=us-central1 \
  --wait
```

### Monitor Execution

**Watch job status:**
```bash
# Job completes automatically with --wait flag
# Without --wait, check status:
gcloud run jobs executions list --region=REGION
```

**View logs in real-time:**
```bash
gcloud logging tail "resource.type=cloud_run_job AND resource.labels.job_name=splunk-decoder"
```

**View completed execution logs:**
```bash
gcloud logging read "resource.type=cloud_run_job" \
  --limit=100 \
  --format="value(textPayload,jsonPayload.message)"
```

### Retrieve Output

**List decoded files:**
```bash
gsutil ls gs://OUTPUT_BUCKET/decoded/
```

**Download all files:**
```bash
gsutil -m cp gs://OUTPUT_BUCKET/decoded/*.jsonl ./decoded/
```

**Download specific file:**
```bash
gsutil cp gs://OUTPUT_BUCKET/decoded/db_2024_01.jsonl ./
```

**Preview events:**
```bash
gsutil cat gs://OUTPUT_BUCKET/decoded/db_2024_01.jsonl | head -5 | jq .
```

### Analyze Output

**Count events:**
```bash
wc -l decoded/*.jsonl
```

**Search for specific host:**
```bash
cat decoded/*.jsonl | jq 'select(.host | contains("server01"))'
```

**Extract field:**
```bash
cat decoded/*.jsonl | jq -r '.message' | grep "ERROR"
```

**Filter by time:**
```bash
cat decoded/*.jsonl | jq 'select(.index_time > 1704067200)'
```

---

## Method 2: Using GCP Console UI

### Step 1: Navigate to Cloud Run Jobs

1. Open GCP Console
2. Go to: **Cloud Run** → **Jobs**
3. Find job: `splunk-decoder`
4. Click on job name

### Step 2: Execute Job

1. Click **EXECUTE** button (top right)
2. **Container arguments** field (single line, space-separated):
   ```
   gs://your-frozen-bucket/path/to/frozen --output-bucket gs://your-output-bucket
   ```

**With custom output prefix:**
```
gs://your-frozen-bucket/path/to/frozen --output-bucket gs://your-output-bucket --output-prefix investigation/jan/
```

**Example:**
```
gs://frozen-logs/db_2024_01 --output-bucket gs://decoded-logs --output-prefix investigation/jan/
```

3. Click **EXECUTE**

### Step 3: Monitor Execution

**View status:**
- Execution starts immediately
- Status shows in **EXECUTIONS** tab:
  - 🔵 Running
  - ✅ Succeeded
  - ❌ Failed

**View logs:**
1. Click on execution name
2. Go to **LOGS** tab
3. See real-time progress:
   ```
   INFO - Processing bucket: gs://frozen-logs/db_2024_01
   INFO - Found 15 journal files
   INFO - Decoded 125,430 events
   INFO - Performance: 1,250 events/sec
   ```

### Step 4: Retrieve Output via Console

1. Go to: **Cloud Storage** → **Buckets**
2. Click on output bucket (e.g., `decoded-logs`)
3. Navigate to `decoded/` folder
4. See generated JSONL files:
   - `db_2024_01_bucket_0.jsonl`
   - `db_2024_01_bucket_1.jsonl`
   - etc.

**Download files:**
- Select file → **Download**
- Or click **⋮** → **Download**

**Preview events:**
- Click on file
- Click **Download** or view in browser

### Step 5: Analyze Output

**Using Cloud Shell:**
1. Click **Activate Cloud Shell** (top right)
2. Download file:
   ```bash
   gsutil cp gs://decoded-logs/decoded/*.jsonl ./
   ```
3. Analyze:
   ```bash
   cat *.jsonl | jq . | less
   ```

**Using BigQuery:**
1. Create dataset
2. Load JSONL files:
   - Go to **BigQuery** → **Create Table**
   - Source: Google Cloud Storage
   - File: `gs://decoded-logs/decoded/*.jsonl`
   - Format: JSONL
   - Schema: Auto-detect
3. Query with SQL:
   ```sql
   SELECT host, COUNT(*) as events
   FROM `dataset.table`
   WHERE index_time > 1704067200
   GROUP BY host
   ```

---

## Command-Line Options

| Option | Required | Description | Example |
|--------|----------|-------------|---------|
| `source` | Yes | GCS path to frozen logs | `gs://bucket/frozen/db` |
| `--output-bucket` | Yes | GCS bucket for JSONL output | `gs://output-bucket` |
| `--output-prefix` | No | Prefix for output files (default: `decoded/`) | `investigation/jan/` |
| `--project` | No | GCP Project ID (auto-detected if omitted) | `my-project-123` |
| `--verbose` | No | Enable debug logging | `-v` or `--verbose` |

---

## Output Format

### JSONL Structure

Each line is a JSON object with Splunk event fields:

```json
{
  "host": "host::server01",
  "source": "source::/var/log/syslog",
  "sourcetype": "sourcetype::syslog",
  "index_time": 1704067200,
  "message": "Jan 01 00:00:00 server01 kernel: [12345.678] ...",
  "stream_id": 1234567890,
  "stream_offset": 0
}
```

### Field Descriptions

- `host`: Splunk host field
- `source`: Log source file path
- `sourcetype`: Splunk sourcetype
- `index_time`: Unix timestamp when indexed
- `message`: Raw log message content
- `stream_id`: Internal Splunk stream identifier
- `stream_offset`: Position in stream

---

## Common Use Cases

### Security Investigation

**Scenario**: Analyze security events from January 2024

```bash
# Execute decoder
gcloud run jobs execute splunk-decoder \
  --args="gs://frozen-logs/security_jan_2024,--output-bucket,gs://investigations" \
  --region=us-central1 --wait

# Download and search for failed logins
gsutil cp gs://investigations/decoded/*.jsonl ./
cat *.jsonl | jq 'select(.message | contains("Failed password"))'
```

### Audit Log Review

**Scenario**: Extract admin actions for compliance

```bash
# Decode audit logs
gcloud run jobs execute splunk-decoder \
  --args="gs://frozen-logs/audit_2024,--output-bucket,gs://compliance,--output-prefix,audit/" \
  --region=us-central1 --wait

# Filter admin activity
gsutil cat gs://compliance/audit/*.jsonl | \
  jq 'select(.sourcetype == "sourcetype::audit" and .message | contains("admin"))'
```

### Application Debugging

**Scenario**: Debug production errors from last week

```bash
# Decode application logs
gcloud run jobs execute splunk-decoder \
  --args="gs://frozen-logs/app_errors_2024_w52,--output-bucket,gs://debug" \
  --region=us-central1 --wait

# Extract error stack traces
gsutil cat gs://debug/decoded/*.jsonl | \
  jq -r 'select(.message | contains("ERROR")) | .message'
```

---

## Performance & Costs

### Typical Performance

- **Small jobs** (1-10 GB frozen): 1-2 minutes, ~$0.01
- **Medium jobs** (100 GB frozen): 5-10 minutes, ~$0.05
- **Large jobs** (1 TB frozen): 30-60 minutes, ~$0.50

**Throughput**: ~1,000-2,000 events/sec (512 MiB container)

### Cost Breakdown

| Component | Cost | Notes |
|-----------|------|-------|
| Cloud Run execution | $0.00002400/vCPU-second | 1 vCPU @ 512 MiB |
| Cloud Storage (read) | Included | Archive retrieval free |
| Cloud Storage (write) | $0.020/GB | Standard storage |
| Data egress | $0.00 | Intra-region |

**Example**: 500 GB frozen → 15 GB JSONL:
- Execution: ~$0.02 (2 minutes)
- Storage: ~$0.30 (15 GB)
- **Total**: ~$0.32

---

## Troubleshooting

### Job Fails Immediately

**Check logs:**
```bash
gcloud logging read "resource.type=cloud_run_job AND severity>=ERROR" --limit=20
```

**Common causes:**
- Invalid GCS path
- Missing permissions
- Bucket in different region

### No Output Files

**Verify bucket permissions:**
```bash
gsutil ls gs://output-bucket/decoded/
```

**Check service account has Storage Object Admin role**

### Slow Performance

**Increase resources (up to 4 vCPU):**
```bash
gcloud run jobs update splunk-decoder \
  --memory=2Gi \
  --cpu=2 \
  --region=REGION
```

### Incomplete Output

**Check job timeout:**
```bash
gcloud run jobs update splunk-decoder \
  --task-timeout=1800 \
  --region=REGION
```

---

## Best Practices

### Organization

- Use descriptive output prefixes:
  ```
  --output-prefix incident-2024-01/
  --output-prefix compliance/audit-q4/
  ```

### Efficiency

- Process one frozen bucket at a time
- Delete output files after analysis
- Use Archive storage for frozen logs

### Security

- Use dedicated service account (least privilege)
- Store sensitive output in restricted buckets
- Enable audit logging for job executions

---

## Advanced Usage

### Batch Processing Script

```bash
#!/bin/bash
# Process multiple frozen buckets

FROZEN_BASE="gs://frozen-logs"
OUTPUT_BASE="gs://decoded-logs"

for bucket in $(gsutil ls ${FROZEN_BASE}/ | grep "db_2024"); do
  bucket_name=$(basename $bucket)
  echo "Processing $bucket_name..."
  
  gcloud run jobs execute splunk-decoder \
    --args="${bucket},--output-bucket,${OUTPUT_BASE},--output-prefix,${bucket_name}/" \
    --region=us-central1 \
    --wait
done
```

### Load into BigQuery

```bash
# Decode logs
gcloud run jobs execute splunk-decoder \
  --args="gs://frozen-logs/db,--output-bucket,gs://temp-output" \
  --region=us-central1 --wait

# Load to BigQuery
bq load --source_format=NEWLINE_DELIMITED_JSON \
  my_dataset.splunk_events \
  gs://temp-output/decoded/*.jsonl
```

---

## Support & Resources

- **GitHub**: https://github.com/far-light/SplunkFrozenLogsDecode
- **Issues**: Report bugs via GitHub Issues
- **Documentation**: See README.md for technical details
