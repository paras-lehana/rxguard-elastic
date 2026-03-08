import re

with open('/root/repo/pharmai_portal/frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

pattern = re.compile(
    r'<!-- ── Jan Aushadhi ── -->\s*<div id="toolPanel-janaushadhi" class="tool-panel" style="display:none">.*?</div>\s*</div>',
    re.DOTALL
)

replacement = """<!-- ── Jan Aushadhi ── -->
  <div id="toolPanel-janaushadhi" class="tool-panel" style="display:none">
    <div class="tool-panel-header">
      <h2>💊 PMBJP Jan Aushadhi</h2>
      <button class="tool-panel-close">✕</button>
    </div>
    
    <div class="ja-tabs" style="display:flex; border-bottom:1px solid var(--border-color); margin-bottom:1.5rem;">
        <button id="jaTabBtnAlt" class="ja-tab-btn active" style="flex:1; padding:0.75rem; background:none; border:none; border-bottom:2px solid var(--primary-color); color:var(--primary-color); font-weight:600; cursor:pointer; transition:all 0.2s;" onclick="switchJaTab('alt')">Find Alternatives</button>
        <button id="jaTabBtnLoc" class="ja-tab-btn" style="flex:1; padding:0.75rem; background:none; border:none; border-bottom:2px solid transparent; color:var(--text-secondary); font-weight:500; cursor:pointer; transition:all 0.2s;" onclick="switchJaTab('loc')">Find a Kendra</button>
    </div>

    <!-- Tab 1: Alternatives -->
    <div id="jaTabAlt" class="ja-tab-content" style="background: var(--bg-surface); padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border-color);">
        <div style="display: flex; align-items:flex-start; gap: 1rem; margin-bottom:1.5rem;">
            <div style="font-size: 2rem; background: rgba(0, 180, 216, 0.1); width: 48px; height: 48px; border-radius: 50%; display: flex; align-items:center; justify-content:center;">₹</div>
            <div>
                <h3 style="margin: 0 0 0.25rem 0; font-size: 1.1rem; color:var(--text-primary);">Save up to 90%</h3>
                <p style="margin: 0; font-size: 0.9rem; color:var(--text-secondary); line-height: 1.4;">Search for any branded medicine to instantly find its exact PMBJP generic equivalent with cost comparisons.</p>
            </div>
        </div>
        
        <div style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem;">
            <input type="text" id="jaMedInput" placeholder="e.g. Augmentin 625..." style="flex:1; padding: 0.75rem 1rem; border: 1px solid var(--border-color); border-radius: 20px; background: var(--bg-body); color: var(--text-primary); font-size: 1rem; outline: none; transition:border 0.2s;">
            <button class="btn-primary" onclick="searchJaQuery('medicine_alternative')" id="jaMedSearchBtn" style="padding: 0.75rem 1.5rem; border-radius: 20px; font-weight: 600;">Search</button>
        </div>
        
        <div id="jaMedResults" style="display:flex; flex-direction:column; gap:1rem;">
            <!-- Placeholder -->
            <div style="text-align:center; padding:2rem; background:var(--bg-body); border-radius:8px; border:1px dashed var(--border-color);">
                <div style="font-size:1.5rem; margin-bottom:0.5rem; opacity:0.5">💊</div>
                <p style="margin:0; font-size:0.9rem; color:var(--text-tertiary);">Your search results will appear here</p>
            </div>
        </div>
    </div>

    <!-- Tab 2: Locate -->
    <div id="jaTabLoc" class="ja-tab-content" style="display:none; background: var(--bg-surface); padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border-color);">
        <div style="display: flex; align-items:flex-start; gap: 1rem; margin-bottom:1.5rem;">
            <div style="font-size: 2rem; background: rgba(0, 180, 216, 0.1); width: 48px; height: 48px; border-radius: 50%; display: flex; align-items:center; justify-content:center;">📍</div>
            <div>
                <h3 style="margin: 0 0 0.25rem 0; font-size: 1.1rem; color:var(--text-primary);">10,000+ Kendras Nationwide</h3>
                <p style="margin: 0; font-size: 0.9rem; color:var(--text-secondary); line-height: 1.4;">Enter your city or state to find the closest officially verified Pradhan Mantri Bhartiya Janaushadhi Pariyojana store.</p>
            </div>
        </div>

        <div style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem;">
            <input type="text" id="jaLocInput" placeholder="e.g. Kerala or New Delhi..." style="flex:1; padding: 0.75rem 1rem; border: 1px solid var(--border-color); border-radius: 20px; background: var(--bg-body); color: var(--text-primary); font-size: 1rem; outline: none; transition:border 0.2s;">
            <button class="btn-primary" onclick="searchJaQuery('kendra_locator')" id="jaLocSearchBtn" style="padding: 0.75rem 1.5rem; border-radius: 20px; font-weight: 600;">Locate</button>
        </div>
        
        <div id="jaLocResults" style="display:flex; flex-direction:column; gap:1rem;">
            <!-- Placeholder -->
            <div style="text-align:center; padding:2rem; background:var(--bg-body); border-radius:8px; border:1px dashed var(--border-color);">
                <div style="font-size:1.5rem; margin-bottom:0.5rem; opacity:0.5">🗺️</div>
                <p style="margin:0; font-size:0.9rem; color:var(--text-tertiary);">Locations will appear here with map links</p>
            </div>
        </div>
    </div>
  </div>"""

html = pattern.sub(replacement, html)

with open('/root/repo/pharmai_portal/frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
