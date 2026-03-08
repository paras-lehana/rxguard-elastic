// ══════════════════════════════════════════════════════════════════════════════
//  Jan Aushadhi Hub — Frontend Logic (Phase R9 Agentic RAG Pipeline)
// ══════════════════════════════════════════════════════════════════════════════
//
// The backend now returns curated HTML tables directly (via LLM → KB → LLM
// pipeline).  This JS file simply:
//   1. Handles tab switching  (Find Alternatives / Find a Kendra)
//   2. Sends the user query to /api/janaushadhi/query
//   3. Injects the returned HTML directly into the results container
//
// No client-side JSON parsing or card-building needed — the LLM does it all.
// ══════════════════════════════════════════════════════════════════════════════


// ── Inject table styling for LLM-generated tables ───────────────────────────
(function injectJaTableStyles() {
    if (document.getElementById('ja-table-styles')) return;
    const style = document.createElement('style');
    style.id = 'ja-table-styles';
    style.textContent = `
        /* Jan Aushadhi LLM-generated table styles */
        #jaMedResults table, #jaLocResults table {
            width: 100%;
            border-collapse: collapse;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin: 1rem 0;
            font-size: 0.9rem;
        }
        #jaMedResults th, #jaLocResults th {
            background: #10b981;
            color: white;
            padding: 10px 14px;
            text-align: left;
            font-weight: 600;
            font-size: 0.85rem;
            letter-spacing: 0.3px;
        }
        #jaMedResults td, #jaLocResults td {
            padding: 8px 14px;
            border-bottom: 1px solid #e5e7eb;
            color: var(--text-primary, #1f2937);
            vertical-align: top;
        }
        #jaMedResults tr:nth-child(even), #jaLocResults tr:nth-child(even) {
            background: #f0fdf4;
        }
        #jaMedResults tr:hover, #jaLocResults tr:hover {
            background: #dcfce7;
            transition: background 0.2s;
        }
        #jaMedResults a, #jaLocResults a {
            color: #10b981;
            text-decoration: none;
            font-weight: 600;
        }
        #jaMedResults a:hover, #jaLocResults a:hover {
            text-decoration: underline;
        }
        #jaMedResults p, #jaLocResults p {
            color: var(--text-secondary, #6b7280);
            line-height: 1.6;
            margin: 0.5rem 0;
        }
        /* Dark mode overrides */
        @media (prefers-color-scheme: dark) {
            #jaMedResults td, #jaLocResults td {
                color: var(--text-primary, #f3f4f6);
            }
            #jaMedResults tr:nth-child(even), #jaLocResults tr:nth-child(even) {
                background: rgba(16, 185, 129, 0.08);
            }
            #jaMedResults tr:hover, #jaLocResults tr:hover {
                background: rgba(16, 185, 129, 0.15);
            }
        }
    `;
    document.head.appendChild(style);
})();


// ── Tab Switching ───────────────────────────────────────────────────────────

window.switchJaTab = function(tab) {
    const btnAlt = document.getElementById('jaTabBtnAlt');
    const btnLoc = document.getElementById('jaTabBtnLoc');
    const tabAlt = document.getElementById('jaTabAlt');
    const tabLoc = document.getElementById('jaTabLoc');

    if (!btnAlt || !btnLoc || !tabAlt || !tabLoc) return;

    if (tab === 'alt') {
        btnAlt.classList.add('active');
        btnAlt.style.borderBottomColor = 'var(--primary-color)';
        btnAlt.style.color = 'var(--primary-color)';

        btnLoc.classList.remove('active');
        btnLoc.style.borderBottomColor = 'transparent';
        btnLoc.style.color = 'var(--text-secondary)';

        tabAlt.style.display = 'block';
        tabLoc.style.display = 'none';
    } else {
        btnLoc.classList.add('active');
        btnLoc.style.borderBottomColor = 'var(--primary-color)';
        btnLoc.style.color = 'var(--primary-color)';

        btnAlt.classList.remove('active');
        btnAlt.style.borderBottomColor = 'transparent';
        btnAlt.style.color = 'var(--text-secondary)';

        tabAlt.style.display = 'none';
        tabLoc.style.display = 'block';
    }
};


// ── Search Query Handler ────────────────────────────────────────────────────

window.searchJaQuery = async function(type) {
    let input, resultsContainer, btn;
    if (type === 'medicine_alternative') {
        input = document.getElementById('jaMedInput');
        resultsContainer = document.getElementById('jaMedResults');
        btn = document.getElementById('jaMedSearchBtn');
    } else {
        input = document.getElementById('jaLocInput');
        resultsContainer = document.getElementById('jaLocResults');
        btn = document.getElementById('jaLocSearchBtn');
    }

    const query = input ? input.value.trim() : '';
    if (!query) {
        if (window.showToast) window.showToast("Please enter a value.", "warning");
        return;
    }

    // ── Loading state ───────────────────────────────────────────
    const loadingLabel = type === 'medicine_alternative'
        ? 'Identifying generic salts and searching Knowledge Base...'
        : 'Searching Jan Aushadhi Kendra directory...';

    resultsContainer.innerHTML = `
        <div style="text-align:center; padding:2.5rem 1rem; background:var(--bg-surface); border-radius:8px; border:1px solid var(--border-color);">
            <div style="margin:0 auto 1rem; width:28px; height:28px; border:3px solid #10b981; border-top-color:transparent; border-radius:50%; animation:spin 1s linear infinite;"></div>
            <p style="color:var(--text-secondary); margin:0 0 0.25rem; font-weight:500;">${loadingLabel}</p>
            <p style="color:var(--text-tertiary, #9ca3af); margin:0; font-size:0.8rem;">This may take 10-15 seconds (LLM + Knowledge Base pipeline)</p>
        </div>
    `;
    btn.disabled = true;
    btn.textContent = 'Searching...';

    try {
        // ── API Call ────────────────────────────────────────────
        const response = await fetch('/api/janaushadhi/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, type: type })
        });

        let data;
        try {
            data = await response.json();
        } catch (e) {
            throw new Error("Server did not return valid JSON. The service may be restarting.");
        }

        if (!data.success) throw new Error(data.error || 'API Error');

        // ── Render HTML response from LLM pipeline ─────────────
        if (data.html && data.html.trim().length > 0) {
            // New pipeline: LLM returns curated HTML with styled tables
            resultsContainer.innerHTML = data.html;
        } else {
            // No results at all
            resultsContainer.innerHTML = `
                <div style="text-align:center; padding:2rem; background:var(--bg-surface); border:1px dashed var(--border-color); border-radius:8px;">
                    <div style="font-size:2rem; margin-bottom:0.5rem;">🔍</div>
                    <h4 style="margin:0 0 0.5rem; color:var(--text-primary);">No Results Found</h4>
                    <p style="color:var(--text-secondary); font-size:0.9rem; margin:0;">We could not find relevant information. Try adjusting your search term.</p>
                </div>
            `;
        }

    } catch (err) {
        console.error('[JanAushadhi] Search error:', err);
        resultsContainer.innerHTML = `
            <div style="background:#fee2e2; border:1px solid #f87171; border-radius:8px; padding:1.25rem; color:#b91c1c;">
                <strong style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;">⚠️ Search Failed</strong>
                <span style="font-size:0.9rem;">${err.message}</span>
            </div>
        `;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Search';
    }
};
