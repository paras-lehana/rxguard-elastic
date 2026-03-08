import re

with open('/root/repo/pharmai_portal/frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

upload_block = """
    <!-- Jan Aushadhi PDF Upload Zone -->
    <div class="upload-zone" id="jaDropZone" style="margin-top: 1.5rem; cursor: pointer; border-radius:12px; padding:1.5rem;">
      <div class="upload-icon" style="font-size:2rem; margin-bottom:0.5rem;">📄</div>
      <p style="margin:0; font-weight:600;">Upload Data Source</p>
      <p class="upload-hint" style="margin:0; font-size:0.85rem; color:var(--text-secondary);">Drop the Jan Aushadhi MRP or Locators PDF here to update the Knowledge Base.</p>
      <input type="file" id="jaUploadInput" accept="application/pdf" multiple style="display:none">
    </div>
  </div>"""

pattern = re.compile(r'    </div>\n  </div><!-- ── Settings ── -->')
html = html.replace('    </div>\n  </div>\n\n  <!-- ── Settings ── -->', upload_block + '\n\n  <!-- ── Settings ── -->')

with open('/root/repo/pharmai_portal/frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
