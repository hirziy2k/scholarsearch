// Airtable Automation Script
// Trigger: When a record is created in "PDF Conversion Requests"
// Fields: PDF (attachment), Status (single select), Job ID (text), Output URL (url)

const API_BASE = 'https://your-api-domain.com';
const API_KEY = 'your-api-key';

// Step 1: Get the newly created record
const inputConfig = input.config();
const recordId = inputConfig.recordId;

// Step 2: Fetch the record to get the PDF attachment
const record = await base.getTable('PDF Conversion Requests').recordAsync(recordId);
const attachments = record.getCellValue('PDF');

if (!attachments || attachments.length === 0) {
    throw new Error('No PDF attachment found');
}

// Step 3: Download the PDF from Airtable's CDN
const pdfUrl = attachments[0].url;
const pdfResponse = await fetch(pdfUrl);
const pdfBlob = await pdfResponse.blob();

// Step 4: Upload to the conversion API
const formData = new FormData();
formData.append('file', pdfBlob, attachments[0].filename);
formData.append('webhook_url', `https://your-webhook-handler.com/airtable/callback?recordId=${recordId}`);

const convertResponse = await fetch(`${API_BASE}/v1/convert`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${API_KEY}` },
    body: formData
});

const result = await convertResponse.json();

// Step 5: Update the record with the job ID
await record.updateAsync({
    'Status': 'Queued',
    'Job ID': result.job_id
});
