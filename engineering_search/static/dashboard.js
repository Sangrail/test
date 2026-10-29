const $ = id => document.getElementById(id);
let current = null;
let page = 0;
let working = false;
let uploading = false;
const pageSize = 20;
const number = value => value == null ? '—' : new Intl.NumberFormat('en-IE').format(value);
const milliseconds = value => value == null ? '—' : `${value.toFixed(2)} ms`;
const date = value => value ? new Intl.DateTimeFormat('en-IE', {dateStyle:'medium', timeStyle:'medium', timeZone:'Europe/Dublin'}).format(new Date(value)) : 'Not yet';
const labels = {up_to_date:['Index is up to date','All scanned files match their indexed versions.','Up to date','✓'], out_of_date:['Index needs an update','Changes were found on disk. Reindex to make them searchable.','Changes pending','↻'], not_indexed:['Ready for the first index','The source files have been scanned. Build the index to enable search.','Not indexed','○'], not_scanned:['Rescan to check freshness','The index is available, but the source folder has not been checked.','Not scanned','○'], scanning:['Scanning source files…','Comparing file contents with the current index.','Scanning','↻'], indexing:['Building the index…','Reading documents and preparing a new searchable snapshot.','Indexing','↻'], error:['An operation needs attention','The last successful snapshot is retained. See the error below.','Error','!']};

function message(text, error=false) {
  $('notice').textContent = text;
  $('notice').className = error ? 'error' : '';
  $('notice').hidden = !text;
}
async function api(path, method='GET') {
  const response = await fetch(path, {method, cache:'no-store'});
  if (response.status === 401 || response.status === 403) {
    window.location.replace('/search?reason=backend-only');
    throw new Error('Index-team session required');
  }
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `Request failed (${response.status})`);
  return data;
}
function buttons() {
  const disabled = working || !current || Boolean(current.operation);
  $('rescan').disabled = disabled;
  $('reindex').disabled = disabled;
  document.body.classList.toggle('busy', disabled && Boolean(current));
}
function render(data) {
  current = data;
  const changes = data.pending_changes;
  $('file-count').textContent = number(data.source_files);
  $('indexed-count').textContent = number(data.indexed_files);
  $('pending-count').textContent = data.last_scanned_at ? number(changes.added + changes.edited + changes.deleted) : '—';
  $('pending-detail').textContent = `${changes.added} added · ${changes.edited} edited · ${changes.deleted} deleted`;
  $('passage-count').textContent = number(data.searchable_passages);
  const [title, description, pill, symbol] = labels[data.status] || labels.not_scanned;
  $('status-title').textContent = title;
  $('status-description').textContent = description;
  $('status-pill').textContent = pill;
  $('status-pill').className = `badge ${data.status}`;
  $('status-symbol').textContent = symbol;
  $('source-root').textContent = data.document_root;
  $('source-root').title = data.document_root;
  $('last-scan').textContent = date(data.last_scanned_at);
  $('last-index').textContent = date(data.last_indexed_at);
  $('inventory-count').textContent = `${number(data.source_files)} indexable files · ${number(data.unsupported_files)} not supported`;
  const run = data.last_index_run;
  $('total-time').textContent = milliseconds(run ? run.total_seconds*1000 : null);
  $('ingestion-time').textContent = milliseconds(run ? run.ingestion_seconds*1000 : null);
  $('index-time').textContent = milliseconds(run ? run.indexing_seconds*1000 : null);
  $('ingestion-rate').textContent = run ? `${number(Math.round(run.ingestion_files_per_second))} files/s` : '—';
  $('index-rate').textContent = run ? `${number(Math.round(run.indexing_files_per_second))} files/s` : '—';
  $('workers').textContent = data.indexer_workers;
  if (data.scan_error || data.index_error) message(data.scan_error || data.index_error, true);
  renderRows();
  buttons();
}
function renderRows() {
  if (!current) return;
  const term = $('file-filter').value.toLocaleLowerCase();
  const rows = current.documents.filter(row => row.file_id.toLocaleLowerCase().includes(term) && (!$('changes-only').checked || ['added','edited','deleted'].includes(row.status)));
  page = Math.max(0, Math.min(page, Math.ceil(rows.length/pageSize)-1));
  const fragment = document.createDocumentFragment();
  for (const row of rows.slice(page*pageSize, (page+1)*pageSize)) {
    const tr = document.createElement('tr');
    const name = document.createElement('td'); name.textContent = row.file_id;
    const size = document.createElement('td'); size.textContent = [row.file_type, row.bytes == null ? null : `${(row.bytes/1024).toFixed(1)} KB`].filter(Boolean).join(' · ') || '—';
    const state = document.createElement('td');
    const badge = document.createElement('span'); badge.className = `badge ${row.status}`;
    badge.textContent = {indexed:'Indexed', added:'New', edited:'Modified', deleted:'Deleted', unsupported:'No reader', unreadable:'Cannot read'}[row.status];
    state.append(badge); tr.append(name, size, state); fragment.append(tr);
  }
  $('document-rows').replaceChildren(fragment);
  $('empty-state').hidden = rows.length > 0;
  $('empty-state').textContent = !current.last_scanned_at ? 'Rescan to discover documents.' : !current.documents.length ? 'No Markdown or PDF documents found in this folder.' : 'No documents match this filter.';
  $('page-label').textContent = rows.length ? `${page*pageSize+1}–${Math.min((page+1)*pageSize,rows.length)} of ${number(rows.length)} documents` : '0 documents';
  $('previous').disabled = page === 0;
  $('next').disabled = (page+1)*pageSize >= rows.length;
}
async function refresh() {
  const [status, metrics, uploads] = await Promise.all([api('/index/status'), api('/telemetry'), api('/uploads')]);
  render(status);
  renderUploads(uploads);
  for (const key of ['min','median','average','max']) $('query-'+key).textContent = milliseconds(metrics.query_ms[key]);
  $('query-window').textContent = `Server timings · last ${number(metrics.query_ms.count)} queries · since process start`;
  $('connection-label').textContent = 'API connected'; $('connection-dot').style.background = '#4e9c7d';
}
function connectionError(error) {
  message(error.message, true);
  $('connection-label').textContent = 'Request failed'; $('connection-dot').style.background = '#bc6551';
}
async function operate(kind) {
  if (working) return;
  working = true;
  message('');
  if (current) render({...current, operation:kind === 'scan' ? 'scanning' : 'indexing', status:kind === 'scan' ? 'scanning' : 'indexing'});
  buttons();
  try {
    const result = await api(kind === 'scan' ? '/scan' : '/index', 'POST');
    await refresh();
    const pending = Object.values(current.pending_changes).reduce((a,b) => a+b,0);
    message(kind === 'scan' ? `Scan complete. ${current.source_files} source files found; ${pending} pending ${pending === 1 ? 'change' : 'changes'}. The search index was not modified.` : `Index complete. ${result.files} documents and ${result.passages} passages are searchable.`);
    if (current.scan_error || current.index_error) message(current.scan_error || current.index_error, true);
  } catch (error) {
    try { await refresh(); } catch (_) { if (current) current.operation = null; }
    connectionError(error);
  } finally { working = false; buttons(); }
}
$('rescan').addEventListener('click', () => operate('scan'));
$('reindex').addEventListener('click', () => operate('index'));
$('file-filter').addEventListener('input', () => {page=0;renderRows();});
$('changes-only').addEventListener('change', () => {page=0;renderRows();});
$('previous').addEventListener('click', () => {page--;renderRows();});
$('next').addEventListener('click', () => {page++;renderRows();});

function uploadMessage(text, error=false) {
  $('upload-notice').textContent = text;
  $('upload-notice').className = error ? 'error' : '';
  $('upload-notice').hidden = !text;
}
function renderUploads(data) {
  for (const state of ['uploading','queued','indexing','ready','failed']) $('jobs-'+state).textContent = number(data.counts[state]);
  $('worker-summary').textContent = `${data.running_workers} / ${data.worker_count} upload workers running · ${data.active_workers.length} busy`;
  $('queue-summary').textContent = `Latest ${data.jobs.length} of ${data.total_jobs} upload jobs · average processing ${milliseconds(data.average_processing_ms)}`;
  $('queue-age').textContent = `Oldest queued: ${data.oldest_queued_seconds.toFixed(1)} s`;
  $('uploads-empty').hidden = data.jobs.length > 0;
  const fragment = document.createDocumentFragment();
  for (const job of data.jobs) {
    const row = document.createElement('tr');
    const name = document.createElement('td'); name.textContent = job.filename; name.title = job.file_id;
    const status = document.createElement('td');
    const badge = document.createElement('span'); badge.className = `badge ${job.status}`;
    badge.textContent = {uploading:'Uploading',queued:'Queued',indexing:'Indexing',ready:'Ready',failed:'Failed'}[job.status]; status.append(badge);
    const worker = document.createElement('td'); worker.textContent = `${job.worker_id || '—'} / ${job.attempts}`;
    const timing = document.createElement('td'); timing.textContent = `${milliseconds(job.queue_wait_ms)} / ${milliseconds(job.duration_ms)}`;
    const details = document.createElement('td');
    if (job.status === 'failed') {
      const reason = document.createElement('span'); reason.textContent = job.error; details.append(reason);
      if (job.source_version) {
        const retry = document.createElement('button'); retry.className = 'secondary retry'; retry.textContent = 'Retry indexing';
        retry.addEventListener('click', async () => {
          retry.disabled = true;
          try { await api(`/uploads/${job.id}/retry`, 'POST'); await refresh(); uploadMessage(`Retry queued for ${job.filename}.`); }
          catch(error) { uploadMessage(error.message, true); retry.disabled = false; }
        });
        details.append(retry);
      }
    } else details.textContent = job.status === 'ready' ? `${job.passages} passages · ${date(job.finished_at)}` : job.status === 'uploading' ? 'Waiting for the file transfer to finish' : 'Saved; awaiting searchable index commit';
    row.append(name,status,worker,timing,details); fragment.append(row);
  }
  $('upload-rows').replaceChildren(fragment);
}
async function uploadFiles(files) {
  if (uploading || !files.length) return;
  uploading = true;
  message('');
  $('choose-files').disabled = true;
  let cursor = 0, accepted = 0, failed = 0;
  const errors = [];
  const publishProgress = () => uploadMessage(`Uploading ${files.length} file(s): ${accepted} accepted for indexing, ${failed} failed.`, failed > 0);
  publishProgress();
  async function transfer() {
    while (cursor < files.length) {
      const file = files[cursor++];
      try {
        if (!file.name.toLowerCase().endsWith('.md')) throw new Error('Only .md files are supported');
        if (!file.size || file.size > 10*1024*1024) throw new Error('Choose a non-empty file up to 10 MiB');
        const created = await fetch('/uploads', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({filename:file.name})});
        const job = await created.json();
        if (!created.ok) throw new Error(typeof job.detail === 'string' ? job.detail : 'Invalid upload filename');
        const sent = await fetch(`/uploads/${job.id}/content`, {method:'PUT', headers:{'Content-Type':'application/octet-stream'}, body:file});
        const result = await sent.json();
        if (!sent.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Upload failed');
        accepted++;
      } catch(error) { failed++; errors.push(`${file.name}: ${error.message}`); }
      publishProgress();
    }
  }
  try {
    await Promise.all(Array.from({length:Math.min(3,files.length)}, transfer));
    await refresh();
    uploadMessage(`${accepted} file(s) accepted for indexing. ${failed ? errors.join(' · ') : 'Follow their progress in the queue below.'}`, failed > 0);
  } catch(error) { uploadMessage(error.message,true); }
  finally { uploading = false; $('choose-files').disabled = false; $('upload-files').value = ''; }
}
$('choose-files').addEventListener('click', () => $('upload-files').click());
$('upload-files').addEventListener('change', event => uploadFiles(Array.from(event.target.files)));
async function start() {
  try {
    const matrix = await api('/admin/access');
    const fragment = document.createDocumentFragment();
    for (const rule of matrix.rules) {
      const row = window.document.createElement('tr');
      const path = window.document.createElement('td'); path.textContent = rule.path; row.append(path);
      for (const id of ['jp','kamal','maya']) {
        const cell = window.document.createElement('td'); cell.textContent = rule.readers.includes(id) ? 'Allowed' : '—'; row.append(cell);
      }
      fragment.append(row);
    }
    $('permission-rows').replaceChildren(fragment);
    await refresh(); if (!current.operation) await operate('scan');
  }
  catch(error) { connectionError(error); }
}
start();
// Poll server state only. Filesystem reads happen on initial load or explicit actions.
setInterval(() => { if (!working && !document.hidden) refresh().catch(connectionError); }, 2000);
