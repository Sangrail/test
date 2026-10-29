const $ = id => document.getElementById(id);
let user = null, controller = null, generation = 0, switching = false;
let activeSearch = null, currentPage = 1, totalPages = 0;
let lastList = null; // file IDs of the last list answer, for follow-up questions

function clearResults() {
  generation++;
  if (controller) controller.abort();
  controller = null;
  activeSearch = null; currentPage = 1; totalPages = 0;
  $('search-pagination').hidden = true; $('searched-for').textContent = '';
  $('previous-page').disabled = true;
  $('next-page').disabled = true;
  $('page-summary').textContent = '';
  $('search-button').disabled = !user || switching;
  $('search-results').replaceChildren();
  $('answer-panel').hidden = true; $('answer-panel').replaceChildren();
  $('results-title').textContent = 'Your evidence will appear here';
  $('results-timing').textContent = '';
  $('trace-note').textContent = '';
  $('search-message').textContent = user ? 'Enter search terms to find permitted source passages.' : 'Choose a demo user to search.';
}
function notice(text, error=false) {
  $('session-notice').textContent = text;
  $('session-notice').className = error ? 'error' : '';
  $('session-notice').hidden = !text;
}
async function jsonRequest(path, options={}) {
  const response = await fetch(path, {cache:'no-store', ...options});
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : data.detail?.message || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return data;
}
function setUser(next) {
  const changed = user?.id !== next?.id;
  user = next;
  if (changed) { clearResults(); setLastList(null); }
  // Nothing but the sign-in screen shows until a user is selected.
  $('signin-screen').hidden = !!user;
  $('app-screen').hidden = !user;
  $('app-nav').hidden = !user;
  $('session-chip').hidden = !user;
  $('identity-title').textContent = user ? `Signed in as ${user.name} · ${user.title}` : '';
  $('admin-link').hidden = user?.role !== 'index_team';
  $('audit-link').hidden = user?.role !== 'index_team';
  $('query').disabled = !user;
  $('search-button').disabled = !user;
  $('try-load').disabled = !user;
  $('search-identity').textContent = user ? `Searching as ${user.name} · file permissions enforced` : 'Sign in to search your permitted documents.';
  $('my-documents').hidden = true;
}
// Categorical slots 1 and 2. The legend and the table give the same numbers as text.
const TYPE_COLOURS = {Markdown: '#2a78d6', PDF: '#eb6834'};
function svgNode(tag, attributes) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  return node;
}
function typeChart(byType) {
  const svg = $('type-chart');
  const entries = Object.entries(byType).filter(([, count]) => count > 0);
  const total = entries.reduce((sum, [, count]) => sum + count, 0);
  const radius = 44, circumference = 2 * Math.PI * radius, gap = entries.length > 1 ? 2 : 0;
  const parts = [svgNode('circle', {cx: 60, cy: 60, r: radius, fill: 'none', stroke: '#eef2f0', 'stroke-width': 18})];
  let offset = 0;
  for (const [type, count] of entries) {
    // A slice is the dash of a thick circle stroke. The 2px gap separates the slices.
    const length = Math.max(count / total * circumference - gap, 1);
    const slice = svgNode('circle', {cx: 60, cy: 60, r: radius, fill: 'none', stroke: TYPE_COLOURS[type],
      'stroke-width': 18, 'stroke-dasharray': `${length} ${circumference - length}`,
      'stroke-dashoffset': -offset, transform: 'rotate(-90 60 60)', class: 'type-slice'});
    const tip = svgNode('title', {}); tip.textContent = `${type}: ${count} of ${total} documents`;
    slice.append(tip); parts.push(slice);
    offset += count / total * circumference;
  }
  const number = svgNode('text', {x: 60, y: 60, 'text-anchor': 'middle', class: 'type-total'}); number.textContent = total;
  const label = svgNode('text', {x: 60, y: 75, 'text-anchor': 'middle', class: 'type-label'}); label.textContent = 'documents';
  const title = svgNode('title', {id: 'type-chart-title'});
  title.textContent = `Documents by type: ${entries.map(([type, count]) => `${type} ${count}`).join(', ')}`;
  svg.replaceChildren(title, ...parts, number, label);
  $('type-legend').replaceChildren(...Object.entries(byType).map(([type, count]) => {
    const item = el('li'); const swatch = el('span', 'swatch'); swatch.style.background = TYPE_COLOURS[type];
    item.append(swatch, el('span', '', type), el('strong', '', `${count}`),
                el('small', '', total ? `${Math.round(count / total * 100)}%` : ''));
    return item;
  }));
}
async function accessibleFiles() {
  const identity = user?.id;
  if (!identity) return;
  const data = await jsonRequest('/demo/documents');
  if (identity !== user?.id) return;
  $('my-documents-title').textContent = `${user.name} can search ${data.documents.length} documents`;
  typeChart(data.by_type);
  $('folder-rows').replaceChildren(...data.by_folder.map(folder => {
    const row = el('tr');
    row.append(el('td', '', folder.folder), el('td', '', `${folder.markdown}`), el('td', '', `${folder.pdf}`), el('td', '', `${folder.readable}`));
    return row;
  }));
  $('my-documents').hidden = false;
}
async function syncSession() {
  if (switching) return;
  try {
    const data = await jsonRequest('/auth/me');
    if (data.user?.id !== user?.id) { setUser(data.user); await accessibleFiles(); }
  } catch(error) { notice(error.message,true); }
}
async function signIn(selected) {
  if (!selected || switching) return;
  switching = true;
  clearResults();
  for (const card of document.querySelectorAll('.user-card')) card.disabled = true;
  try {
    const data = await jsonRequest('/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({user_id:selected})});
    notice('');
    setUser(data.user); await accessibleFiles();
    $('query').focus();
  } catch(error) { setUser(null); notice(error.message,true); }
  finally {
    switching = false;
    for (const card of document.querySelectorAll('.user-card')) card.disabled = false;
  }
}
function userCard(person) {
  const card = document.createElement('button'); card.type = 'button'; card.className = 'user-card';
  const name = document.createElement('strong'); name.textContent = person.name;
  const role = document.createElement('span'); role.className = 'role'; role.textContent = person.title;
  const can = document.createElement('ul');
  for (const line of person.can) { const item = document.createElement('li'); item.textContent = line; can.append(item); }
  const folders = el('ul', 'folder-access');
  folders.setAttribute('aria-label', `Folders ${person.name} can read`);
  for (const folder of person.folders || []) {
    // A symbol and words show the access, so it is not shown by colour alone.
    const [mark, words] = {all: ['✓', `all ${folder.files}`], some: ['◐', `${folder.readable} of ${folder.files}`],
                           none: ['✕', 'none']}[folder.access];
    const item = el('li', `access-${folder.access}`);
    item.append(el('span', 'mark', mark), el('code', '', folder.folder), el('span', 'count', words));
    folders.append(item);
  }
  const tryIt = document.createElement('p'); tryIt.className = 'try'; tryIt.textContent = `Try: ${person.try}`;
  const go = document.createElement('span'); go.className = 'go'; go.textContent = `Sign in as ${person.name} →`;
  card.append(name, role, can, folders, tryIt, go);
  card.addEventListener('click', () => signIn(person.id));
  return card;
}
$('logout-button').addEventListener('click', async () => {
  clearResults();
  try { await jsonRequest('/auth/logout',{method:'POST'}); setUser(null); notice('Signed out. Choose a user to search again.'); }
  catch(error) { notice(error.message,true); }
});

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function where(source) {
  return `${source.file_id}${source.page ? ` · page ${source.page}` : ''} · lines ${source.start_line}–${source.end_line}`;
}
function quoted(source) {
  // The exact text from the document, with the value in bold.
  const quote = el('blockquote', 'answer-quote');
  const at = source.value ? source.text.indexOf(source.value) : -1;
  if (at < 0) { quote.textContent = source.text; return quote; }
  quote.append(source.text.slice(0, at), el('strong', '', source.value), source.text.slice(at + source.value.length));
  return quote;
}
function setLastList(fileIds) {
  lastList = fileIds;
  $('within-list').checked = false;
  $('within-control').hidden = !lastList?.length;
  $('within-label').textContent = lastList ? `Ask the next question about these ${lastList.length} documents only` : '';
}
function renderAnswer(answer) {
  const panel = $('answer-panel');
  const parts = [];
  if (answer.type === 'answer') {
    parts.push(el('div', 'eyebrow', 'ANSWER'));
    if (answer.status === 'partial' || answer.status === 'unverified') {
      parts[0].textContent = answer.status === 'partial' ? 'CLOSEST MATCH, NOT AN ANSWER' : 'VALUE FOUND, SUBJECT NOT CONFIRMED';
      parts.push(el('p', 'answer-missing', answer.message));
    }
    if (answer.status !== 'not_found') {
      parts.push(quoted(answer), el('p', 'answer-source', `Source: ${where(answer)}`));
      const version = el('details', 'answer-version'); version.append(el('summary', '', 'File version'), el('code', '', `SHA-256 ${answer.source_version}`));
      parts.push(version);
      if (answer.also_stated_in.length) {
        parts.push(el('h3', '', 'Other documents that also state a value'));
        const list = el('ul', 'answer-list');
        for (const other of answer.also_stated_in) { const item = el('li'); item.append(quoted(other), el('p', 'answer-source', where(other))); list.append(item); }
        parts.push(list);
      }
    } else parts.push(el('p', 'answer-missing', answer.message));
  } else {
    parts.push(el('div', 'eyebrow', 'DOCUMENTS'));
    const condition = answer.criteria.comparison ? ` · value ${answer.criteria.comparison}` : '';
    parts.push(el('h2', '', answer.status === 'found' ? `${answer.count} ${answer.count === 1 ? 'document matches' : 'documents match'}` : 'No documents match'));
    parts.push(el('p', 'answer-source', `Contains all of: ${answer.criteria.all_words.join(', ')}${condition}`));
    if (answer.status === 'found') {
      const list = el('ul', 'answer-list');
      for (const doc of answer.documents) { const item = el('li'); item.append(el('p', 'answer-file', where(doc)), quoted(doc)); list.append(item); }
      parts.push(list);
      if (answer.truncated || answer.document_pages > 1) parts.push(el('p', 'answer-source', `Showing ${answer.documents.length} of ${answer.count}. Ask a narrower question to see the rest.`));
    } else parts.push(el('p', 'answer-missing', answer.message));
  }
  panel.replaceChildren(...parts);
  panel.hidden = false;
  if (answer.type === 'list') setLastList(answer.documents.map(d => d.file_id));
}
function renderResults(data, elapsed) {
  if (data.page === 1) renderAnswer(data.answer);
  const fragment = document.createDocumentFragment();
  for (const passage of data.evidence) {
    const article = document.createElement('article'); article.className = 'evidence-card';
    const heading = document.createElement('h3'); heading.textContent = passage.heading || passage.file_id.split('/').pop();
    const location = document.createElement('p'); location.className = 'evidence-location';
    location.textContent = `${passage.file_id}${passage.page ? ` · page ${passage.page}` : ''} · lines ${passage.start_line}–${passage.end_line}`;
    const quote = document.createElement('pre'); quote.textContent = passage.text;
    const version = document.createElement('details');
    const summary = document.createElement('summary'); summary.textContent = 'Source version';
    const hash = document.createElement('code'); hash.textContent = `SHA-256 ${passage.source_version}`;
    version.append(summary,hash); article.append(heading,location,quote,version); fragment.append(article);
  }
  $('search-results').replaceChildren(fragment);
  $('results-title').textContent = `Supporting passages · ${data.matched_passages}`;
  $('results-timing').textContent = `${elapsed.toFixed(0)} ms · browser round trip`;
  const first = (data.page-1)*data.limit+1, last = first+data.evidence.length-1;
  $('searched-for').textContent = `Searched for: ${data.searched_for}${data.ignored_words.length ? ` · ignored: ${data.ignored_words.join(', ')}` : ''}`;
  $('search-message').textContent = data.evidence.length ? `Showing ${first}–${last} of ${data.matched_passages} permitted passages available to ${data.user.name}.` : data.matched_passages ? 'No passages on this page. Results have changed; go back or search again.' : 'No matching passages in documents you can read. Try other words.';
  currentPage = data.page; totalPages = data.total_pages;
  $('search-pagination').hidden = !data.matched_passages;
  $('page-summary').textContent = data.page <= totalPages ? `Page ${data.page} of ${totalPages}` : `Page ${data.page} is no longer available`;
  $('previous-page').disabled = !data.has_previous;
  $('next-page').disabled = !data.has_next;
  $('trace-note').textContent = `Request ${data.request_id} · permission decisions and source manifest recorded in the backend audit trail.`;
}
async function searchPage(page, criteria) {
  if (!user || switching || !criteria?.query.trim()) return;
  clearResults();
  activeSearch = criteria;
  const attempt = generation, identity = user.id;
  controller = new AbortController();
  $('search-button').disabled = true;
  $('search-message').textContent = 'Searching permitted documents…';
  const start = performance.now();
  try {
    const data = await jsonRequest('/search', {method:'POST', signal:controller.signal,
      headers:{'Content-Type':'application/json'}, body:JSON.stringify({...criteria, page})});
    if (generation !== attempt || user?.id !== identity) return;
    if (data.user.id !== identity) {
      setUser(data.user); await accessibleFiles(); notice('The active session changed. Search again as the displayed user.'); return;
    }
    renderResults(data, performance.now()-start);
  } catch(error) {
    if (error.name === 'AbortError' || generation !== attempt) return;
    $('search-message').textContent = error.message;
    if (error.status === 401) { setUser(null); notice('Your demo session expired. Sign in again.',true); }
  } finally { if (generation === attempt) $('search-button').disabled = !user; }
}
$('search-form').addEventListener('submit', event => {
  event.preventDefault();
  const within = $('within-list').checked && lastList ? lastList : null;
  searchPage(1, {query:$('query').value, limit:Number($('page-size').value), within});
});
$('previous-page').addEventListener('click', () => searchPage(Math.max(1, Math.min(currentPage-1, totalPages)), activeSearch));
$('next-page').addEventListener('click', () => searchPage(currentPage+1, activeSearch));
$('query').addEventListener('input', clearResults);
$('page-size').addEventListener('change', clearResults);
$('try-load').addEventListener('click', () => { $('query').value='load'; $('search-form').requestSubmit(); });
async function start() {
  try {
    const [people, session] = await Promise.all([jsonRequest('/auth/users'), jsonRequest('/auth/me')]);
    $('user-cards').replaceChildren(...people.users.map(userCard));
    setUser(session.user); await accessibleFiles();
    if (new URLSearchParams(location.search).get('reason') === 'backend-only') notice('Index operations and audit are restricted to the index team. Maya has that role in this demo.');
  } catch(error) { notice(error.message,true); }
}
window.addEventListener('focus',syncSession);
document.addEventListener('visibilitychange', () => { if (!document.hidden) syncSession(); });
start();
