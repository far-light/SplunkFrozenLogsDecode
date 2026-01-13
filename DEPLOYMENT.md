# Deployment Instructions (Without Cloud Shell)

## Prerequisites
- GCP Project with billing enabled
- Code pushed to GitHub repository (or use Cloud Source Repositories)
- Service account created (see below)

---

## Step 1: Push Code to GitHub

Since you can't use Cloud Shell, push your code to GitHub:

```bash
# From your local machine
git add .
git commit -m "Ready for deployment"
git push origin main
```

---

## Step 2: Create Service Account (GCP Console)

1. Go to [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click **"CREATE SERVICE ACCOUNT"**
3. Fill in:
   - **Name**: `splunk-decoder`
   - **Description**: `Service account for Splunk log decoder`
4. Click **"CREATE AND CONTINUE"**
5. Add roles:
   - Click **"SELECT A ROLE"**
   - Add: `Storage Object Viewer`
   - Click **"ADD ANOTHER ROLE"**
   - Add: `Storage Object Admin`
6. Click **"DONE"**

---

## Step 3: Enable Required APIs

1. Go to [APIs & Services](https://console.cloud.google.com/apis/dashboard)
2. Click **"+ ENABLE APIS AND SERVICES"**
3. Search and enable:
   - **Cloud Run API**
   - **Cloud Storage API**
   - **Cloud Build API**

---

## Step 4: Create Output Bucket (GCP Console)

1. Go to [Cloud Storage](https://console.cloud.google.com/storage/browser)
2. Click **"CREATE BUCKET"**
3. Configure:
   - **Name**: `YOUR-PROJECT-ID-splunk-decoded` (must be globally unique)
   - **Location**: `us-central1` (region)
   - **Storage class**: `Standard`
4. Click **"CREATE"**

### Set Lifecycle Rule (Auto-Delete After 1 Day)

1. Click on your bucket name
2. Go to **"LIFECYCLE"** tab
3. Click **"ADD A RULE"**
4. Configure:
   - **Action**: Select **"Delete object"**
   - Click **"CONTINUE"**
   - **Conditions**: Set **"Age"** to `1` day
   - Click **"CONTINUE"**
5. Click **"CREATE"**

---

## Step 5: Deploy Cloud Run Job (GCP Console)

1. Go to [Cloud Run Jobs](https://console.cloud.google.com/run/jobs)
2. Click **"CREATE JOB"**
3. Configure:

### Container Section
- **Deployment platform**: Cloud Run (fully managed)
- **Job name**: `splunk-decoder`
- **Region**: `us-central1`

### Container Settings
- Click **"Set up with Cloud Build"**
  - **Repository provider**: Select **"GitHub"**
  - Click **"CONNECT TO GITHUB"** and authorize
  - Select your repository
  - **Branch**: `main` (or your default branch)
  - **Build type**: Will auto-detect as **Python**
  - Click **"SAVE"**

### Resources Allocation
- **Memory**: `2 GiB`
- **CPU**: `1`
- **Maximum number of tasks**: `1`
- **Task timeout**: `3600` seconds (1 hour)

### Security
- **Service account**: Select `splunk-decoder@YOUR-PROJECT-ID.iam.gserviceaccount.com`

4. Click **"CREATE"**

**Wait**: The initial deployment will take 3-5 minutes while Cloud Build creates the container.

---

## Step 6: Execute the Job (GCP Console)

1. Go to your job: [Cloud Run Jobs > splunk-decoder](https://console.cloud.google.com/run/jobs)
2. Click **"EXECUTE"**
3. Under **"Container arguments override"**, enter:
   ```
   gs://YOUR-SOURCE-BUCKET/frozen/db
   --output-bucket
   gs://YOUR-PROJECT-ID-splunk-decoded
   --console
   ```
4. Click **"EXECUTE"**

---

## Step 7: View Results

### Option A: View Console Output (Debugging)
1. Click on the execution name
2. Go to **"LOGS"** tab
3. You'll see each decoded event printed as JSON

### Option B: Download JSONL Files
1. Go to [Cloud Storage](https://console.cloud.google.com/storage/browser)
2. Click on `YOUR-PROJECT-ID-splunk-decoded` bucket
3. Navigate to `decoded/` folder
4. Download `.jsonl` files

---

## Troubleshooting

### Error: "Permission Denied"
**Solution**: Add Storage permissions to service account
1. Go to [IAM & Admin](https://console.cloud.google.com/iam-admin/iam)
2. Find `splunk-decoder@...` service account
3. Click **Edit** (pencil icon)
4. Add roles: `Storage Object Viewer` and `Storage Object Admin`

### Error: "Cloud Build API not enabled"
**Solution**: Enable it at [APIs & Services](https://console.cloud.google.com/apis/library/cloudbuild.googleapis.com)

### Job Timeout
**Solution**: Increase timeout:
1. Go to job details
2. Click **"EDIT"**
3. Under **"Container"** > **"General"**, set **"Task timeout"** to higher value (max: 3600s)

---

## Cost Estimate

For a 1 TB job:
- **Cloud Run**: ~$4.33
- **Temp Storage**: ~$0.11 (with 1-day lifecycle rule)
- **Total**: ~$4.44

---

## Summary Commands (For Reference)

If you later gain Cloud Shell access, you can execute like this:
```bash
gcloud run jobs execute splunk-decoder \
  --args="gs://YOUR-BUCKET/frozen/db,--output-bucket,gs://output-bucket,--console" \
  --region us-central1
```
