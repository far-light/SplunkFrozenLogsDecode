# Deployment Package for Personal GitHub

This folder contains a clean, sanitized version of the Splunk decoder ready for upload to your personal GitHub repository.

## What's Included

```
deploy/
├── splunk_frozen_logs_export/   # Core library
│   ├── __init__.py
│   ├── journal.py
│   ├── decoder.py
│   ├── event.py
│   ├── opcode.py
│   ├── reader.py
│   ├── varint.py
│   └── gcs.py
├── export_logs.py               # Main script
├── requirements.txt             # Dependencies
├── README.md                    # Documentation
├── DEPLOYMENT.md                # GCP deployment guide
└── THIS_README.md               # This file
```

## What's Excluded

- ❌ Test data (`test_data/`)
- ❌ Git history (`.git/`)
- ❌ Work artifacts (`.gemini/`, task files)
- ❌ Local development files (`__pycache__/`, `.pytest_cache/`)
- ❌ Deployment scripts for EPAM account

## Upload to Your Personal GitHub

```bash
# Navigate to deploy folder
cd deploy/

# Initialize new git repo
git init
git add .
git commit -m "Initial commit: Splunk frozen logs decoder"

# Add your personal GitHub repo as remote
git remote add origin https://github.com/YOUR-USERNAME/splunk-decoder.git

# Push to GitHub
git push -u origin main
```

## Deploy to GCP from GitHub

Follow instructions in `DEPLOYMENT.md` - Step 6 will connect this GitHub repo to Cloud Run.

## Cost Estimate for Testing

- **Initial deployment**: ~$0.01
- **Storage (2 MB test)**: ~$0.00
- **Total**: < $0.50

Your $300 free credits are safe! 🎉
