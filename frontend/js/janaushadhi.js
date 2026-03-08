// Jan Aushadhi Hub Logic

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
}

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
        if(window.showToast) window.showToast("Please enter a value.", "warning");
        return;
    }
    
    // UI Loading state
    resultsContainer.innerHTML = `
        <div style="text-align:center; padding:2rem; background:var(--bg-surface); border-radius:8px; border:1px solid var(--border-color);">
            <div class="loader" style="margin:0 auto 1rem; width:24px; height:24px; border:3px solid var(--primary-color); border-top-color:transparent; border-radius:50%; animation:spin 1s linear infinite;"></div>
            <p style="color:var(--text-secondary); margin:0;">Analyzing Jan Aushadhi Knowledge Base...</p>
        </div>
    `;
    btn.disabled = true;
    btn.innerHTML = '<span style="opacity:0.5">...</span>';

    try {
        const response = await fetch('/api/janaushadhi/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, type: type })
        });
        
        let data;
        try {
            data = await response.json();
        } catch(e) {
            throw new Error("Server did not return valid JSON. Could be booting up.");
        }
        
        if (!data.success) throw new Error(data.error || 'API Error');
        
        let html = '';
        if (data.data && data.data.length > 0) {
            if (type === 'medicine_alternative') {
                html = `<div style="display:flex; flex-direction:column; gap:1rem;">` + data.data.map(med => `
                    <div style="background:var(--bg-surface); border:1px solid #10b981; border-left:4px solid #10b981; border-radius:8px; padding:1.25rem; box-shadow:0 2px 8px rgba(0,0,0,0.05); transition:transform 0.2s;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
                            <h4 style="margin:0; color:var(--text-primary); font-size:1.1rem; display:flex; align-items:center; gap:0.5rem;">
                                💊 ${med.generic_name || 'Generic Alternative'}
                            </h4>
                            <span style="background:#dcfce7; color:#065f46; padding:0.25rem 0.6rem; border-radius:12px; font-size:0.75rem; font-weight:700;">
                                ${med.savings_percentage || 'Max'}% Saved
                            </span>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; font-size:0.9rem; color:var(--text-secondary);">
                            <div style="background:var(--bg-body); padding:0.5rem; border-radius:4px;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.5px;">Branded (Original)</div>
                                <strong style="color:var(--text-primary);">${med.original_name || query}</strong>
                            </div>
                            <div style="background:var(--bg-body); padding:0.5rem; border-radius:4px;">
                                <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.5px;">Jan Aushadhi Price</div>
                                <strong style="color:var(--primary-color); font-size:1.1rem;">₹${med.mrp || '--'}</strong>
                            </div>
                        </div>
                    </div>
                `).join('') + `</div>`;
            } else {
                html = `<div style="display:flex; flex-direction:column; gap:1rem;">` + data.data.map(loc => {
                    const addrUrl = encodeURIComponent((loc.name || '') + ' ' + (loc.address || '') + ' ' + (loc.pin || ''));
                    return `
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:1.25rem; display:flex; justify-content:space-between; align-items:center; box-shadow:0 2px 8px rgba(0,0,0,0.05); transition:transform 0.2s; gap:1rem;">
                        <div style="flex:1;">
                            <h4 style="margin:0 0 0.5rem 0; color:var(--text-primary); font-size:1rem; display:flex; align-items:center; gap:0.5rem;">
                                📍 ${(loc.name || 'PMBJP Kendra')}
                            </h4>
                            <p style="margin:0; font-size:0.85rem; color:var(--text-secondary); line-height:1.4;">
                                ${loc.address || 'Address unavailable'} 
                                ${loc.pin ? '<br><strong>PIN:</strong> ' + loc.pin : ''}
                            </p>
                        </div>
                        <a href="https://www.google.com/maps/dir/?api=1&destination=${addrUrl}" target="_blank" rel="noopener noreferrer" style="flex-shrink:0; background:var(--primary-color); color:white; padding:0.6rem 1rem; border-radius:6px; text-decoration:none; font-size:0.85rem; font-weight:600; text-align:center; box-shadow:0 2px 4px rgba(0,180,216,0.3); transition:background 0.2s;">
                            🗺️ Directions
                        </a>
                    </div>
                `}).join('') + `</div>`;
            }
        } else {
            html = `<div style="text-align:center; padding:2rem; background:var(--bg-surface); border:1px dashed var(--border-color); border-radius:8px;">
                <div style="font-size:2rem; margin-bottom:0.5rem;">🔍</div>
                <h4 style="margin:0 0 0.5rem; color:var(--text-primary);">No Results Found</h4>
                <p style="color:var(--text-secondary); font-size:0.9rem; margin:0;">We couldn't find a direct match. Try adjusting your search term.</p>
            </div>`;
        }
        
        resultsContainer.innerHTML = html;
        
    } catch (err) {
        console.error(err);
        resultsContainer.innerHTML = `<div style="background:#fee2e2; border:1px solid #f87171; border-radius:8px; padding:1.25rem; color:#b91c1c;">
            <strong style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;">⚠️ Search Failed</strong>
            <span style="font-size:0.9rem;">${err.message}</span>
        </div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Search';
    }
}
