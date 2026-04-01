# 🧪 Render Production Testing Guide

## Current Status
✅ **Backend Code**: Fixed with lazy-loading spacy model  
✅ **Frontend Code**: Enhanced with diagnostics logging  
✅ **Test Pages**: Created for quick testing  
⏳ **Render Deployment**: In progress (rebuilding with new code)

---

## Step-by-Step Testing

### **Step 1: Wait for Render to Rebuild**
After pushing code, Render auto-rebuilds (takes 2-5 minutes):
- Go to: https://dashboard.render.com
- Find service: `nyaylens-backend`
- Check "Events" or "Logs" tab for build status
- Wait for: "✓ Deploy successful" message

### **Step 2: Test Health Endpoint**
Once deployment completes, test:

```
https://nyaylens-backend.onrender.com/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-01T...",
  "version": "1.0.0"
}
```

**If you get 502:** Check Render logs for:
- Build errors
- Startup errors
- Memory/resource issues

### **Step 3: Test PIL Generation**
```
https://nyaylens-backend.onrender.com/generate-pil?idx=0
```

**Expected Response:**
```json
{
  "news_title": "...",
  "severity_score": 0.45,
  "priority_level": "MEDIUM",
  "topics": ["education"],
  "entities": ["Budget", "K.G. Radhakrishnan", ...],
  ...
}
```

### **Step 4: Test Main Frontend**
1. Visit: https://nyaylens-backend.onrender.com/
2. Press **F12** to open Developer Tools
3. Go to **Console** tab
4. Click **"⚡ Generate PIL"** button
5. Look for console logs starting with:
   - 🚀 generatePIL started
   - 📡 Fetching: ...
   - ✅ PIL data received
   - ✓ Title updated
   - ✓ Severity updated
   - ✓ Priority updated
   - ✓ Topics updated
   - 🎉 generatePIL completed successfully

**Check above console for displayed data:**
- ✅ Title appears
- ✅ Severity Score (e.g., "4.5 / 10")
- ✅ Priority (e.g., "MEDIUM")
- ✅ Topics (e.g., "education")
- ✅ Entities list populated

### **Step 5: Test Display**
Click **"View & Edit PIL"** button to see:
- Full PIL document in modal
- All sections with real data
- No hardcoded defaults

---

## Troubleshooting

### **502 Bad Gateway**
This means backend crashed or isn't starting:

1. **Check Render Logs**:
   - Dashboard → nyaylens-backend → Logs
   - Look for error messages

2. **Common Issues**:
   - spaCy download still timing out → Check render.yaml timeout (now 180 sec)
   - Missing dependencies → Check requirements.txt
   - Memory issues → Check resource usage

3. **Fix**:
   - If timeout: Render will attempt download on first request (lazy-load)
   - If missing dep: Add to requirements.txt and redeploy
   - If memory: Try Paid plan

### **Blank Fields**
If severity/priority/topics not showing:

1. **Check console for warnings**:
   - Look for "❌" or "⚠️" messages
   - Look for "NOT FOUND" in DOM elements check

2. **Solution**:
   - Clear cache: Ctrl+Shift+Delete → All time
   - Reload: F5
   - Check script.js loaded (look for "Init: Elements initialized")

### **API Returns Data but Frontend Blank**
Console shows data but page shows dashes:

1. **Likely Issue**: Elements missing from HTML
2. **Check**:
   - Open page source (Ctrl+U)
   - Search for: `id="severityScore"`, `id="priorityLevel"`, etc.
3. **Solution**:
   - Share console errors
   - Verify index.html wasn't corrupted

---

## Quick Test URLs

| Test | URL |
|------|-----|
| Health Check | https://nyaylens-backend.onrender.com/health |
| API Test | https://nyaylens-backend.onrender.com/generate-pil?idx=0 |
| Main Page | https://nyaylens-backend.onrender.com/ |
| Test Page 1 | https://nyaylens-backend.onrender.com/test-display.html |
| Test Page 2 | https://nyaylens-backend.onrender.com/render-test.html |
| Browser Console | Open any page above + Press F12 |

---

## What We Fixed

### **Backend Changes (Commit 13f6c02)**
✅ Lazy-load spaCy model instead of blocking build
✅ 300-second timeout for download (graceful fallback)
✅ Downloads on first API request if needed
✅ No more Render build timeouts

### **Frontend Changes (Commit 1c04959)**
✅ Enhanced logging with diagnostics
✅ Element existence checking
✅ Better error messages
✅ Console shows exactly what's happening

### **Config Changes**
✅ render.yaml with 180-sec build timeout
✅ Better build fallback messaging

---

## Success Indicators

✅ **Backend Health**: `/health` returns 200 OK  
✅ **API Works**: `/generate-pil?idx=0` returns full data  
✅ **Display Works**: Page shows severity, priority, topics, entities  
✅ **Console Clean**: No errors, shows diagnostic logs (🚀, 📡, ✅, etc.)  
✅ **Modal Works**: "View & Edit PIL" shows full document  

---

## If Still Having Issues

1. **Screenshot console logs** (F12 → Console → Ctrl+A → Take screenshot)
2. **Share Render logs** (Dashboard → Logs → Last 50 lines)
3. **Note what appears/doesn't appear** on page
4. **Share API response** (copy from render-test.html Test 2)

Then we can debug further! 🔍
