const $ = id => document.getElementById(id);
let page = 1, snapshot = null, pages = 0, generation = 0, controller = null;
function clearEvents() {
  $('audit-events').replaceChildren();
  $('audit-summary').textContent = '—';
  $('audit-previous').disabled = true;
  $('audit-next').disabled = true;
}
function deny() {
  generation++;
  if (controller) controller.abort();
  clearEvents();
  window.location.replace('/search?reason=backend-only');
}
async function checkSession() {
  try {
    const response = await fetch('/auth/me', {cache:'no-store'});
    const data = await response.json();
    if (!response.ok || data.user?.role !== 'index_team') deny();
  } catch {
    clearEvents();
    $('audit-message').textContent = 'Could not verify your session. Refresh to try again.';
  }
}
async function load(target=1, refresh=false) {
  const attempt = ++generation;
  if (controller) controller.abort();
  controller = new AbortController();
  if (refresh) snapshot = null;
  clearEvents();
  $('audit-message').textContent = 'Loading audit events…';
  const query = new URLSearchParams({page:target, limit:$('audit-size').value});
  if (snapshot !== null) query.set('snapshot_id', snapshot);
  try {
    const response = await fetch(`/audit/events?${query}`, {cache:'no-store', signal:controller.signal});
    if (response.status === 401 || response.status === 403) { deny(); return; }
    const data = await response.json();
    if (attempt !== generation) return;
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not read audit events');
    page = data.page; snapshot = data.snapshot_id; pages = data.total_pages;
    const fragment = document.createDocumentFragment();
    for (const entry of data.events) {
      const event = entry.payload;
      const article = document.createElement('article'); article.className = 'audit-event';
      const heading = document.createElement('h3'); heading.textContent = `#${entry.id} · ${event.event || 'Event'}`;
      const meta = document.createElement('p'); meta.className = 'evidence-location';
      meta.textContent = `${event.timestamp || 'Time unavailable'} · ${event.actor_subject || 'No actor recorded'}${event.request_id ? ` · Request ${event.request_id}` : ''}`;
      const details = document.createElement('details');
      const summary = document.createElement('summary'); summary.textContent = 'Event details and permission decisions';
      const content = document.createElement('pre'); content.textContent = JSON.stringify(event, null, 2);
      details.append(summary, content); article.append(heading, meta, details); fragment.append(article);
    }
    $('audit-events').replaceChildren(fragment);
    $('audit-message').textContent = data.total_events ? `${data.total_events} recorded events in this view · newest first` : 'No audit events recorded yet.';
    $('audit-summary').textContent = pages ? `Page ${page} of ${pages} · ${data.events.length} events shown` : '0 events';
    $('audit-previous').disabled = !data.has_previous;
    $('audit-next').disabled = !data.has_next;
  } catch (error) {
    if (error.name !== 'AbortError' && attempt === generation) $('audit-message').textContent = error.message;
  }
}
$('audit-refresh').addEventListener('click', () => load(1, true));
$('audit-size').addEventListener('change', () => load(1, true));
$('audit-previous').addEventListener('click', () => load(Math.max(1, Math.min(page-1, pages))));
$('audit-next').addEventListener('click', () => load(page+1));
window.addEventListener('focus', checkSession);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { generation++; if (controller) controller.abort(); clearEvents(); }
  else { checkSession(); load(page); }
});
load();
