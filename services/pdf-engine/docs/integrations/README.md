# Integration Guides

Setup instructions for connecting the PDF-to-PPTX Conversion API with external platforms.

---

## Make.com (formerly Integromat)

### Setup

1. Open your Make.com scenario editor
2. Add a new **HTTP > Make a request** module (or use the custom app if published)
3. Configure the connection:

| Field | Value |
|-------|-------|
| Base URL | `https://your-api-domain.com` |
| Header Name | `Authorization` |
| Header Value | `Bearer <your-api-key>` |

### Building a Scenario

1. **Trigger**: Choose your trigger (e.g., Google Drive new file, email attachment, webhook)
2. **Convert PDF**: Use the `Convert PDF` module (`POST /v1/convert`) with the PDF file
3. **Wait**: Add a **Sleep** module set to 2 seconds
4. **Poll Status**: Use `Check Job Status` (`GET /v1/jobs/{job_id}`)
5. **Router**: Branch on the `status` field:
   - If `completed` → proceed to Download
   - If `failed` → send error notification
   - If `queued` or `processing` → loop back to the Sleep module
6. **Download**: Use `Download Result` (`GET /v1/jobs/{job_id}/download`) to get the PPTX
7. **Route Result**: Send the PPTX to Google Drive, Dropbox, email, etc.

### Files

- Module definitions: [`make_com.json`](./make_com.json)

---

## Airtable Automations

### Prerequisites

A table named **PDF Conversion Requests** with these columns:

| Column Name | Field Type | Notes |
|-------------|-----------|-------|
| PDF | Attachment | The source PDF file |
| Status | Single select | Options: `Queued`, `Processing`, `Completed`, `Failed` |
| Job ID | Text | Populated by the automation |
| Output URL | URL | Set via webhook callback |

### Setup

1. Go to **Automations** in your Airtable base
2. Create a new automation with trigger **When a record is created** in "PDF Conversion Requests"
3. Add a **Run script** action and paste the contents of `airtable_automation.js`
4. Replace the placeholders:
   - `API_BASE` → your API domain
   - `API_KEY` → your API key
5. Set up a webhook endpoint that receives POST callbacks from the API and updates the Airtable record with the `Output URL` and `Completed`/`Failed` status

### Webhook Callback Handler

Your webhook endpoint should:
1. Receive a POST with the job result
2. Look up the `recordId` from the query string
3. Update the Airtable record with the download URL and new status

### Files

- Automation script: [`airtable_automation.js`](./airtable_automation.js)

---

## Bubble.io

### Setup

1. Navigate to **Plugins > API Connector** in your Bubble editor
2. Click **Add another API** and import [`bubble_io_connector.json`](./bubble_io_connector.json)
3. Set your API key in the authentication fields

### Using in Workflows

1. **Convert**: Call the `Convert PDF` endpoint, passing the PDF file from a file uploader element
2. **Track Status**: Use `Get Job Status` in a recurring workflow (e.g., with the **Backend Workflow** scheduler) to poll every 2-3 seconds
3. **Download**: Once `status = completed`, call `Download PPTX` and provide the file link to the user

### Recommended Workflow Structure

```
Trigger: Button click (Upload)
  → Convert PDF (pass uploaded file)
  → Save job_id to page state or custom data type
  → Schedule Backend Workflow (every 2 seconds)
      → Get Job Status
      → If status = "completed" → Download PPTX → Display link
      → If status = "failed" → Show error alert
      → If status = "queued" or "processing" → Schedule next poll
```

### Files

- Connector definition: [`bubble_io_connector.json`](./bubble_io_connector.json)

---

## Common Configuration

### API Key

All integrations require an API key. Pass it as:

```
Authorization: Bearer <your-api-key>
```

### Webhook Format

When a job completes or fails and a `webhook_url` was provided, the API sends a POST with:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "file_name": "presentation.pptx",
    "file_size": 245760,
    "download_url": "https://api.your-domain.com/v1/jobs/.../download"
  }
}
```

### Polling Best Practices

- Poll interval: **2-3 seconds**
- Timeout: Most conversions complete within 60 seconds for files under 10 MB
- Max retries before giving up: **150** (5 minutes at 2s intervals)
- Always check for `status = "failed"` and handle the `error` object
