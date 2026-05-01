// ============================================================
// CONFIRMATION MODAL — Promise-based replacement for confirm()
// ============================================================

function showConfirm(message, { title = 'Are you sure?', confirmText = 'Confirm', danger = true } = {}) {
  return new Promise(resolve => {
    const modal     = document.getElementById('confirm-modal');
    const msgEl     = document.getElementById('confirm-modal-message');
    const okBtn     = document.getElementById('confirm-modal-ok');
    const cancelBtn = document.getElementById('confirm-modal-cancel');

    document.getElementById('confirm-modal-title').textContent = title;
    msgEl.textContent = message;
    okBtn.textContent = confirmText;
    okBtn.className   = `btn ${danger ? 'btn-danger' : 'btn-primary'}`;
    okBtn.style.flex  = '2';

    function cleanup(result) {
      modal.style.display = 'none';
      okBtn.removeEventListener('click', onOk);
      cancelBtn.removeEventListener('click', onCancel);
      document.removeEventListener('keydown', onKey);
      resolve(result);
    }
    function onOk()     { cleanup(true);  }
    function onCancel() { cleanup(false); }
    function onKey(e)   { if (e.key === 'Escape') cleanup(false); }

    okBtn.addEventListener('click', onOk);
    cancelBtn.addEventListener('click', onCancel);
    document.addEventListener('keydown', onKey);

    modal.style.display = 'flex';
    cancelBtn.focus();
  });
}
