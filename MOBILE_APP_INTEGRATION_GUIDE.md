# PharmaSafe API Integration Guide for Mobile App

## 📋 **Overview**
This document provides complete API integration details for the PharmaSafe pharmaceutical regulatory system. All APIs are production-ready and actively serving the web application.

---

## 🌐 **Base URL**
```
https://api.lehana.in/ai/gemini-file-search
```

---

## 🔑 **API Endpoints**

### **1. Search Medicine Status (Primary Feature)**

**Endpoint:** `POST /api/search`

**Purpose:** Search whether a medicine is banned, allowed, or regulated in India with complete regulatory details.

**Request Format:**
```json
{
  "query": "Is paracetamol banned in India?",
  "sessionId": "mobile-session-12345"
}
```

**Request Parameters:**
- `query` (string, required): The medicine name or question about drug status
- `sessionId` (string, optional): Unique session identifier for tracking

**Example cURL:**
```bash
curl -X POST https://api.lehana.in/ai/gemini-file-search/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Is paracetamol banned in India?",
    "sessionId": "mobile-session-001"
  }'
```

**Response Format:**
```json
{
  "query": "dolo 650",
  "medicine_searched": "Paracetamol (active ingredient in Dolo 650)",
  "current_status": "open",
  "results": {
    "gazette_id": "N/A",
    "pdf_name": "N/A",
    "medicine_name": "N/A",
    "date_of_ban": "N/A",
    "date_of_uplift": "N/A",
    "drug_category": "single_drug",
    "schedule_classification": "Not Scheduled",
    "controlled_status": "Not controlled",
    "source_authority": "CDSCO",
    "act_reference": "N/A",
    "summary": "Paracetamol, the active ingredient in Dolo 650, was not found to be listed as banned, scheduled, or controlled in the indexed CDSCO regulatory documents, indicating an open status."
  },
  "sessionId": "mobile-session-001"
}
```

**🎨 KEY FIELDS TO DISPLAY IN MOBILE UI:**

1. **Medicine Name** (Header - Large, Bold)
   - Field: `medicine_searched`
   - Example: "Paracetamol (active ingredient in Dolo 650)"

2. **Status Badge** (Prominent Visual Indicator)
   - Field: `current_status`
   - Values: `"open"` (allowed), `"banned"`, `"restricted"`
   - **UI Suggestion:**
     - `"open"` → Green badge with ✅ "ALLOWED"
     - `"banned"` → Red badge with 🚫 "BANNED"
     - `"restricted"` → Orange badge with ⚠️ "RESTRICTED"

3. **Summary** (Primary Information - Most Important)
   - Field: `results.summary`
   - Display in a prominent card/section
   - This contains the complete answer in plain English

4. **Regulatory Details** (Expandable Section)
   - `results.drug_category` → "Drug Category"
   - `results.schedule_classification` → "Schedule Class"
   - `results.controlled_status` → "Controlled Status"
   - `results.source_authority` → "Authority"
   - `results.date_of_ban` → "Ban Date" (if applicable)
   - `results.date_of_uplift` → "Uplift Date" (if applicable)
   - `results.gazette_id` → "Gazette ID"
   - `results.act_reference` → "Act Reference"

**⚠️ Important Notes:**
- Hide fields with values `"N/A"` or `"Not specified in documents"`
- The `summary` field is the most important - display it prominently
- `current_status` determines the overall safety indicator

---

### **2. Upload & Index Document**

**Endpoint:** `POST /api/index`

**Purpose:** Upload a pharmaceutical regulatory PDF document and index it for RAG search.

**Request Format:** `multipart/form-data`

**Request Parameters:**
- `file` (file, required): PDF file to upload
- `metadata` (JSON string, optional): Document metadata

**Example cURL:**
```bash
curl -X POST https://api.lehana.in/ai/gemini-file-search/api/index \
  -F "file=@banned-drugs-cdsco.pdf" \
  -F 'metadata={"source": "CDSCO", "type": "banned_drugs_list", "year": "2024"}'
```

**Response Format:**
```json
{
  "message": "Document indexed successfully",
  "result": {
    "done": true,
    "response": {
      "documentName": "fileSearchStores/abc123/documents/xyz789"
    }
  }
}
```

**🎨 MOBILE UI DISPLAY:**
- Show success message: "Document uploaded and indexed successfully"
- Display document name
- Show upload progress indicator during upload

---

### **3. List All Documents**

**Endpoint:** `GET /api/documents`

**Purpose:** Retrieve all indexed regulatory documents in the database.

**Request Format:** Simple GET request (no body required)

**Example cURL:**
```bash
curl -X GET https://api.lehana.in/ai/gemini-file-search/api/documents
```

**Response Format:**
```json
{
  "documents": [
    {
      "name": "fileSearchStores/abc123/documents/xyz789",
      "displayName": "banned-drugs-cdsco-2024.pdf",
      "mimeType": "application/pdf",
      "sizeBytes": 34703,
      "createTime": "2026-02-16T10:30:00Z",
      "updateTime": "2026-02-16T10:30:00Z",
      "metadata": [
        {"key": "source", "stringValue": "CDSCO"},
        {"key": "type", "stringValue": "banned_drugs_list"},
        {"key": "year", "stringValue": "2024"}
      ],
      "state": "ACTIVE"
    }
  ],
  "total": 1
}
```

**🎨 MOBILE UI DISPLAY:**

For each document, show:
1. **Document Name:** `displayName`
2. **File Type Icon:** Based on `mimeType`
3. **File Size:** Convert `sizeBytes` to KB/MB (e.g., "34.7 KB")
4. **Upload Date:** Format `createTime` as readable date
5. **Source:** Extract from `metadata` array (key: "source")
6. **Status Badge:** `state` (ACTIVE = green, others = gray)

**List Item Layout Suggestion:**
```
📄 banned-drugs-cdsco-2024.pdf
    💾 34.7 KB  |  📅 Feb 16, 2026  |  🏛️ CDSCO
    ✅ ACTIVE
```

---

### **4. Delete Single Document**

**Endpoint:** `POST /api/documents/delete`

**Purpose:** Delete a specific document by its ID.

**Request Format:**
```json
{
  "documentId": "fileSearchStores/abc123/documents/xyz789"
}
```

**Example cURL:**
```bash
curl -X POST https://api.lehana.in/ai/gemini-file-search/api/documents/delete \
  -H "Content-Type: application/json" \
  -d '{"documentId": "fileSearchStores/abc123/documents/xyz789"}'
```

**Response Format:**
```json
{
  "message": "Document deleted successfully",
  "document": {
    "name": "fileSearchStores/abc123/documents/xyz789",
    "displayName": "banned-drugs-cdsco-2024.pdf"
  }
}
```

**🎨 MOBILE UI:**
- Show confirmation dialog before deleting: "Are you sure you want to delete [filename]?"
- Display success message after deletion
- Refresh document list

---

### **5. Delete All Documents**

**Endpoint:** `DELETE /api/documents/all`

**Purpose:** Delete all documents from the database (bulk operation).

**Request Format:** Simple DELETE request (no body required)

**Example cURL:**
```bash
curl -X DELETE https://api.lehana.in/ai/gemini-file-search/api/documents/all
```

**Response Format:**
```json
{
  "message": "All documents deleted",
  "geminiDeleted": 3,
  "geminiFailed": 0,
  "localDeleted": 3,
  "details": [
    {"name": "fileSearchStores/.../doc1", "success": true},
    {"name": "fileSearchStores/.../doc2", "success": true},
    {"name": "fileSearchStores/.../doc3", "success": true}
  ]
}
```

**🎨 MOBILE UI:**
- Show strong warning dialog: "⚠️ This will delete ALL documents. This action cannot be undone!"
- Require double confirmation
- Show deletion progress
- Display summary: "Successfully deleted X documents"

---

## 📱 **Mobile App Integration Checklist**

### **Required Screens:**

#### **1. Medicine Search Screen (Primary Feature)**
```
┌─────────────────────────────────┐
│  🔍 Search Medicine Status      │
├─────────────────────────────────┤
│  [Search Bar]                   │
│  "Is paracetamol banned?"       │
│  [Search Button]                │
├─────────────────────────────────┤
│  Quick Searches:                │
│  • Check banned drugs           │
│  • Verify FDC status            │
│  • Controlled substances        │
└─────────────────────────────────┘
```

#### **2. Results Screen**
```
┌─────────────────────────────────┐
│  Medicine: Paracetamol          │
│  ┌───────────────────────────┐  │
│  │  ✅ ALLOWED / OPEN        │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  📋 Summary                     │
│  ┌───────────────────────────┐  │
│  │ Paracetamol is not banned │  │
│  │ in India. It is a widely  │  │
│  │ available medication...   │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  📊 Regulatory Details ▼        │
│  • Drug Category: single_drug  │
│  • Schedule: Not Scheduled     │
│  • Authority: CDSCO            │
└─────────────────────────────────┘
```

#### **3. Document Management Screen**
```
┌─────────────────────────────────┐
│  📋 Document Database           │
│  [Search] [Upload] [Delete All] │
├─────────────────────────────────┤
│  📄 banned-drugs-2024.pdf       │
│     💾 34.7 KB | 📅 Feb 16      │
│     🏛️ CDSCO | ✅ ACTIVE        │
│     [Delete]                    │
├─────────────────────────────────┤
│  📄 fdc-list-2023.pdf           │
│     💾 128.5 KB | 📅 Jan 10     │
│     🏛️ CDSCO | ✅ ACTIVE        │
│     [Delete]                    │
└─────────────────────────────────┘
```

---

## 🎯 **Search Query Examples**

Test with these queries for comprehensive coverage:

### **Simple Medicine Checks:**
```
"Is paracetamol banned in India?"
"Check dolo 650 status"
"Is aspirin allowed?"
```

### **FDC (Fixed Dose Combination) Checks:**
```
"Tell me about phenylpropanolamine ban"
"Is nimesulide + paracetamol combination banned?"
```

### **Controlled Substance Checks:**
```
"Is tramadol a controlled substance?"
"Check codeine regulatory status"
```

### **Recent Bans:**
```
"Which drugs were banned in latest notification?"
"Show recent pharmaceutical bans"
```

---

## ⚡ **Response Time & Performance**

- **Search API:** Typically responds in 2-5 seconds
- **Upload API:** 3-10 seconds depending on file size
- **List/Delete APIs:** < 1 second

**Recommendation:** Show loading indicators for all API calls.

---

## 🔐 **Authentication**

Currently, these APIs are **open** (no authentication required). If your app uses sessions, include the `sessionId` parameter in search requests for tracking.

---

## ❌ **Error Handling**

### **Common HTTP Status Codes:**
- `200` - Success
- `400` - Bad request (missing parameters)
- `404` - Document not found
- `500` - Server error
- `503` - Service unavailable

### **Error Response Format:**
```json
{
  "error": "Error message description",
  "status": "error"
}
```

**Mobile UI Handling:**
- Show user-friendly error messages
- For network errors: "Unable to connect. Please check your internet connection"
- For 500 errors: "Service temporarily unavailable. Please try again later"

---

## 🎨 **UI/UX Recommendations**

### **Color Coding:**
- **Green (#10b981):** Allowed/Open status
- **Red (#dc2626):** Banned status
- **Orange (#f59e0b):** Restricted/Warning status
- **Gray (#6b7280):** N/A or not applicable

### **Typography:**
- Medicine Name: Bold, 18-20px
- Status Badge: Bold, 16-18px
- Summary: Regular, 14-16px
- Details: Regular, 12-14px

### **Icons:**
- ✅ Allowed
- 🚫 Banned
- ⚠️ Restricted
- 📋 Summary
- 📊 Details
- 📄 Document
- 🗑️ Delete
- 🔄 Refresh

---

## 📊 **Real Response Example (Banned Drug)**

**Query:** "Is nimesulide banned in India?"

**Expected Response:**
```json
{
  "query": "Is nimesulide banned in India?",
  "medicine_searched": "Nimesulide",
  "current_status": "banned",
  "results": {
    "medicine_name": "Nimesulide",
    "date_of_ban": "2023-06-15",
    "drug_category": "single_drug",
    "schedule_classification": "Schedule H",
    "controlled_status": "Banned",
    "source_authority": "CDSCO",
    "act_reference": "Drugs and Cosmetics Act 1940",
    "summary": "Nimesulide is banned in India due to safety concerns related to liver toxicity. The drug was prohibited by CDSCO under the Drugs and Cosmetics Act 1940."
  },
  "sessionId": "mobile-session-001"
}
```

**Mobile Display:**
- Show RED badge: "🚫 BANNED"
- Highlight ban date prominently
- Display summary in red-tinted card
- Show warning icon throughout

---

## 🚀 **Quick Start Integration**

### **Step 1: Test Search API**
```javascript
// Example using fetch/axios
const searchMedicine = async (query) => {
  try {
    const response = await fetch('https://api.lehana.in/ai/gemini-file-search/api/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query,
        sessionId: 'mobile-app-' + Date.now()
      })
    });
    
    const data = await response.json();
    
    // Key fields to extract:
    const medicineName = data.medicine_searched;
    const status = data.current_status; // "open", "banned", "restricted"
    const summary = data.results.summary; // Main answer
    const details = data.results; // All regulatory details
    
    return { medicineName, status, summary, details };
  } catch (error) {
    console.error('Search failed:', error);
    throw error;
  }
};
```

### **Step 2: Display Results**
```javascript
// Pseudo-code for mobile UI
function displayResults(data) {
  // 1. Show medicine name
  medicineName.text = data.medicineName;
  
  // 2. Show status badge with color
  if (data.status === "open") {
    statusBadge.text = "✅ ALLOWED";
    statusBadge.backgroundColor = "#10b981"; // Green
  } else if (data.status === "banned") {
    statusBadge.text = "🚫 BANNED";
    statusBadge.backgroundColor = "#dc2626"; // Red
  }
  
  // 3. Show summary (MOST IMPORTANT)
  summaryText.text = data.summary;
  
  // 4. Show details (only non-N/A values)
  detailsSection.clear();
  for (let [key, value] of Object.entries(data.details)) {
    if (value !== "N/A" && value !== "Not specified in documents" && key !== "summary") {
      detailsSection.addRow(formatLabel(key), value);
    }
  }
}
```

---

## 📞 **Support & Questions**

For any integration issues or questions:
- Test all endpoints using the provided cURL examples
- Check response format matches documented structure
- Verify base URL is correct: `https://api.lehana.in/ai/gemini-file-search`

---

## ✅ **Integration Verification Checklist**

Before deploying, verify:
- [ ] Search API returns results and parses correctly
- [ ] Status badges display with correct colors
- [ ] Summary text is prominent and readable
- [ ] N/A values are hidden from UI
- [ ] Document upload works with progress indicator
- [ ] Document list displays with proper formatting
- [ ] Delete operations show confirmation dialogs
- [ ] Error messages are user-friendly
- [ ] Loading states are implemented
- [ ] Response times are acceptable

---

**Last Updated:** February 17, 2026
**API Version:** Production v1.0
**Base URL:** https://api.lehana.in/ai/gemini-file-search
