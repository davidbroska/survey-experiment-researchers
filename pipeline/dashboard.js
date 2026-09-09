'use strict';
const DATA = JSON.parse(document.getElementById('dashboard-data').textContent);
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const LABELS = {us_explicit:'US · explicit',us_inferred:'US · inferred',non_us:'Non-US evidence',unclear:'Unclear geography',not_applicable:'No applicable sample identified'};
const COLS = [
  ['full_name','Researcher','text','name-cell'],
  ['n_articles','Survey-experiment articles','number','primary num'],
  ['n_us_articles','US-sample articles','number','num'],
  ['n_unclear_articles','Unclear geography','number','num'],
  ['institution','Institution','text','aff-cell'],
  ['department','Department / unit','text','dept-cell'],
  ['country','Country','text','country-cell'],
  ['role','Role','text','role-cell'],
  ['n_first','First','number','num'],
  ['n_last','Last','number','num'],
  ['n_sole','Sole','number','num'],
  ['score_rank','Total-count rank','number','num']
];
let sortKey = 'n_articles', direction = -1, activeAuthor = null, lastFocused = null;
const collator = new Intl.Collator('en', {sensitivity:'base',numeric:true});
const authors = new Map(DATA.authors.map(a => [a.authid,a]));
const articles = new Map(DATA.articles.map(a => [a.scopus_id,a]));
const queued = new Map(DATA.queue.map(a => [a.scopus_id,a]));
const available = new Map((DATA.downloaded_pending || []).map(a => [a.scopus_id,a]));
let downloaded = new Set();
try { downloaded = new Set(JSON.parse(localStorage.getItem('socialtune-downloaded-v1') || '[]')); } catch (_) { /* file:// storage may be disabled */ }

function setSort(key, forceDirection) {
  const col = COLS.find(c => c[0] === key);
  direction = forceDirection ?? (sortKey === key ? -direction : (col[2] === 'number' && key !== 'score_rank' ? -1 : 1));
  sortKey = key;
  renderPeople();
}
function visiblePeople() {
  const term = $('search').value.toLocaleLowerCase().trim();
  const rows = DATA.authors.filter(a => !term || [a.full_name,a.institution,a.department,a.country,a.role].join(' ').toLocaleLowerCase().includes(term));
  const numeric = COLS.find(c => c[0] === sortKey)[2] === 'number';
  return rows.slice().sort((a,b) => {
    const primary = numeric ? Number(a[sortKey])-Number(b[sortKey]) : collator.compare(a[sortKey],b[sortKey]);
    // Deterministic secondary ordering does not imply a difference in the primary score.
    return direction * primary || (sortKey === 'n_us_articles' ? Number(b.n_articles)-Number(a.n_articles) : 0) || Number(a.authid)-Number(b.authid);
  });
}
function renderPeople() {
  const rows = visiblePeople();
  $('headers').innerHTML = COLS.map(([key,label,type,cls]) => `<th scope="col" class="${cls}" aria-sort="${sortKey === key ? (direction < 0 ? 'descending' : 'ascending') : 'none'}"><button data-sort="${key}" title="Sort by ${label}; click again to reverse"><span>${label}${key === 'n_articles' ? '<span class="number-detail">PRIMARY · FIRST / LAST</span>' : ''}</span><span class="sort-mark" aria-hidden="true">${sortKey === key ? (direction < 0 ? '↓' : '↑') : '↕'}</span></button></th>`).join('');
  $('people-rows').innerHTML = rows.map(a => `<tr data-author="${a.authid}">${COLS.map(([key,label,type,cls]) => {
    let value = esc(a[key]);
    if (key === 'full_name') value = `<button class="name-button" data-open-author="${a.authid}">${esc(a.full_name)}</button>`;
    if (key === 'n_articles') value = `<strong class="count">${a.n_articles}</strong>`;
    if (key === 'n_us_articles') value = `<strong class="us-count">${a.n_us_articles}</strong><span class="number-detail">${a.n_us_explicit_articles} explicit + ${a.n_us_inferred_articles} inferred</span>`;
    if (key === 'n_unclear_articles') value = `<span class="unclear-count">${a.n_unclear_articles}</span>`;
    if (key === 'institution') value = `<a href="${esc(a.source_url)}" target="_blank" rel="noopener noreferrer">${esc(a.institution)} ↗</a>`;
    return `<td class="${cls}" data-key="${key}">${value}</td>`;
  }).join('')}</tr>`).join('');
  if (!rows.length) $('people-rows').innerHTML = `<tr><td colspan="${COLS.length}">No researchers match this search.</td></tr>`;
  const label = COLS.find(c => c[0] === sortKey)[1];
  $('table-status').textContent = `Showing ${rows.length} of ${DATA.authors.length} researchers · Sorted by ${label.toLowerCase()}, ${direction < 0 ? 'descending' : 'ascending'} · Equal counts remain tied.`;
  $('sort-total').setAttribute('aria-pressed',String(sortKey === 'n_articles' && direction === -1));
  $('sort-us').setAttribute('aria-pressed',String(sortKey === 'n_us_articles' && direction === -1));
}
const TAB_NAMES = ['people','summary','queue'];
const TAB_HASHES = {people:'ranking',summary:'summary',queue:'downloads'};
function switchTab(name, updateHash = true) {
  if (!TAB_NAMES.includes(name)) name = 'people';
  for (const tab of TAB_NAMES) {
    const on = tab === name;
    $(tab+'-view').hidden = !on;
    $(tab+'-tab').setAttribute('aria-selected',String(on));
    $(tab+'-tab').tabIndex = on ? 0 : -1;
  }
  if (updateHash) {
    try { history.replaceState(null,'','#'+TAB_HASHES[name]); } catch (_) { /* Some local-file contexts restrict history. */ }
  }
}
function batchRows() { return DATA.queue.filter(r => r.batch === Number($('batch').value)); }
function renderQueue() {
  const rows = batchRows();
  $('queue-cards').innerHTML = rows.map(r => `<article class="queue-card ${downloaded.has(r.scopus_id) ? 'downloaded' : ''}">
    <h3>${r.manual_position || r.queue_position}. <a href="${esc(r.manual_download_url || r.article_url)}" target="_blank" rel="noopener noreferrer">${esc(r.title)} ↗</a></h3>
    <p>${esc(r.year)} · ${esc(r.journal)} · <a href="${esc(r.article_url)}" target="_blank" rel="noopener noreferrer">DOI / publisher ↗</a></p><p><strong>Affects ${r.n_credited_researchers} researcher${r.n_credited_researchers > 1 ? 's' : ''}:</strong> ${esc(r.credited_researchers)}</p>
    <p class="review-note">${esc(r.open_access_note || r.rationale)}</p>${r.tie_priority_position ? `<p><strong>Potential tie impact:</strong> ${r.top50_us_tied_pairs_separated_if_us} US-ranking pairs; ${r.top50_total_ties_differentiated_if_us} total-count ties distinguishable using US evidence.</p><p class="review-note">If this article has a US sample: ${esc(r.us_positive_scenario)}. This is a scenario, not a prediction.</p>` : ""}${r.manual_retrieval_status === "user_unavailable" ? `<p class="review-note"><strong>Reported unavailable; skip this paper.</strong> ${esc(r.manual_retrieval_note)}</p>` : ""}<div class="actions"><code>${esc(r.suggested_filename)}</code><button class="copy-filename secondary" data-copy-name="${r.scopus_id}">Copy filename</button>
    <label><input type="checkbox" data-downloaded="${r.scopus_id}" ${downloaded.has(r.scopus_id) ? 'checked' : ''}>Downloaded</label></div></article>`).join('');
  const done = DATA.queue.filter(r => downloaded.has(r.scopus_id)).length;
  $('queue-status').textContent = rows.length ? `Batch ${$('batch').value} of ${DATA.summary.n_download_batches} · ${rows.length} papers · ${done} of ${DATA.queue.length} marked downloaded in this browser` : 'No further downloads are needed; available PDFs may still await geography review.';
}
function showAuthor(aid) {
  const a = authors.get(aid);
  activeAuthor = aid;
  lastFocused = document.activeElement;
  $('author-name').textContent = a.full_name;
  $('author-profile').innerHTML = `<p><strong>${esc(a.institution)}</strong> · ${esc(a.country)}<br>${esc(a.department)}<br>${esc(a.role)}</p>
    <p><a href="${esc(a.source_url)}" target="_blank" rel="noopener noreferrer">Affiliation source ↗</a> · <a href="${esc(a.scopus_author_url)}" target="_blank" rel="noopener noreferrer">Scopus author profile ↗</a></p>
    <p class="review-note">${esc(a.notes || '')} Source status: ${esc(a.verification_status.replaceAll('_',' '))}.</p>
    <div class="profile-counts"><span><strong>${a.n_articles}</strong> survey-experiment articles</span><span><strong>${a.n_us_articles}</strong> US-sample articles</span><span><strong>${a.n_unclear_articles}</strong> unclear</span></div>
    <p class="review-note">Total-count rank ${a.score_rank}; US-count rank ${a.us_count_rank_within_pool} within this pool. First ${a.n_first} + last ${a.n_last} − sole ${a.n_sole} = ${a.n_articles}. If every unclear article resolved as US, the US count would be ${a.us_if_all_unclear_resolve_us}; existing labels may also change after review.</p>`;
  $('article-filter').value = 'all';
  renderAuthorArticles();
  $('author-dialog').showModal();
}
function renderAuthorArticles() {
  const a = authors.get(activeAuthor), filter = $('article-filter').value;
  const rows = a.article_ids.split('|').map(id => articles.get(id)).filter(x => filter === 'all' || (filter === 'us' ? x.sample_us_label.startsWith('us_') : x.sample_us_label === filter)).sort((x,y) => Number(y.year)-Number(x.year) || Number(x.scopus_id)-Number(y.scopus_id));
  $('article-status').textContent = `${rows.length} of ${a.n_articles} credited articles`;
  $('author-articles').innerHTML = rows.map(r => {
    const q = queued.get(r.scopus_id), local = available.get(r.scopus_id);
    return `<article class="article-card"><h3><a href="${esc(r.article_url)}" target="_blank" rel="noopener noreferrer">${esc(r.title)} ↗</a></h3>
      <p>${esc(r.year)} · ${esc(r.journal)} · <span class="badge ${r.sample_us_label}">${LABELS[r.sample_us_label]}</span>${r.us_and_non_us_samples_reported === 'true' ? ' · Also reports non-US samples' : ''}</p>
      ${r.evidence_quote ? `<blockquote>${esc(r.evidence_quote)}</blockquote><p class="review-note">Evidence: ${esc(r.evidence_field.replaceAll('_',' '))}${r.fulltext_page ? ', PDF page '+esc(r.fulltext_page) : ''}</p>` : ''}
      <p>${esc(r.rationale)}</p>${local ? `<p class="review-note">PDF saved locally; geography review pending. <code>${esc(local.local_filenames)}</code></p>` : ''}${q ? `<p><button class="secondary" data-go-batch="${q.batch}">Find in download batch ${q.batch}</button> <code>${esc(q.suggested_filename)}</code></p>` : ''}</article>`;
  }).join('');
}
function csvText(rows, fields) {
  const cell = value => '"' + String(value ?? '').replaceAll('"','""') + '"';
  return '\ufeff' + [fields.map(cell).join(','),...rows.map(r => fields.map(k => cell(r[k])).join(','))].join('\r\n');
}
function saveCSV(name, rows, fields) {
  const url = URL.createObjectURL(new Blob([csvText(rows,fields)], {type:'text/csv;charset=utf-8'}));
  const link = document.createElement('a'); link.href = url; link.download = name;
  document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url),1000);
}
async function copyText(text, message) {
  try {
    await navigator.clipboard.writeText(text);
    $('queue-status').textContent = message;
    $('copy-fallback-wrap').hidden = true;
  } catch (_) {
    $('copy-fallback-wrap').hidden = false;
    $('copy-fallback').value = text; $('copy-fallback').focus(); $('copy-fallback').select();
    $('queue-status').textContent = 'Copy the selected text below.';
  }
}
function init() {
  const s = DATA.summary;
  $('publication-window').textContent = `Explore ${s.n_authors} researchers by first/last-author article volume and evidence of US samples · Publications ${s.publication_start_year}–${s.publication_end_year}.`;
  $('review-dates').textContent = `Self-contained review dashboard · Geography reviewed through ${s.annotation_date}; profiles checked ${s.affiliation_date_min} to ${s.affiliation_date_max} · AI-assisted geography review; independent validation pending.`;
  $('stats').innerHTML = [[s.n_authors,'Researchers in the review pool',''],[s.n_unique_articles,'Distinct credited articles',''],[s.n_us_articles,'Articles with US-sample evidence','us'],[s.n_unclear_articles,'Articles awaiting geography review','pending']].map(([n,label,cls]) => `<div class="stat ${cls}"><strong>${n}</strong><span>${label}</span></div>`).join('');
  $('scope').textContent = `This pool was selected by total first/last-author article count before geography review. US sorting compares these ${s.n_authors} researchers. At the ${s.cutoff_article_count}-article cutoff, ${s.n_cutoff_tied_authors_outside_pool} other tied researchers are outside the displayed pool; this is not a global top 100 by US samples.`;
  $('methods-text').innerHTML = `<p>The primary count credits a distinct candidate article once when the researcher is its first or last author. Sole authors receive one credit. Candidate eligibility, original data fielding, parser compatibility, and access to shareable materials still require review.</p>
    <p>US-sample articles combine <strong>${s.article_counts.us_explicit} explicit</strong> and <strong>${s.article_counts.us_inferred} inferred</strong> labels from titles, abstracts, available keywords, and reviewed full texts. ${s.n_fulltext_reviewed_articles} supplied PDFs have page-cited decisions that supersede metadata labels. ${s.article_counts.non_us} articles have non-US evidence and ${s.article_counts.not_applicable} identify no applicable original experimental sample. These are article counts, not independent samples or datasets. A study's US context can support an inferred label; a US treatment evaluated by explicitly foreign respondents does not qualify.</p>
    <p>${s.n_author_article_credits} author–article credits correspond to ${s.n_unique_articles} distinct papers. First/last authorship is a proxy for possible PI involvement; alphabetical bylines can weaken it. Country describes the researcher’s work institution, independently of sample geography.</p>
    <p>${s.n_authors_tied_at_cutoff} researchers share the cutoff. Numeric author ID selects pool members within this tie. Identical total or US counts share a rank; display ordering does not establish a substantive difference. Geography labels are AI-assisted and await independent validation. Evidence and source links are available in each researcher’s details.</p>`;
  $('availability-status').textContent = `${s.n_unclear_articles} articles have unresolved geography. PDFs or supplements for ${s.n_local_pdfs_awaiting_review} are saved locally and await review; the ${s.n_manual_download_needed} papers below still need downloading. An unsuccessful automatic download does not establish that an article is paywalled.`;
  $('available-papers').innerHTML = (DATA.downloaded_pending || []).map(r => `<p><a href="${esc(r.acquired_from_url || r.article_url)}" target="_blank" rel="noopener noreferrer">${esc(r.title)}</a><br><code>${esc(r.local_filenames)}</code>${r.fulltext_review_note ? `<br>Needed: ${esc(r.needed_material)}. ${esc(r.fulltext_review_note)}` : ""}</p>`).join('') || '<p>No unresolved articles have a local PDF yet.</p>';
  $('batch').innerHTML = Array.from({length:s.n_download_batches},(_,i) => `<option value="${i+1}">${i+1} of ${s.n_download_batches}</option>`).join('');
  $('headers').addEventListener('click',event => {
    const b = event.target.closest('[data-sort]'); if (!b) return;
    const key = b.dataset.sort; setSort(key); $('headers').querySelector(`[data-sort="${key}"]`).focus();
  });
  $('people-rows').addEventListener('click',event => { const b = event.target.closest('[data-open-author]'); if (b) showAuthor(b.dataset.openAuthor); });
  $('search').addEventListener('input',renderPeople);
  $('sort-total').addEventListener('click',() => setSort('n_articles',-1));
  $('sort-us').addEventListener('click',() => setSort('n_us_articles',-1));
  for (const name of TAB_NAMES) $(name+'-tab').addEventListener('click',() => switchTab(name));
  document.querySelector('.tabs').addEventListener('keydown',event => {
    if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
    event.preventDefault();
    const current = TAB_NAMES.findIndex(name => $(name+'-tab').getAttribute('aria-selected') === 'true');
    const index = event.key === 'Home' ? 0 : event.key === 'End' ? TAB_NAMES.length-1 :
      (current + (event.key === 'ArrowRight' ? 1 : -1) + TAB_NAMES.length) % TAB_NAMES.length;
    switchTab(TAB_NAMES[index]); $(TAB_NAMES[index]+'-tab').focus();
  });
  $('copy-query').addEventListener('click',async () => {
    try {
      await navigator.clipboard.writeText(DATA.query);
      $('query-copy-status').textContent = 'Complete Scopus query copied.';
    } catch (_) {
      const selection = window.getSelection(), range = document.createRange();
      range.selectNodeContents($('summary-query')); selection.removeAllRanges(); selection.addRange(range);
      $('query-copy-status').textContent = 'Query selected. Press Command+C or Control+C to copy.';
    }
  });
  $('batch').addEventListener('change',() => { $('copy-fallback-wrap').hidden = true; renderQueue(); });
  $('queue-cards').addEventListener('change',event => {
    const sid = event.target.dataset.downloaded; if (!sid) return;
    if (event.target.checked) downloaded.add(sid); else downloaded.delete(sid);
    let persisted = true;
    try { localStorage.setItem('socialtune-downloaded-v1',JSON.stringify([...downloaded])); } catch (_) { persisted = false; }
    renderQueue(); $('queue-cards').querySelector(`[data-downloaded="${sid}"]`).focus();
    if (!persisted) $('queue-status').textContent += ' · Browser storage unavailable; progress lasts for this page session.';
  });
  $('queue-cards').addEventListener('click',event => {
    const b = event.target.closest('[data-copy-name]'); if (b) copyText(queued.get(b.dataset.copyName).suggested_filename,'Filename copied.');
  });
  $('copy-links').addEventListener('click',() => copyText(batchRows().map(r => `${r.suggested_filename}\n${r.manual_download_url || r.article_url}`).join('\n\n'),'Batch filenames and links copied.'));
  $('export-batch').addEventListener('click',() => saveCSV(`fulltext-batch-${$('batch').value}.csv`,batchRows().map(r => ({...r,marked_downloaded:downloaded.has(r.scopus_id)})),['manual_position','manual_batch','scopus_id','suggested_filename','title','manual_download_url','article_url','credited_researchers','marked_downloaded']));
  $('export-people').addEventListener('click',() => saveCSV('survey-experiment-researchers.csv',visiblePeople(),['authid',...COLS.map(c => c[0]),'n_us_explicit_articles','n_us_inferred_articles','us_count_rank_within_pool','source_url']));
  $('close-dialog').addEventListener('click',() => $('author-dialog').close());
  $('author-dialog').addEventListener('close',() => { if (lastFocused?.isConnected) lastFocused.focus(); });
  $('article-filter').addEventListener('change',renderAuthorArticles);
  $('author-articles').addEventListener('click',event => {
    const b = event.target.closest('[data-go-batch]'); if (!b) return;
    $('author-dialog').close(); $('batch').value = b.dataset.goBatch; switchTab('queue'); renderQueue(); $('batch').focus();
  });
  renderPeople(); renderQueue();
  switchTab(TAB_NAMES.find(name => TAB_HASHES[name] === location.hash.slice(1)) || 'people', false);
}
init();
