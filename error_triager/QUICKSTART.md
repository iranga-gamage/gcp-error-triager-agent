# Quick Start Guide

Get started with GCP Error Triager in 5 minutes!

## 1. Install Dependencies

```bash
# Make sure you're in the error_trager directory
cd error_trager

# Install with uv
uv pip install -e .
```

## 2. Authenticate with GCP

```bash
# Login with your Google account
gcloud auth application-default login

# Or set service account credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

## 3. Run Your First Query

Replace `YOUR_PROJECT_ID` with your actual GCP project ID:

```bash
gcp-triage --project YOUR_PROJECT_ID
```

This will query the last 24 hours of errors and show you:
- Total error count
- Error types breakdown
- Similar error groups
- Recent error timeline
- Suggested next steps

## 4. Try More Examples

### See detailed error information
```bash
gcp-triage --project YOUR_PROJECT_ID --detailed
```

### Query Cloud Run errors
```bash
gcp-triage --project YOUR_PROJECT_ID --resource-type cloud_run_revision --hours 6
```

### Search for specific errors
```bash
gcp-triage --project YOUR_PROJECT_ID --search "timeout"
```

### Get help
```bash
gcp-triage --help
```

## 5. Test with Error Simulator

If you have the error simulator deployed:

```bash
# Generate a test error
curl -X POST "https://your-cloud-run-url.run.app/api/v1/analytics?error_type=CALCULATION_ERROR"

# Triage it immediately
gcp-triage --project YOUR_PROJECT_ID --hours 1 --detailed
```

## Common Issues

### "Permission denied" error
Make sure your account has the `roles/logging.viewer` IAM role:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/logging.viewer"
```

### "No logs found"
- Check that your project ID is correct
- Verify logs exist in Cloud Logging console
- Try increasing the time range: `--hours 48`
- Check the resource type filter

### Module import errors
Make sure you installed the package:
```bash
uv pip install -e .
```

## What's Next?

- Read the full [README.md](README.md) for all features
- Check out [example_usage.py](example_usage.py) for programmatic usage
- Set up monitoring alerts based on error patterns
- Integrate with your incident response workflow

## Support

For issues or questions, check the main README or open an issue in the repository.
