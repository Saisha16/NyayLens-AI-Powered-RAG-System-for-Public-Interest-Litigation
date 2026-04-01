// Resolve API base once so we can override without editing code
// Auto-detect: use same hostname for production, localhost:8001 for local dev
const DEFAULT_API_URL = (() => {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
        return 'http://localhost:8001'; // Local development
    }
    // Production: use https with current hostname (e.g., nyaylens-backend.onrender.com)
    return 'https://' + host;
})();
function resolveApiBase() {
    const fromStorage = localStorage.getItem("api_base_url");
    const fromGlobal = typeof window !== "undefined" && window.API_URL ? window.API_URL : null;
    const base = (fromStorage || fromGlobal || DEFAULT_API_URL || "").replace(/\/+$/, "");
    return base || DEFAULT_API_URL;
}
const API_URL = resolveApiBase();
let statusEl, newsSelect, topicSelect, excerptEl;
let newsItems = [];
let authToken = localStorage.getItem("auth_token") || "";
let currentDraftId = null; // Store current draft ID for editing

function setStatus(msg, type = "info") {
    if (!statusEl) return;
    statusEl.textContent = msg;
    statusEl.className = `status ${type}`;
}

async function loadTopics() {
    try {
        const res = await fetch(`${API_URL}/topics`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const topics = data.topics || [];
        topicSelect.innerHTML = "";
        const allOpt = document.createElement("option");
        allOpt.value = "";
        allOpt.textContent = "All topics";
        topicSelect.appendChild(allOpt);
        topics.forEach(t => {
            const opt = document.createElement("option");
            opt.value = t;
            opt.textContent = t.replace(/_/g, " ");
            topicSelect.appendChild(opt);
        });
    } catch (err) {
        console.error("loadTopics error", err);
    }
}

function updateDateInput() {
    const filterType = document.getElementById("dateFilterType").value;
    const dateInputGroup = document.getElementById("dateInputGroup");
    const dateFilter = document.getElementById("dateFilter");
    const dateFilterEnd = document.getElementById("dateFilterEnd");
    const dateInputLabel = document.getElementById("dateInputLabel");
    
    if (filterType === "all") {
        dateInputGroup.style.display = "none";
        dateFilter.value = "";
        dateFilterEnd.value = "";
    } else {
        dateInputGroup.style.display = "block";
        dateFilterEnd.style.display = "none";
        
        if (filterType === "year") {
            dateInputLabel.textContent = "Year:";
            dateFilter.type = "number";
            dateFilter.placeholder = "YYYY (e.g., 2025)";
            dateFilter.min = "2020";
            dateFilter.max = "2030";
            dateFilter.value = new Date().getFullYear();
        } else if (filterType === "month") {
            dateInputLabel.textContent = "Month:";
            dateFilter.type = "month";
            dateFilter.placeholder = "YYYY-MM";
            dateFilter.value = new Date().toISOString().substring(0, 7);
        } else if (filterType === "date") {
            dateInputLabel.textContent = "Date:";
            dateFilter.type = "date";
            dateFilter.placeholder = "YYYY-MM-DD";
            dateFilter.value = new Date().toISOString().split('T')[0];
        } else if (filterType === "range") {
            dateInputLabel.textContent = "From:";
            dateFilter.type = "date";
            dateFilter.placeholder = "Start Date";
            dateFilterEnd.style.display = "inline-block";
            dateFilterEnd.placeholder = "End Date";
        }
    }
}

async function loadNews() {
    if (!newsSelect) {
        console.error("newsSelect not initialized");
        return;
    }
    
    const topicVal = topicSelect ? topicSelect.value || "" : "";
    const filterType = document.getElementById("dateFilterType").value;
    const dateVal = document.getElementById("dateFilter").value || "";
    const dateEndVal = document.getElementById("dateFilterEnd").value || "";
    
    let queryParams = [];
    if (topicVal) queryParams.push(`topic=${encodeURIComponent(topicVal)}`);
    
    // Handle different date filter types
    if (filterType !== "all" && dateVal) {
        if (filterType === "range" && dateEndVal) {
            queryParams.push(`date_from=${encodeURIComponent(dateVal)}`);
            queryParams.push(`date_to=${encodeURIComponent(dateEndVal)}`);
        } else {
            queryParams.push(`date=${encodeURIComponent(dateVal)}`);
        }
    }
    
    const queryString = queryParams.length > 0 ? "?" + queryParams.join("&") : "";
    
    setStatus("Loading news...", "info");
    console.log(`Fetching: ${API_URL}/news${queryString}`);
    try {
        const headers = authToken ? {"Authorization": `Bearer ${authToken}`} : {};
        const res = await fetch(`${API_URL}/news${queryString}`, { headers });
        console.log(`Response status: ${res.status}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        const data = await res.json();
        newsItems = data.items || [];
    console.log(`Loaded ${newsItems.length} news items`);

        newsSelect.innerHTML = "";
        newsItems.forEach(item => {
            const opt = document.createElement("option");
            opt.value = item.index;
            const dateStr = item.published ? ` (${item.published.split('T')[0]})` : "";
            opt.textContent = (item.title || `Article ${item.index}`) + dateStr;
            newsSelect.appendChild(opt);
        });

        if (newsItems.length === 0) {
            setStatus("No news available. Run ingest or change filters.", "error");
            excerptEl.textContent = "—";
            return;
        }

        // Auto-load first article
        newsSelect.value = newsItems[0].index;
        displayNewsArticle(newsItems[0].index);
        
        // Attach event listener after populating
        attachNewsSelectListener();
        
        setStatus(`Loaded ${newsItems.length} articles. Select one to view details.`, "success");
    } catch (err) {
        console.error("loadNews error:", err);
        console.error("Error stack:", err.stack);
        setStatus("Failed to load news: " + err.message + " — ensure backend at " + API_URL + " is running", "error");
    }
}

function displayNewsArticle(idx) {
    console.log("displayNewsArticle called with idx:", idx);
    console.log("newsItems length:", newsItems.length);
    console.log("newsItems indices:", newsItems.map(n => n.index));

    // Prefer matching by index field; fallback to positional index if needed
    let item = newsItems.find(n => String(n.index) === String(idx));
    if (!item && !Number.isNaN(Number(idx))) {
        item = newsItems[Number(idx)];
    }
    if (!item) {
        console.error("Article not found with index:", idx);
        return;
    }

    console.log("Found article:", item.title);
    
    document.getElementById("newsTitle").innerText = item.title || "No title";
    
    // Display summary in the summary div
    const summaryDiv = document.getElementById("summary");
    if (summaryDiv) {
        summaryDiv.innerHTML = `<h4>📰 Summary</h4><p>${item.summary || item.excerpt || "No summary available"}</p>`;
    }
    
    // Display elaborated facts
    const factsDiv = document.getElementById("elaboratedFacts");
    if (factsDiv) {
        factsDiv.innerHTML = elaborateFacts(item);
    }
    
    excerptEl.textContent = item.excerpt || "—";
    document.getElementById("articleSource").innerText = `📰 ${item.source || "Unknown"}`;
    document.getElementById("articleDate").innerText = `📅 ${item.published || "Date unknown"}`;
    
    // Reset severity/priority displays until PIL is generated for this article
    document.getElementById("severityScore").innerText = "—";
    const priority = document.getElementById("priorityLevel");
    priority.innerText = "—";
    priority.className = "";
    
    // Clear entity list until PIL generated
    document.getElementById("entityList").innerHTML = "";
    
    // Clear current draft since article changed
    currentDraftId = null;
    
    setStatus("Article loaded. Click 'Generate PIL' to analyze.", "info");
}

function elaborateFacts(article) {
    // Generate elaborated facts from article content
    // Use text field first, then fallback to summary/excerpt
    const fullText = article.text || article.summary || article.excerpt || "";
    const entities = article.topics || [];
    
    if (!fullText || fullText.length < 10) {
        return `<p style="color: #666; font-style: italic;">No detailed text available for this article.</p>`;
    }
    
    // Break text into sentences for better readability
    const sentences = fullText
        .split(/[.!?]+/)
        .map(s => s.trim())
        .filter(s => s.length > 20);
    
    if (sentences.length === 0) {
        return `<p style="color: #666; font-style: italic;">Unable to extract detailed facts.</p>`;
    }
    
    // Build formatted HTML output
    let html = `<h4>🔍 Elaborated Facts</h4>`;
    html += `<div style="margin-bottom: 10px; font-size: 0.9em; color: #666;">`;
    html += `<strong>Source:</strong> ${article.source || "Unknown"} | `;
    html += `<strong>Published:</strong> ${article.published || "Unknown"}<br>`;
    html += `<strong>Topics:</strong> ${entities.join(", ") || "General"} | `;
    html += `<strong>Content Length:</strong> ${fullText.length} characters`;
    html += `</div>`;

    html += `<ul style="list-style: none; padding-left: 0;">`;
    sentences.slice(0, 5).forEach((sentence, i) => {
        html += `<li style="margin-bottom: 12px; padding-left: 20px; border-left: 3px solid #ff6600;">`;
        html += `<strong>Fact ${i + 1}:</strong> ${sentence}.`;
        html += `</li>`;
    });
    html += `</ul>`;
    
    return html;
}

async function submitCustomArticle() {
    const summary = document.getElementById("customSummary").value.trim();
    const details = document.getElementById("customDetails").value.trim();
    const title = document.getElementById("customArticleTitle").value.trim();
    const source = document.getElementById("customSource").value.trim();
    const topicsRaw = document.getElementById("customTopics").value.trim();
    
    // Validation
    if (!summary || summary.length < 10) {
        setStatus("Case summary is required (min 10 characters)", "error");
        return;
    }
    
    if (summary.length > 8000) {
        setStatus("Case summary is too long (max 8000 characters)", "error");
        return;
    }
    
    if (details && details.length > 12000) {
        setStatus("Full details is too long (max 12000 characters)", "error");
        return;
    }
    
    // Parse topics
    const topics = topicsRaw
        .split(",")
        .map(t => t.trim().toLowerCase().replace(/\s+/g, "_"))
        .filter(t => t.length > 0 && /^[a-z0-9_-]+$/.test(t));
    
    setStatus("Generating PIL from custom submission...", "info");
    
    try {
        const payload = {
            article_summary: summary,
            article_text: details || null,
            title: title || "Custom Submission",
            source: source || "User Submission",
            topics: topics.length > 0 ? topics : ["general"]
        };
        
        const headers = {
            "Content-Type": "application/json",
            ...(authToken ? {"Authorization": `Bearer ${authToken}`} : {})
        };
        
        const res = await fetch(`${API_URL}/generate-pil`, {
            method: "POST",
            headers,
            body: JSON.stringify(payload)
        });
        
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        
        const data = await res.json();
        
        // Update UI with generated PIL
        document.getElementById("newsTitle").innerText = title || "Generated PIL";
        document.getElementById("summary").innerText = summary;
        document.getElementById("elaboratedFacts").innerHTML = `<p>${details || summary}</p>`;
        document.getElementById("articleSource").innerText = `📰 ${source || "Custom"}`;
        document.getElementById("articleDate").innerText = `📅 ${new Date().toLocaleDateString()}`;
        
        document.getElementById("severityScore").innerText = `${data.severity_score || "—"} / 10`;
        const priority = document.getElementById("priorityLevel");
        priority.innerText = data.priority_level || "MEDIUM";
        priority.className = data.priority_level || "MEDIUM";
        
        const entityList = document.getElementById("entityList");
        entityList.innerHTML = "";
        (data.entities_detected || []).forEach(ent => {
            const li = document.createElement("li");
            li.innerText = ent;
            entityList.appendChild(li);
        });
        
        // Store draft ID
        if (data.draft_id) {
            currentDraftId = data.draft_id;
            console.log("Custom PIL Draft created:", currentDraftId);
        }
        
        setStatus("✓ Custom PIL generated! Click 'View & Edit PIL' to customize.", "success");
        
        // Clear form
        document.getElementById("customSummary").value = "";
        document.getElementById("customDetails").value = "";
        document.getElementById("customArticleTitle").value = "";
        document.getElementById("customSource").value = "";
        document.getElementById("customTopics").value = "";
        
        // Switch back to URL tab
        document.querySelectorAll('.input-tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelector('[data-mode="url"]').classList.add('active');
        document.getElementById('urlMode').classList.add('active');
        document.getElementById('textMode').classList.remove('active');
        
    } catch (err) {
        console.error("submitCustomArticle error", err);
        setStatus("Failed to generate PIL: " + err.message, "error");
    }
}

// Generate PIL for the selected news item
async function generatePIL(idx = null, auto = false) {
    const selIdx = idx !== null ? idx : Number(newsSelect.value || 0);
    const topicVal = topicSelect.value || "";
    const topicParam = topicVal ? `&topic=${encodeURIComponent(topicVal)}` : "";
    setStatus(auto ? "Loading PIL..." : "Generating PIL...", "info");
    try {
        const headers = authToken ? {"Authorization": `Bearer ${authToken}`} : {};
        const response = await fetch(`${API_URL}/generate-pil?idx=${selIdx}${topicParam}`, { headers });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();

        document.getElementById("newsTitle").innerText = data.news_title || "No title";
        
        // Display severity score - show as score/10 format
        const severityEl = document.getElementById("severityScore");
        if (severityEl) {
            severityEl.innerText = typeof data.severity_score === 'number' 
                ? (data.severity_score * 10).toFixed(1) + " / 10" 
                : "—";
        }

        // Display summary/excerpt
        excerptEl.textContent = data.summary || data.excerpt || "—";
        if (data.news_index !== undefined) {
            newsSelect.value = data.news_index;
        }

        // Display priority level with color coding
        const priority = document.getElementById("priorityLevel");
        priority.innerText = data.priority_level || "—";
        priority.className = (data.priority_level || "").toUpperCase();

        // Display topics
        const topicsEl = document.querySelector('[data-topics]') || document.getElementById("topics");
        if (topicsEl && data.topics && data.topics.length > 0) {
            topicsEl.innerText = data.topics.join(", ");
        }

        // Display extracted entities
        const entityList = document.getElementById("entityList");
        entityList.innerHTML = "";
        // Support both 'entities' and 'entities_detected' field names
        const entityArray = data.entities || data.entities_detected || [];
        entityArray.forEach(ent => {
            const li = document.createElement("li");
            li.innerText = ent;
            entityList.appendChild(li);
        });

        // Store draft ID for later use
        if (data.draft_id) {
            currentDraftId = data.draft_id;
            console.log("Draft created:", currentDraftId);
        }

        // Display legal sources with relevance
        if (data.legal_sources_used) {
            console.log("Legal sources:", data.legal_sources_used);
        }

        setStatus("PIL Generated! Click 'View & Edit PIL' to customize.", "success");
    } catch (err) {
        console.error("generatePIL error", err);
        setStatus("Backend unreachable or error: " + err.message, "error");
    }
}

// PIL View/Edit Functions
async function viewPil() {
    if (!currentDraftId) {
        setStatus("Generate a PIL first!", "error");
        return;
    }
    
    setStatus("Loading PIL draft...", "info");
    try {
        const headers = authToken ? {"Authorization": `Bearer ${authToken}`} : {};
        const res = await fetch(`${API_URL}/view-pil?draft_id=${currentDraftId}`, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        const draft = await res.json();
        if (draft.error) {
            setStatus(draft.error, "error");
            return;
        }
        
        // Populate preview
        displayPilPreview(draft);
        
        // Populate edit form
        document.getElementById("editFacts").value = draft.facts_of_case || "";
        document.getElementById("editRights").value = (draft.fundamental_rights || []).join("\n");
        document.getElementById("editPrinciples").value = (draft.directive_principles || []).join("\n");
        document.getElementById("editCases").value = (draft.case_precedents || []).join("\n");
        document.getElementById("editPrayer").value = draft.prayer_relief || "";
        
        // Show modal
        document.getElementById("pilModal").style.display = "block";
        setStatus("PIL loaded. You can now view or edit.", "success");
    } catch (err) {
        console.error("viewPil error", err);
        setStatus("Failed to load PIL: " + err.message, "error");
    }
}

function displayPilPreview(draft) {
    const preview = `
<div class="pil-header">
    <h3>${draft.news_title}</h3>
    <p><strong>Severity:</strong> ${draft.priority_level} (${draft.severity_score})</p>
    <p><strong>Last Updated:</strong> ${new Date(draft.updated_at).toLocaleString()}</p>
</div>

<div class="pil-section">
    <h4>Facts of the Case</h4>
    <p>${draft.facts_of_case}</p>
</div>

<div class="pil-section">
    <h4>Fundamental Rights Violated</h4>
    <ul>
        ${draft.fundamental_rights.map(r => `<li>${r}</li>`).join('')}
    </ul>
</div>

<div class="pil-section">
    <h4>Directive Principles</h4>
    <ul>
        ${draft.directive_principles.map(p => `<li>${p}</li>`).join('')}
    </ul>
</div>

<div class="pil-section">
    <h4>Case Precedents</h4>
    <ul>
        ${draft.case_precedents.map(c => `<li>${c}</li>`).join('')}
    </ul>
</div>

<div class="pil-section">
    <h4>Prayer for Relief</h4>
    <p>${draft.prayer_relief}</p>
</div>

<div class="pil-footer">
    <small>Draft ID: ${draft.id}</small>
</div>
    `;
    
    document.getElementById("pilPreview").innerHTML = preview;
}

function switchTab(tabName, evt) {
    // Hide all tabs
    document.getElementById("previewTab").classList.remove("active");
    document.getElementById("editTab").classList.remove("active");
    const explainTab = document.getElementById("explainabilityTab");
    if (explainTab) explainTab.classList.remove("active");
    
    // Remove active class from all buttons
    document.querySelectorAll(".tab-button").forEach(btn => btn.classList.remove("active"));
    
    // Show selected tab
    if (tabName === "preview") {
        document.getElementById("previewTab").classList.add("active");
    } else if (tabName === "edit") {
        document.getElementById("editTab").classList.add("active");
    } else if (tabName === "explainability") {
        if (explainTab) explainTab.classList.add("active");
    }
    
    // Add active class to clicked button
    if (evt && evt.target) {
        evt.target.classList.add("active");
    } else {
        // Fallback: find and activate the corresponding button
        const buttons = document.querySelectorAll(".tab-button");
        buttons.forEach(btn => {
            const btnText = btn.textContent.toLowerCase();
            if ((tabName === "preview" && btnText.includes("preview")) ||
                (tabName === "edit" && btnText.includes("edit")) ||
                (tabName === "explainability" && btnText.includes("analysis"))) {
                btn.classList.add("active");
            }
        });
    }
}

function switchTabUI(tabName) {
    // Hide all tabs
    const tabs = document.querySelectorAll(".tab-content");
    tabs.forEach(tab => tab.classList.remove("active"));
    
    // Show selected tab
    const tabElement = document.getElementById(tabName + "Tab");
    if (tabElement) {
        tabElement.classList.add("active");
    }
    
    // Update buttons
    const buttons = document.querySelectorAll(".tab-button");
    buttons.forEach(btn => btn.classList.remove("active"));
    
    const activeBtn = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeBtn) {
        activeBtn.classList.add("active");
    }
}

async function savePilEdits() {
    if (!currentDraftId) return;
    
    setStatus("Saving edits...", "info");
    try {
        const updates = {
            facts_of_case: document.getElementById("editFacts").value,
            fundamental_rights: document.getElementById("editRights").value.split("\n").filter(l => l.trim()),
            directive_principles: document.getElementById("editPrinciples").value.split("\n").filter(l => l.trim()),
            case_precedents: document.getElementById("editCases").value.split("\n").filter(l => l.trim()),
            prayer_relief: document.getElementById("editPrayer").value
        };
        
        const headers = {
            "Content-Type": "application/json",
            ...(authToken ? {"Authorization": `Bearer ${authToken}`} : {})
        };
        
        const res = await fetch(`${API_URL}/edit-pil?draft_id=${currentDraftId}`, {
            method: "POST",
            headers,
            body: JSON.stringify(updates)
        });
        
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        const data = await res.json();
        if (data.success) {
            // Update preview
            displayPilPreview(data.draft);
            setStatus("Edits saved successfully!", "success");
            switchTab("preview");
        } else {
            setStatus("Failed to save: " + data.error, "error");
        }
    } catch (err) {
        console.error("savePilEdits error", err);
        setStatus("Error saving edits: " + err.message, "error");
    }
}

function downloadPilPdf() {
    if (!currentDraftId) {
        setStatus("Generate a PIL first!", "error");
        return;
    }
    
    setStatus("Generating PDF...", "info");
    window.location.href = `${API_URL}/download-pil?draft_id=${currentDraftId}`;
}

function downloadPDF() {
    if (!currentDraftId) {
        setStatus("Generate a PIL first!", "error");
        return;
    }
    
    setStatus("Downloading PDF...", "info");
    window.location.href = `${API_URL}/download-pil?draft_id=${currentDraftId}`;
}

function closePilModal() {
    const modal = document.getElementById("pilModal");
    if (modal) {
        modal.style.display = "none";
    }
}

// Debounce utility
function debounce(func, delay = 100) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delay);
    };
}

// Show explainability analysis
async function showExplainability() {
    if (!currentDraftId) {
        setStatus("Generate a PIL first!", "error");
        return;
    }
    
    setStatus("Loading AI analysis...", "info");
    try {
        const headers = authToken ? {"Authorization": `Bearer ${authToken}`} : {};
        
        // Fetch explainability data from backend
        const res = await fetch(`${API_URL}/explain-pil?draft_id=${currentDraftId}`, { headers });
        
        if (!res.ok) {
            console.log("Explainability endpoint returned:", res.status);
            throw new Error(`HTTP ${res.status}`);
        }
        
        const explainData = await res.json();
        console.log("Explainability data:", explainData);
        
        // Display modal with explainability tab
        document.getElementById("pilModal").style.display = "block";
        displayExplainability(explainData);
        switchTab("explainability");
        setStatus("AI reasoning loaded.", "success");
    } catch (err) {
        console.error("showExplainability error", err);
        // Fallback: show generic explainability
        document.getElementById("pilModal").style.display = "block";
        displayDefaultExplainability();
        switchTab("explainability");
        setStatus("Using default AI analysis (backend unavailable).", "info");
    }
}

function displayExplainability(data) {
    const container = document.getElementById("explainabilityContent");
    
    if (!data || Object.keys(data).length === 0) {
        displayDefaultExplainability();
        return;
    }
    
    const formatKeywordItem = (item) => {
        if (!item) return "";
        if (typeof item === "string" || typeof item === "number") return String(item);
        const candidate = item.keyword || item.word || item.term || item.label;
        return candidate || JSON.stringify(item);
    };
    const formatKeywords = (list) => {
        if (!Array.isArray(list)) return "";
        return list.map(formatKeywordItem).filter(Boolean).join(", ");
    };
    const formatMultipliers = (multipliers) => {
        if (!multipliers) return "";
        if (Array.isArray(multipliers)) {
            return multipliers
                .map(m => {
                    if (!m) return "";
                    if (typeof m === "string") return m;
                    const name = m.name || m.key || m.factor || "factor";
                    const val = m.multiplier || m.value || "";
                    return `${name}: ${val}`;
                })
                .filter(Boolean)
                .join("; ");
        }
        return Object.entries(multipliers).map(([k, v]) => `${k}: ${v}`).join("; ");
    };
    
    let html = `<h4>🤖 AI Analysis & Reasoning</h4>`;
    
    // Severity Analysis
    if (data.severity_analysis) {
        const sev = data.severity_analysis;
        const keywords = formatKeywords(sev.keywords_found || []);
        const multipliers = formatMultipliers(sev.multipliers);
        const urgency = sev.urgency_assessment ? `<p><strong>Urgency:</strong> ${sev.urgency_assessment}</p>` : "";
        const extra = [];
        if (sev.key_violations && sev.key_violations.length) extra.push(`<p><strong>Key Violations:</strong> ${sev.key_violations.join(', ')}</p>`);
        if (sev.constitutional_concerns && sev.constitutional_concerns.length) extra.push(`<p><strong>Constitutional Concerns:</strong> ${sev.constitutional_concerns.join(', ')}</p>`);
        if (sev.vulnerable_groups && sev.vulnerable_groups.length) extra.push(`<p><strong>Vulnerable Groups:</strong> ${sev.vulnerable_groups.join(', ')}</p>`);
        html += `
<div class="analysis-section">
    <h5>📊 Severity Assessment ${sev.ai_powered ? '<span class="pill pill-green">AI</span>' : ''}</h5>
    <p><strong>Score:</strong> ${(Number(sev.score) || 0).toFixed(2)} / 1.0</p>
    <p><strong>Priority:</strong> ${sev.priority || "N/A"}</p>
    <p><strong>Confidence:</strong> ${sev.confidence || "N/A"}</p>
    ${keywords ? `<p><strong>Keywords Found:</strong> ${keywords}</p>` : ''}
    ${multipliers ? `<p><strong>Multipliers:</strong> ${multipliers}</p>` : ''}
    ${urgency}
    ${extra.join("\n")}
    <div style="margin-top: 10px; padding: 10px; background: #0f172a; border-radius: 4px;">
        <strong>Reasoning:</strong>
        <p>${sev.reasoning || "Based on keyword analysis and context"}</p>
    </div>
</div>
        `;
    }
    
    // Entity Analysis
    if (data.entity_extraction) {
        const ent = data.entity_extraction;
        html += `
<div class="analysis-section">
    <h5>🏛️ Key Parties Identified</h5>
    <p><strong>Total Entities:</strong> ${ent.entities_found || 0}</p>
    <p><strong>Key Parties:</strong></p>
    <ul>${(ent.key_parties || []).map(p => `<li>${p}</li>`).join("")}</ul>
    <p>${ent.explanation || "Entities extracted from article text"}</p>
</div>
        `;
    }
    
    // Legal References
    if (data.legal_references) {
        const leg = data.legal_references;
        html += `
<div class="analysis-section">
    <h5>⚖️ Constitutional & Legal Grounds ${leg.ai_powered ? '<span class="pill pill-green">AI</span>' : ''}</h5>
    <p><strong>Total References Selected:</strong> ${leg.total_selected || 0}</p>
    <p><strong>Primary Articles:</strong></p>
    <ul>${(leg.primary_articles || []).map(a => `<li>${a}</li>`).join("")}</ul>
    ${leg.primary_grounds && leg.primary_grounds.length ? `<p><strong>Primary Grounds:</strong></p><ul>${leg.primary_grounds.map(g => `<li>${g}</li>`).join('')}</ul>` : ''}
    ${leg.filing_strategy ? `<p><strong>Filing Strategy:</strong> ${leg.filing_strategy}</p>` : ''}
    <p>${leg.explanation || "Legal references based on article topics"}</p>
</div>
        `;
    }
    
    // PIL Viability
    if (data.pil_viability) {
        const viab = data.pil_viability;
        html += `
<div class="analysis-section">
    <h5>✅ PIL Filing Viability ${viab.ai_powered ? '<span class="pill pill-green">AI</span>' : ''}</h5>
    <p><strong>Suitable for PIL:</strong> ${viab.suitable_for_pil ? "✓ YES" : "✗ Needs further investigation"}</p>
    <p><strong>Recommendation:</strong> ${viab.recommendation || "Analyze further"}</p>
    ${viab.viability_rating ? `<p><strong>Viability Rating:</strong> ${viab.viability_rating}</p>` : ''}
    ${viab.timeline_urgency ? `<p><strong>Timeline Urgency:</strong> ${viab.timeline_urgency}</p>` : ''}
    ${viab.strengths && viab.strengths.length ? `<p><strong>Strengths:</strong></p><ul>${viab.strengths.map(s => `<li>${s}</li>`).join('')}</ul>` : ''}
    ${viab.challenges && viab.challenges.length ? `<p><strong>Challenges:</strong></p><ul>${viab.challenges.map(c => `<li>${c}</li>`).join('')}</ul>` : ''}
    <p><strong>Next Steps:</strong></p>
    <ol>${(viab.next_steps || []).map(s => `<li>${s}</li>`).join("")}</ol>
</div>
        `;
    }
    
    if (html === `<h4>🤖 AI Analysis & Reasoning</h4>`) {
        displayDefaultExplainability();
        return;
    }
    
    container.innerHTML = html;
}

function displayDefaultExplainability() {
    const content = `
<h4>📊 AI Analysis & Reasoning</h4>
<p>This feature uses explainable AI to show you:</p>
<ul>
    <li><strong>Severity Assessment:</strong> Why the AI rated this issue at the given severity level</li>
    <li><strong>Entity Recognition:</strong> Who are the key parties involved and their roles</li>
    <li><strong>Legal Grounds:</strong> Which constitutional articles and principles apply</li>
    <li><strong>PIL Viability:</strong> Whether this case is suitable for Public Interest Litigation</li>
</ul>
<p style="margin-top: 20px; padding: 10px; background: #f0f0f0; border-left: 4px solid #ff6b6b;">
    <strong>How to Use:</strong> Generate a PIL first, then click "🤖 AI Reasoning" to see the AI's decision-making process. This helps you understand why certain legal provisions were selected and whether the case meets PIL criteria.
</p>
    `;
    document.getElementById("explainabilityContent").innerHTML = content;
}

// Close modal when clicking outside of it
window.addEventListener('click', function(event) {
    const modal = document.getElementById("pilModal");
    if (modal && event.target === modal) {
        modal.style.display = "none";
    }
});

async function addCustomNews() {
    const urlInput = document.getElementById("customUrl");
    const titleInput = document.getElementById("customTitle");
    const url = urlInput.value.trim();
    const title = titleInput.value.trim();

    if (!url) {
        setStatus("Please enter a URL", "error");
        return;
    }

    setStatus("Adding custom article...", "info");
    try {
        const headers = authToken ? {"Authorization": `Bearer ${authToken}`} : {};
        const params = new URLSearchParams({url});
        if (title) params.append("title", title);
        
        const res = await fetch(`${API_URL}/add-custom-news?${params}`, {
            method: "POST",
            headers
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (data.success) {
            setStatus("Article added! Refreshing list...", "success");
            urlInput.value = "";
            titleInput.value = "";
            await loadNews();
        } else {
            setStatus("Failed: " + data.error, "error");
        }
    } catch (err) {
        console.error("addCustomNews error", err);
        setStatus("Error: " + err.message, "error");
    }
}

// Attach event listener to news select
function attachNewsSelectListener() {
    const select = document.getElementById("newsSelect");
    if (select) {
        // Remove old listener if any
        select.onchange = null;
        // Add new listener
        select.onchange = function(e) {
            const idx = Number(e.target.value);
            console.log("Article selected:", idx);
            displayNewsArticle(idx);
        };
    }
}

function initialize() {
    // Initialize DOM element references
    statusEl = document.getElementById("status");
    newsSelect = document.getElementById("newsSelect");
    topicSelect = document.getElementById("topicSelect");
    excerptEl = document.getElementById("excerpt");
    
    console.log("Init: Elements initialized");
    console.log("statusEl:", statusEl ? "✓" : "✗");
    console.log("newsSelect:", newsSelect ? "✓" : "✗");
    console.log("topicSelect:", topicSelect ? "✓" : "✗");
    
    // Initialize date filter to "All Dates" by default
    const dateFilterType = document.getElementById("dateFilterType");
    if (dateFilterType) {
        dateFilterType.value = "all";
        updateDateInput(); // Initialize the UI
    }
    
    // Load initial data
    console.log("Starting initialization...");
    loadTopics().then(() => {
        console.log("Topics loaded, now loading news");
        loadNews();
    }).catch(err => {
        console.error("Initialization failed:", err);
    });
    
    // Topic filter listener
    topicSelect.addEventListener("change", () => {
        console.log("Topic changed");
        loadNews();
    });
    
    // Date filter type listener
    if (dateFilterType) {
        dateFilterType.addEventListener("change", () => {
            console.log("Date filter type changed");
            updateDateInput();
            loadNews();
        });
    }
    
    // Date filter listener - reload news when date changes
    const dateFilter = document.getElementById("dateFilter");
    const dateFilterEnd = document.getElementById("dateFilterEnd");
    if (dateFilter) {
        dateFilter.addEventListener("change", () => {
            console.log("Date filter changed to:", dateFilter.value);
            loadNews();
        });
    }
    if (dateFilterEnd) {
        dateFilterEnd.addEventListener("change", () => {
            console.log("Date end filter changed to:", dateFilterEnd.value);
            loadNews();
        });
    }

    // Robust close handlers for the PIL modal using event delegation
    const modal = document.getElementById("pilModal");
    
    // Event delegation - listen on modal for all button clicks
    if (modal) {
        modal.addEventListener('click', (ev) => {
            const target = ev.target;
            
            // Check if clicked element is a close button
            const isCloseButton = target.classList.contains('close') ||
                                (target.classList.contains('tertiary') && 
                                 (target.textContent.includes('Close') || target.textContent.includes('Cancel')));
            
            // Check if it's a tab switch button
            const switchTabAttr = target.getAttribute('data-switch-tab');
            
            // Check if clicking outside modal content
            const isOutsideClick = target === modal;
            
            if (isCloseButton || isOutsideClick) {
                ev.preventDefault();
                ev.stopPropagation();
                closePilModal();
            } else if (switchTabAttr) {
                ev.preventDefault();
                ev.stopPropagation();
                switchTab(switchTabAttr, ev);
            }
        });
        
        // Remove close button inline handlers
        const closeHandlers = modal.querySelectorAll('[onclick*="closePilModal"]');
        closeHandlers.forEach(node => node.removeAttribute('onclick'));
        
        // Remove switchTab inline handlers
        const switchHandlers = modal.querySelectorAll('[onclick*="switchTab"]');
        switchHandlers.forEach(node => node.removeAttribute('onclick'));
    }
    
    // Setup tab button handlers
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const tabName = this.getAttribute('data-tab');
            if (tabName) {
                switchTab(tabName, e);
                if (tabName === 'explainability') {
                    showExplainability();
                }
            }
        });
    });

    // Escape key closes the modal too
    document.addEventListener('keydown', (ev) => {
        if (ev.key === 'Escape' && modal && modal.style.display === 'block') {
            closePilModal();
        }
    });

    // Attach initial listener
    attachNewsSelectListener();
    
    // Setup custom input tab switching
    const inputTabBtns = document.querySelectorAll('.input-tab-btn');
    inputTabBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const mode = this.getAttribute('data-mode');
            
            // Update active tab button
            inputTabBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Show/hide input modes
            document.getElementById('urlMode').classList.remove('active');
            document.getElementById('textMode').classList.remove('active');
            
            if (mode === 'url') {
                document.getElementById('urlMode').classList.add('active');
            } else if (mode === 'text') {
                document.getElementById('textMode').classList.add('active');
            }
        });
    });
}

// Robust bootstrap: run immediately if DOM already ready, else wait
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}
