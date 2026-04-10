// ============================================================
// REPORTS
// ============================================================

async function generateReports() {
  const dir = document.getElementById('report-dir').value.trim();
  const r   = await pywebview.api.generate_reports(dir);
  log(r.msg, r.ok ? 'ok' : 'err');
  if (r.ok && r.files) {
    document.getElementById('report-files').innerHTML =
      '<div class="card" style="max-width:520px"><div class="card-title">Generated Files</div>'
      + r.files.map(f => `<div style="padding:5px 0;font-size:14px">📄 ${f}</div>`).join('')
      + '</div>';
  }
}
