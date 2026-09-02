"""
Phase 4a: Generate HTML review dashboard.
Replaces CSV export to avoid Excel encoding corruption.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from config import OUTPUT_DIR, REVIEW_HTML_PATH
from db import init_db, get_connection


# HTML Dashboard Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mendeley Patcher - Review Dashboard</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        .subtitle {
            opacity: 0.9;
            font-size: 14px;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-top: 20px;
        }
        .stat-box {
            background: rgba(255,255,255,0.2);
            padding: 15px 25px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-number {
            font-size: 24px;
            font-weight: bold;
        }
        .stat-label {
            font-size: 12px;
            opacity: 0.9;
        }
        .controls {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-primary:hover {
            background: #5a6fd6;
        }
        .btn-success {
            background: #28a745;
            color: white;
        }
        .btn-success:hover {
            background: #218838;
        }
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        .btn-danger:hover {
            background: #c82333;
        }
        .btn-outline {
            background: transparent;
            border: 2px solid #667eea;
            color: #667eea;
        }
        .btn-outline:hover {
            background: #667eea;
            color: white;
        }
        .search-box {
            flex: 1;
            min-width: 200px;
            padding: 10px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
        }
        .search-box:focus {
            outline: none;
            border-color: #667eea;
        }
        .table-container {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        tr:hover {
            background: #f8f9fa;
        }
        tr.selected {
            background: #e8f5e9;
        }
        .field-diff {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        .field-current {
            color: #dc3545;
            text-decoration: line-through;
            font-size: 13px;
        }
        .field-proposed {
            color: #28a745;
            font-weight: 500;
        }
        .field-arrow {
            color: #667eea;
            font-weight: bold;
        }
        .checkbox-cell {
            width: 50px;
            text-align: center;
        }
        input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        .uuid-cell {
            font-family: monospace;
            font-size: 12px;
            color: #666;
            max-width: 100px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .no-changes {
            color: #28a745;
            font-style: italic;
        }
        .footer {
            margin-top: 30px;
            padding: 20px;
            background: white;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .save-status {
            font-size: 14px;
            color: #666;
        }
        .save-status.success {
            color: #28a745;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal.active {
            display: flex;
        }
        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 10px;
            max-width: 500px;
            width: 90%;
        }
        .modal h3 {
            margin-bottom: 15px;
        }
        .modal p {
            margin-bottom: 20px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Mendeley Patcher - Review Dashboard</h1>
            <p class="subtitle">Review and approve metadata corrections before applying to Mendeley cloud</p>
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-number" id="total-count">0</div>
                    <div class="stat-label">Total Documents</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number" id="corrections-count">0</div>
                    <div class="stat-label">Need Corrections</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number" id="approved-count">0</div>
                    <div class="stat-label">Approved</div>
                </div>
            </div>
        </header>
        
        <div class="controls">
            <button class="btn btn-primary" onclick="selectAll()">Select All</button>
            <button class="btn btn-outline" onclick="deselectAll()">Deselect All</button>
            <input type="text" class="search-box" id="search" placeholder="Search by title, author, or UUID..." oninput="filterTable()">
            <button class="btn btn-success" onclick="saveApprovals()">Save Approvals</button>
            <button class="btn btn-danger" onclick="clearApprovals()">Clear Saved</button>
        </div>
        
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th class="checkbox-cell">Approve</th>
                        <th>UUID</th>
                        <th>Title (Current - Mendeley)</th>
                        <th>Title (Proposed - Crossref)</th>
                        <th>Year</th>
                        <th>Authors</th>
                    </tr>
                </thead>
                <tbody id="documents-body">
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <div class="save-status" id="save-status">Not saved yet</div>
            <div>
                <button class="btn btn-success" onclick="saveApprovals()">Save Approvals</button>
            </div>
        </div>
    </div>
    
    <div class="modal" id="save-modal">
        <div class="modal-content">
            <h3>Approvals Saved!</h3>
            <p>Your selections have been saved to the <strong>SQLite database</strong>.</p>
            <p>Run the following command to apply the changes:</p>
            <code>python orchestrator.py approve</code>
            <br><br>
            <button class="btn btn-primary" onclick="closeModal()">Close</button>
        </div>
    </div>
    
    <script>
        // Document data will be loaded from JSON
        let documents = [];
        let approvals = {};
        
        // Load data from embedded JSON or fetch from file
        function loadData(data) {
            documents = data;
            
            // Load saved approvals from localStorage
            const saved = localStorage.getItem('mendeley_approvals');
            if (saved) {
                approvals = JSON.parse(saved);
            }
            
            renderTable();
            updateStats();
        }
        
        function renderTable() {
            const tbody = document.getElementById('documents-body');
            const searchTerm = document.getElementById('search').value.toLowerCase();
            
            tbody.innerHTML = '';
            
            documents.forEach(doc => {
                // Filter by search
                if (searchTerm && !matchesSearch(doc, searchTerm)) {
                    return;
                }
                
                const tr = document.createElement('tr');
                tr.className = approvals[doc.uuid] ? 'selected' : '';
                
                const needsCorrection = doc.title_mendeley !== doc.title_crossref || 
                                       doc.year_mendeley !== doc.year_crossref ||
                                       doc.authors_mendeley !== doc.authors_crossref;
                
                tr.innerHTML = `
                    <td class="checkbox-cell">
                        <input type="checkbox" 
                               ${approvals[doc.uuid] ? 'checked' : ''} 
                               onchange="toggleApproval('${doc.uuid}', this.checked)">
                    </td>
                    <td class="uuid-cell" title="${doc.uuid}">${doc.uuid.substring(0, 12)}...</td>
                    <td>
                        ${needsCorrection ? 
                            `<div class="field-current">${escapeHtml(doc.title_mendeley || 'N/A')}</div>` :
                            `<span class="no-changes">${escapeHtml(doc.title_mendeley || 'N/A')}</span>`
                        }
                    </td>
                    <td>
                        ${needsCorrection ? 
                            `<div class="field-proposed">${escapeHtml(doc.title_crossref || 'N/A')}</div>` :
                            `<span class="no-changes">${escapeHtml(doc.title_crossref || 'N/A')}</span>`
                        }
                    </td>
                    <td>
                        ${doc.year_mendeley !== doc.year_crossref ? 
                            `<span class="field-current">${doc.year_mendeley || '?'}</span> 
                             <span class="field-arrow">&rarr;</span> 
                             <span class="field-proposed">${doc.year_crossref || '?'}</span>` :
                            `<span>${doc.year_mendeley || '?'}</span>`
                        }
                    </td>
                    <td>
                        ${doc.authors_mendeley !== doc.authors_crossref ? 
                            `<div class="field-current">${escapeHtml(doc.authors_mendeley || 'N/A')}</div>
                             <div class="field-proposed">${escapeHtml(doc.authors_crossref || 'N/A')}</div>` :
                            `<span class="no-changes">${escapeHtml(doc.authors_mendeley || 'N/A')}</span>`
                        }
                    </td>
                `;
                
                tbody.appendChild(tr);
            });
        }
        
        function matchesSearch(doc, term) {
            return (doc.title_mendeley || '').toLowerCase().includes(term) ||
                   (doc.title_crossref || '').toLowerCase().includes(term) ||
                   (doc.authors_mendeley || '').toLowerCase().includes(term) ||
                   (doc.authors_crossref || '').toLowerCase().includes(term) ||
                   (doc.uuid || '').toLowerCase().includes(term);
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function toggleApproval(uuid, approved) {
            if (approved) {
                approvals[uuid] = true;
            } else {
                delete approvals[uuid];
            }
            updateStats();
            renderTable();
        }
        
        function selectAll() {
            documents.forEach(doc => {
                approvals[doc.uuid] = true;
            });
            updateStats();
            renderTable();
        }
        
        function deselectAll() {
            approvals = {};
            updateStats();
            renderTable();
        }
        
        function updateStats() {
            document.getElementById('total-count').textContent = documents.length;
            document.getElementById('corrections-count').textContent = documents.filter(d => 
                d.title_mendeley !== d.title_crossref || 
                d.year_mendeley !== d.year_crossref ||
                d.authors_mendeley !== d.authors_crossref
            ).length;
            document.getElementById('approved-count').textContent = Object.keys(approvals).length;
        }
        
        function filterTable() {
            renderTable();
        }
        
        function saveApprovals() {
            // Save to localStorage
            localStorage.setItem('mendeley_approvals', JSON.stringify(approvals));
            
            // Also trigger download of JSON file
            const output = {
                timestamp: new Date().toISOString(),
                approvals: Object.keys(approvals).filter(k => approvals[k])
            };
            
            // Save approvals to SQLite via API call
            fetch('/api/approve', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    uuids: Object.keys(approvals).filter(k => approvals[k])
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show success status
                    const status = document.getElementById('save-status');
                    status.textContent = 'Saved at ' + new Date().toLocaleTimeString();
                    status.className = 'save-status success';
                    
                    // Show modal
                    document.getElementById('save-modal').classList.add('active');
                } else {
                    alert('Error saving approvals: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                alert('Error saving approvals: ' + error.message);
            });
        }
        
        function clearApprovals() {
            if (confirm('Clear all saved approvals?')) {
                approvals = {};
                localStorage.removeItem('mendeley_approvals');
                updateStats();
                renderTable();
                document.getElementById('save-status').textContent = 'Approvals cleared';
                document.getElementById('save-status').className = 'save-status';
            }
        }
        
        function closeModal() {
            document.getElementById('save-modal').classList.remove('active');
        }
        
        // Initialize with embedded data if available
        if (typeof documentData !== 'undefined') {
            loadData(documentData);
        }
    </script>
</body>
</html>
"""


def generate_review_dashboard():
    """Generate HTML review dashboard from database."""
    init_db()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            uuid,
            title_mendeley,
            title_crossref,
            year_mendeley,
            year_crossref,
            authors_mendeley,
            authors_crossref,
            needs_correction
        FROM documents 
        WHERE state = 'DIFFED'
        ORDER BY needs_correction DESC, title_mendeley
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("No documents in DIFFED state.")
        print("Run diff.py first.")
        return False
    
    # Convert to list of dicts
    documents = [dict(row) for row in rows]
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate HTML with embedded data
    html_content = HTML_TEMPLATE.replace(
        "if (typeof documentData !== 'undefined') {\n            loadData(documentData);\n        }",
        f"const documentData = {json.dumps(documents, ensure_ascii=False)};\n        loadData(documentData);"
    )
    
    # Write HTML file
    with open(REVIEW_HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Also save raw JSON for programmatic access
    json_path = os.path.join(OUTPUT_DIR, 'review_data.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)
    
    print(f"Generated review dashboard:")
    print(f"  HTML: {REVIEW_HTML_PATH}")
    print(f"  JSON: {json_path}")
    print(f"\nNext steps:")
    print(f"  1. Open {REVIEW_HTML_PATH} in your web browser")
    print(f"  2. Review each document and check the boxes for corrections to apply")
    print(f"  3. Click 'Save Approvals' to download review_approvals.json")
    print(f"  4. Run: python orchestrator.py approve")
    
    return True


if __name__ == "__main__":
    success = generate_review_dashboard()
    sys.exit(0 if success else 1)
