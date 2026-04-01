# 🔧 Troubleshooting Guide: PIL Generation Not Showing

## Problem: "When I click Generate PIL, nothing shows in the frontend"

### Quick Diagnosis Steps

#### 1️⃣ Open Browser Developer Tools
- **Firefox/Chrome/Edge:** Press `F12`
- **Safari:** Cmd + Option + I
- Go to **Console** tab

#### 2️⃣ Click "Generate PIL" and watch the Console
You should see logs like:
```
🚀 generatePIL started: {selIdx: 0, API_URL: 'http://localhost:8001', auto: false}
📡 Fetching: http://127.0.0.1:8001/generate-pil?idx=0
✅ PIL data received: {severity_score: 0.45, priority_level: "MEDIUM", ...}
✓ Title updated: "Ernakulam District Panchayat..."
✓ Severity updated: 0.45
...
🎉 generatePIL completed successfully
```

---

## Common Issues & Solutions

### Issue 1: API Not Reachable
**Console Error:**
```
❌ generatePIL error: Failed to fetch
```

**Cause:** Backend is not running or API URL is wrong

**Fix:**
1. Check backend is running:
```bash
# In PowerShell, go to project directory
cd "c:\Users\ISHA SAHAY\NyayLens-AI-Powered-RAG-System-for-Public-Interest-Litigation"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

2. Verify backend responds:
```bash
# In another PowerShell window
Invoke-WebRequest http://127.0.0.1:8001/health -UseBasicParsing
# Should return status: 200
```

3. Check API_URL in console (paste in console):
```javascript
console.log("API_URL:", API_URL);
console.log("Expected: http://localhost:8001 or http://127.0.0.1:8001");
```

---

### Issue 2: API Responds but Data Not Displaying
**Console Output:**
```
✅ PIL data received: {...}
📡 But no ✓ Title updated, ✓ Severity updated, etc.
```

**Cause:** DOM elements not found or not initialized

**Fix:**
1. Check if elements exist (paste in console):
```javascript
console.log("Title element:", document.getElementById("newsTitle"));
console.log("Severity element:", document.getElementById("severityScore"));
console.log("Topics element:", document.getElementById("topics"));
console.log("Entity list:", document.getElementById("entityList"));
```

All should return non-null values.

2. Check if excerptEl is initialized:
```javascript
console.log("excerptEl:", excerptEl);
// Should be the excerpt div, not null
```

---

### Issue 3: "HTTP 502 Bad Gateway" Error
**Console Error:**
```
❌ generatePIL error: HTTP 502
```

**Cause:** Backend crashed or Render is having issues

**Fix - Local:**
1. Restart backend:
```bash
# Kill old process
Get-Process -Name python* | Stop-Process -Force

# Wait 2 seconds
Start-Sleep -Seconds 2

# Restart
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

2. Check logs for errors:
```bash
# Look for ERROR or exception in backend logs
# The logs should show:
# "🔍 Extracting issue entities with spaCy..."
# "⚖️ Retrieving legal sections..."
# "✨ Generating PIL in markdown format..."
```

---

### Issue 4: Data Loads but Shows as "—" (dashes)
**Console Output:**
```
✅ PIL data received: {...}
But frontend shows "Severity: —" instead of "Severity: 4.5 / 10"
```

**Cause:** DOM element found but not updated properly

**Fix:**
1. Check response data format:
```javascript
// In console, after clicking Generate PIL
console.log("Data structure:", {
  news_title: data.news_title,
  severity_score: data.severity_score,
  priority_level: data.priority_level,
  topics: data.topics,
  entities: data.entities
});
```

2. Verify values are not null/undefined:
```javascript
if (data.severity_score === undefined) {
  console.warn("severity_score is undefined!");
}
```

---

### Issue 5: "Extracting issue entities with spaCy..." Never Completes
**Backend Log:**
```
🔍 Extracting issue entities with spaCy...
[... then nothing, keeps repeating]
```

**Cause:** spaCy model not loaded or API stuck

**Fix:**
1. Verify spaCy model is installed:
```bash
python -m spacy download en_core_web_sm
```

2. Check backend health directly:
```bash
Invoke-WebRequest http://127.0.0.1:8001/health -UseBasicParsing
# Should return {"status": "ok"}
```

3. Check for hanging processes:
```bash
Get-Process -Name python*
# If multiple python processes, kill all and restart
Get-Process -Name python* | Stop-Process -Force
```

---

## Full Debugging Workflow

### Step 1: Verify Backend
```bash
# Check if running
curl http://127.0.0.1:8001/health

# Test API directly without frontend
curl "http://127.0.0.1:8001/generate-pil?idx=0"

# Should return full PIL data with all sections
```

### Step 2: Check Frontend (Console)
1. Open DevTools: Press `F12`
2. Select **Console** tab
3. Paste:
```javascript
console.log({
  api_url: API_URL,
  DOM_initialized: Boolean(excerptEl),
  news_select: Boolean(newsSelect),
  topic_select: Boolean(topicSelect)
});
```

Should show all `true` except `api_url` which should be `http://localhost:8001`

### Step 3: Test Generate PIL
1. In Console, run:
```javascript
generatePIL(0); // Generate PIL for article 0
```

2. Watch console for:
   - 🚀 Start marker
   - 📡 API fetch
   - ✅ Data received
   - ✓ Element updates
   - 🎉 Completion

### Step 4: If Still Failing
Run diagnostic:
```javascript
// Check each step
console.log("=== PIL Display Diagnostic ===");
console.log("API URL:", API_URL);
console.log("News loaded:", newsItems.length, "items");
console.log("DOM elements found:");
console.log("  - newsTitle:", !!document.getElementById("newsTitle"));
console.log("  - severityScore:", !!document.getElementById("severityScore"));
console.log("  - priorityLevel:", !!document.getElementById("priorityLevel"));
console.log("  - topics:", !!document.getElementById("topics"));
console.log("  - entityList:", !!document.getElementById("entityList"));
console.log("  - excerptEl (JS var):", !!excerptEl);
```

---

## Clear Cache & Reload

If frontend still shows old data after backend fixes:

### Chrome/Brave:
1. Press `Ctrl + Shift + Delete`
2. Select "All time"
3. Check "Cookies and other site data" and "Cached images"
4. Click "Clear data"

### Firefox:
1. Press `Ctrl + Shift + Delete`
2. Select "Everything"
3. Click "Clear Now"

### Edge:
1. Press `Ctrl + Shift + Delete`
2. Click "Clear now"

Then **refresh** the page (`F5` or `Ctrl + R`)

---

## Still Having Issues?

### Check Backend Logs
Look for patterns:
- ✅ `REAL RAG PIPELINE RESTORED` - Good, NLP is active
- ✅ `Extracting issue entities with spaCy` - Good, entity recognition working
- ⚠️ `No chunks matched` - RAG not finding legal sections
- ❌ `socket.error` - Port already in use
- ❌ `ModuleNotFoundError` - Missing dependency

### Restart Everything
```bash
# Kill all Python processes
Get-Process -Name python* | Stop-Process -Force

# Wait
Start-Sleep -Seconds 3

# Clear cache
# Go to browser → Settings → Clear browsing data

# Restart backend fresh
cd "c:\Users\ISHA SAHAY\NyayLens-AI-Powered-RAG-System-for-Public-Interest-Litigation"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001

# Refresh frontend in browser (F5)
```

---

## What Should Happen When Working

1. **Select an article** → Article details appear
2. **Click "⚡ Generate PIL"** → Status shows "Generating PIL..."
3. **Backend processes** → Logs show entity extraction + legal retrieval
4. **Frontend displays**:
   - ✅ Title changes to PIL title
   - ✅ Severity shows like "4.5 / 10"
   - ✅ Priority shows "HIGH", "MEDIUM", or "LOW"
   - ✅ Topics list appears (health, education, etc.)
   - ✅ Entities list shows 4-5 named entities
5. **Status updated** → "PIL Generated! Click 'View & Edit PIL' to customize."
6. **Click "📋 View & Edit PIL"** → Modal opens with full PIL document

---

## Performance Considerations

- First API call may take 3-5 seconds (spaCy loading model)
- Subsequent calls should be 1-2 seconds
- If taking longer:
  - Check server resources
  - Look for background processes killing CPU
  - Verify spaCy model fully downloaded: `python -m spacy download en_core_web_sm`

---

## Need More Help?

Add these to Console to get full diagnostic dump:
```javascript
{
  api_url: API_URL,
  hostname: window.location.hostname,
  port: window.location.port,
  protocol: window.location.protocol,
  localStorage_api: localStorage.getItem("api_base_url"),
  news_count: newsItems.length,
  current_draft: currentDraftId,
  browser: navigator.userAgent
}
```

Copy the output and share it with your logs!
