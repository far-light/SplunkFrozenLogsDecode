# Deployment Guide

This guide covers deploying the Splunk Frozen Logs Decoder to Google Cloud Run Jobs using either the **gcloud CLI** or the **GCP Console UI**.

---

## Prerequisites

- GCP project with billing enabled
- Required APIs enabled:
  - Cloud Run API
  - Cloud Storage API
  - Cloud Build API
- Service account with permissions:
  - `Storage Object Viewer` (read frozen logs)
  - `Storage Object Admin` (write decoded output)

---

## Method 1: Deploy via gcloud CLI

### 1. Install gcloud SDK

```bash
# macOS (Homebrew)
brew install --cask google-cloud-sdk

# Other platforms: https://cloud.google.com/sdk/docs/install
```

### 2. Authenticate and Set Project

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 3. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create splunk-decoder \
  --display-name="Splunk Decoder Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:splunk-decoder@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:splunk-decoder@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### 4. Create Artifact Registry Repository

Artifact Registry stores the Docker container images built from your source code.

```bash
# Create Docker repository for container images
gcloud artifacts repositories create cloud-run-source-deploy \
  --repository-format=docker \
  --location=REGION \
  --description="Container images for Cloud Run deployments"
```

**Repository details:**
- **Name**: `cloud-run-source-deploy` (standard name for Cloud Run source deployments)
- **Format**: Docker
- **Location**: Must match your Cloud Run region
- **Purpose**: Stores built container images (~100-200 MB per image)

**Verify creation:**
```bash
gcloud artifacts repositories list --location=REGION
```

### 5. Create Storage Buckets

```bash
# Source bucket (Archive storage for frozen logs)
gsutil mb -c ARCHIVE -l REGION gs://YOUR-FROZEN-BUCKET

# Output bucket (Standard storage for decoded JSONL)
gsutil mb -l REGION gs://YOUR-OUTPUT-BUCKET
```

### 6. Deploy Cloud Run Job from GitHub

```bash
# Clone repository locally
git clone https://github.com/far-light/SplunkFrozenLogsDecode.git
cd SplunkFrozenLogsDecode

# Deploy to Cloud Run Jobs
gcloud run jobs deploy splunk-decoder \
  --region=REGION \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=0 \
  --task-timeout=300 \
  --service-account=splunk-decoder@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --source=.
```

**Build time**: First build takes ~2-3 minutes. Subsequent builds are faster due to layer caching.

### 7. Execute Job

```bash
gcloud run jobs execute splunk-decoder \
  --args="gs://YOUR-FROZEN-BUCKET/path/to/frozen,--output-bucket,gs://YOUR-OUTPUT-BUCKET" \
  --region=REGION \
  --wait
```

---

## Method 2: Deploy via GCP Console UI

### 1. Enable APIs

1. Go to: **APIs & Services** → **Library**
2. Search and enable:
   - Cloud Run API
   - Cloud Storage API
   - Cloud Build API

### 2. Create Service Account

1. Go to: **IAM & Admin** → **Service Accounts**
2. Click **CREATE SERVICE ACCOUNT**
   - Name: `splunk-decoder`
   - Description: `Service account for Splunk decoder`
3. Click **CREATE AND CONTINUE**
4. Add roles:
   - `Storage Object Viewer`
   - `Storage Object Admin`
5. Click **DONE**

### 3. Create Artifact Registry Repository

Artifact Registry stores Docker container images built during deployment.

1. Go to: **Artifact Registry** → **Repositories**
2. Click **CREATE REPOSITORY**
3. Configure repository:
   - **Name**: `cloud-run-source-deploy`
   - **Format**: **Docker**
   - **Mode**: **Standard**
   - **Location type**: **Region**
   - **Region**: Same as your Cloud Run jobs (e.g., `us-central1`)
   - **Description**: `Container images for Cloud Run deployments`
4. Click **CREATE**

**Why needed:**
- Cloud Run builds Docker images from your source code
- Images are stored in Artifact Registry (~100-200 MB each)
- Required before deploying from source

### 4. Create Storage Buckets

**Source Bucket:**
1. Go to: **Cloud Storage** → **Buckets**
2. Click **CREATE BUCKET**
   - Name: `your-frozen-bucket`
   - Location: Choose region (e.g., `us-central1`)
   - Storage class: **Archive**
3. Click **CREATE**

**Output Bucket:**
4. Click **CREATE BUCKET** again
   - Name: `your-output-bucket`
   - Location: Same region as source
   - Storage class: **Standard**
5. Click **CREATE**

### 5. Deploy Cloud Run Job

1. Go to: **Cloud Run** → **Jobs**
2. Click **CREATE JOB**
3. **Container configuration:**
   - Container image URL: Leave blank for now
   - Click **Deploy from source repository**

4. **Source repository:**
   - Repository provider: **GitHub**
   - Click **Set up with Cloud Build**
   - Authorize GitHub access
   - Select repository: `far-light/SplunkFrozenLogsDecode`
   - Branch: `main`
   - Build type: **Dockerfile**

5. **Job settings:**
   - Job name: `splunk-decoder`
   - Region: Same as buckets (e.g., `us-central1`)

6. **Service account:**
   - Under **Security** → **Service account**
   - Select: `splunk-decoder@YOUR_PROJECT_ID.iam.gserviceaccount.com`

7. **Resources:**
   - Memory: `512 MiB`
   - CPU: `1`
   - Task timeout: `300 seconds`
   - Max retries: `0`

8. Click **CREATE**

**Build process:**
- Container image builds from source (~2-3 minutes)
- Image stored in Artifact Registry repository
- Subsequent deployments faster (layer caching)

### 6. Execute Job via Console

1. Go to your job: **Cloud Run** → **Jobs** → `splunk-decoder`
2. Click **EXECUTE**
3. **Container arguments** (single line, space-separated):
   ```
   gs://your-frozen-bucket/path/to/frozen --output-bucket gs://your-output-bucket
   ```
4. Click **EXECUTE**
5. Monitor execution in **EXECUTIONS** tab
6. View logs in **LOGS** tab

---

## Verification

### Check Output Files

**CLI:**
```bash
gsutil ls -lh gs://your-output-bucket/decoded/
```

**Console:**
- Go to: **Cloud Storage** → `your-output-bucket` → `decoded/`
- Verify JSONL files exist

### Download Sample

```bash
gsutil cp gs://your-output-bucket/decoded/FILENAME.jsonl ./
head FILENAME.jsonl
```

---

## Cost Optimization

**For minimal cost usage:**
- Use **Archive** storage class for frozen logs (if not already)
- Use **Standard** storage class for output (temporary analysis)
- Execute jobs on-demand (not scheduled)
- Delete output files after analysis
- Use 512 MiB memory (lowest tier)

**Typical costs per execution:**
- Cloud Run: $0.01-0.02 per job (512 MiB, 1-2 minutes)
- Cloud Build: $0.01-0.03 per build (first deployment only)
- Storage: Minimal for temporary output

---

## Troubleshooting

### Build Fails

**Check Cloud Build logs:**
```bash
gcloud builds list --limit=5
gcloud builds log BUILD_ID
```

### Job Execution Fails

**Check job logs:**
```bash
gcloud logging read "resource.type=cloud_run_job" --limit=50
```

**Console:** Jobs → Execution → LOGS tab

### Permission Errors

Verify service account has both:
- `Storage Object Viewer` (read source)
- `Storage Object Admin` (write output)

---

## Cleanup

### Delete Job
```bash
gcloud run jobs delete splunk-decoder --region=REGION
```

### Delete Buckets
```bash
gsutil -m rm -r gs://your-frozen-bucket
gsutil -m rm -r gs://your-output-bucket
```

### Delete Service Account
```bash
gcloud iam service-accounts delete splunk-decoder@YOUR_PROJECT_ID.iam.gserviceaccount.com
```
