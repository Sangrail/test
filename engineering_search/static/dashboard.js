const $ = id => document.getElementById(id);
let current = null;
let page = 0;
let working = false;
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
  // Index statuses (indexing/status.py) -> badge text and badge style.
  const STATUS_LABELS = {indexed: ['Indexed', 'indexed'], added: ['New', 'added'], edited: ['Modified', 'edited'],
    deleted: ['Deleted', 'deleted'], INDEXED_PARTIAL: ['Partly read', 'edited'], NO_TEXT_LAYER: ['No text (scan)', 'unreadable'],
    NO_EXTRACTABLE_CONTENT: ['Nothing to index', 'unsupported'], UNSUPPORTED_FORMAT: ['Unknown type', 'unsupported'],
    NO_READER: ['No reader', 'unsupported'], UNSUPPORTED_VERSION: ['Version not supported', 'unsupported'],
    DEPENDENCY_MISSING: ['Reader not installed', 'unsupported'], FORMAT_MISMATCH: ['Wrong extension', 'unreadable'],
    INVALID_HEADER: ['Broken header', 'unreadable'], READ_ERROR: ['Cannot read', 'unreadable'],
    MALFORMED: ['Malformed', 'unreadable'], ENCRYPTED: ['Encrypted', 'unreadable'], READER_CRASH: ['Reader failed', 'unreadable']};
  const rows = current.documents.filter(row => row.file_id.toLocaleLowerCase().includes(term) && (!$('changes-only').checked || ['added','edited','deleted'].includes(row.status)));
  page = Math.max(0, Math.min(page, Math.ceil(rows.length/pageSize)-1));
  const fragment = document.createDocumentFragment();
  for (const row of rows.slice(page*pageSize, (page+1)*pageSize)) {
    const tr = document.createElement('tr');
    const name = document.createElement('td'); name.textContent = row.file_id;
    const size = document.createElement('td'); size.textContent = [row.file_type, row.bytes == null ? null : `${(row.bytes/1024).toFixed(1)} KB`].filter(Boolean).join(' · ') || '—';
    const state = document.createElement('td');
    const [label, kind] = STATUS_LABELS[row.status] || [row.status, 'unsupported'];
    const badge = document.createElement('span'); badge.className = `badge ${kind}`; badge.textContent = label;
    if (row.format_version) size.textContent += ` ${row.format_version}`;
    state.append(badge); tr.append(name, size, state); fragment.append(tr);
  }
  $('document-rows').replaceChildren(fragment);
  $('empty-state').hidden = rows.length > 0;
  $('empty-state').textContent = !current.last_scanned_at ? 'Rescan to discover documents.' : !current.documents.length ? 'No readable documents found in this folder.' : 'No documents match this filter.';
  $('page-label').textContent = rows.length ? `${page*pageSize+1}–${Math.min((page+1)*pageSize,rows.length)} of ${number(rows.length)} documents` : '0 documents';
  $('previous').disabled = page === 0;
  $('next').disabled = (page+1)*pageSize >= rows.length;
}
async function refresh() {
  const [status, metrics] = await Promise.all([api('/index/status'), api('/telemetry')]);
  render(status);
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
