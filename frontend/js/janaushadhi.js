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
    resultsContainer.innerHTML = '<div style="text-align:center; padding:1rem; color:var(--text-secondary);">⏳ Searching Knowledge Base...</div>';
    btn.disabled = true;
    btn.textContent = '...';

    try {
        const response = await fetch('/api/janaushadhi/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, type: type })
        });
        const data = await response.json();
        
        if (!data.success) throw new Error(data.error || 'API Error');
        
        let html = '';
        if (data.data && data.data.length > 0) {
            if (type === 'medicine_alternative') {
                html = data.data.map(med => `
                    <div style="background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:8px; padding:1rem;">
                        <h4 style="margin:0 0 0.5rem 0; color:var(--primary-color);">💊 ${med.generic_name || 'Generic'}</h4>
                        <p style="margin:0; font-size:0.9rem;"><strong>Original:</strong> ${med.original_name || query}</p>
                        <p style="margin:0.25rem 0; font-size:0.9rem;"><strong>MRP:</strong> ₹${med.mrp || 'N/A'}</p>
                        <p style="margin:0; font-size:0.9rem; color: #2e7d32;"><strong>Savings:</strong> ${med.savings_percentage || 'N/A'}%</p>
                    </div>
                `).join('');
            } else {
                html = data.data.map(loc => {
                    const addrUrl = encodeURIComponent((loc.name || '') + ' ' + (loc.address || '') + ' ' + (loc.pin || ''));
                    return `
                    <div style="background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:8px; padding:1rem;">
                        <h4 style="margin:0 0 0.5rem 0;">📍 ${(loc.name || 'Jan Aushadhi Kendra')}</h4>
                        <p style="margin:0 0 0.5rem 0; font-size:0.9rem; color:var(--text-secondary);">${loc.address || 'Address unavailable'} - ${loc.pin || ''}</p>
                        <a href="https://www.google.com/maps/dir/?api=1&destination=${addrUrl}" target="_blank" rel="noopener noreferrer" style="display:inline-block; background:var(--primary-color); color:white; padding:0.4rem 0.8rem; border-radius:4px; text-decoration:none; font-size:0.85rem; font-weight:500;">🗺️ Get Directions</a>
                    </div>
                `}).join('');
            }
        } else {
            html = `<div style="text-align:center; padding:1rem; color:var(--text-secondary);">No results found. (Raw: ${data.raw_response?.substring(0,50)}...)</div>`;
        }
        
        resultsContainer.innerHTML = html;
        
    } catch (err) {
        console.error(err);
        resultsContainer.innerHTML = \`<div style="color:red; padding:1rem;">⚠️ Error: ${err.message}</div>\`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Search';
    }
}