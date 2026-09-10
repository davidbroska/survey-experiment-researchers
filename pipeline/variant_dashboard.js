'use strict';
const DATA = JSON.parse(document.getElementById('dashboard-data').textContent);
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => Number(n).toLocaleString('en-US');
const AUTHORS = new Map(DATA.authors.map(a => [a.authid, a]));
const TABS = ['ranking', 'methodology', 'downloads', 'review'];
const LABELS = {us_explicit:'Explicit US evidence',us_inferred:'Inferred US evidence',non_us:'Non-US sample',unclear:'Unclear geography',unreviewed:'Not reviewed',not_applicable:'No applicable sample'};
let sortKey = 'n_articles', direction = -1, displayed = [], queue = [], batch = [], articleLimit = 50;

function switchTab(name) {
  for (const tab of TABS) {
    const active = tab === name;
    $(tab+'-view').hidden = !active;
    $(tab+'-tab').setAttribute('aria-selected', String(active));
    $(tab+'-tab').tabIndex = active ? 0 : -1;
  }
  if (name === 'downloads') renderQueue();
  if (name === 'review') renderArticles();
}

function scopeFields(scope) {
  return scope === 'pool' ? ['pool_rank','pool_position','us_count'] :
    scope === 'global_us' ? ['us_rank','us_position','us_count'] : ['rank','position','n_articles'];
}

function selectAuthors(scope, limit, search) {
  const [rank, position, count] = scopeFields(scope);
  let rows = DATA.authors.filter(a => scope === 'pool' ? a.in_pool : a[position] !== null || (search && a.n_articles === 0));
  if (search) {
    return rows.filter(a => [a.name,a.authid,a.institution,a.department,a.country,a.role].join(' ').toLowerCase().includes(search));
  }
  if (limit === '100') rows = rows.filter(a => a[position] !== null && a[position] <= 100);
  if (limit === 'ties') rows = rows.filter(a => a[rank] !== null && a[rank] <= 100);
  return rows;
}

function columns() {
  return [['view_rank','Rank','num'],['name','Researcher','name-cell'],
    ['n_articles','Survey-experiment candidate articles','num primary'],
    ['us_count','US-sample evidence articles','num'],['n_first','First author','num'],
    ['n_last','Last author','num'],['unclear','Unclear geography','num'],
    ['unreviewed','Not reviewed','num'],['institution','Institution','aff-cell'],
    ['department','Department','dept-cell'],['country','Country','country-cell'],['role','Role','role-cell']];
}

function renderRanking() {
  const scope = $('ranking-scope').value, search = $('search').value.trim().toLowerCase();
  const [rank, position] = scopeFields(scope);
  const rows = selectAuthors(scope, $('ranking-limit').value, search).map(a => ({...a, view_rank:a[rank]}));
  const collator = new Intl.Collator('en', {sensitivity:'base',numeric:true});
  rows.sort((a,b) => {
    const x=a[sortKey], y=b[sortKey], xm=x===null||x==='', ym=y===null||y==='';
    if (xm!==ym) return xm?1:-1;
    const c = typeof x==='string' ? collator.compare(x,y) : Number(x)-Number(y);
    return c*direction || Number(a.authid)-Number(b.authid);
  });
  displayed=rows;
  const cols=columns();
  $('headers').innerHTML=cols.map(([key,label,cls])=>`<th class="${cls}" aria-sort="${key===sortKey?(direction===1?'ascending':'descending'):'none'}"><button data-sort="${key}">${esc(label)}<span class="sort-mark" aria-hidden="true">${key===sortKey?(direction===1?'↑':'↓'):'↕'}</span></button></th>`).join('');
  $('people-rows').innerHTML=rows.slice(0,1000).map(a=>'<tr>'+cols.map(([key,label,cls])=>{
    let content=esc(a[key]??'—');
    if(key==='name') content=`<button class="name-button" data-author="${a.authid}">${esc(a.name)}</button>`;
    else if(key==='n_articles') content=`<span class="count">${a.n_articles}</span><span class="number-detail">${a.n_first} first + ${a.n_last} last − ${a.n_sole} sole</span>`;
    else if(key==='us_count') content=`<span class="us-count">${a.us_count}</span><span class="number-detail">${a.us_explicit} explicit · ${a.us_inferred} inferred</span>`;
    else if(key==='unclear') content=`<span class="unclear-count">${a.unclear}</span>`;
    else if(['institution','department','country','role'].includes(key)) content=esc(a[key]||'Unknown');
    return `<td class="${cls}">${content}</td>`;
  }).join('')+'</tr>').join('')||'<tr><td colspan="12">No researchers match this selection.</td></tr>';
  const explanation=scope==='all' ?
    `Total-count ranking across ${fmt(DATA.authors.filter(a=>a.position!==null).length)} credited researchers. US counts are shown alongside totals, but coverage outside the shared 120-person pool is incomplete. Use the US-sample button for the fair comparison within the same 120 researchers.` : scope==='pool' ?
    `US-evidence ranking within the same 120 researchers on all three dashboards. All ${fmt(DATA.pool_articles)} distinct credited articles in this query have a geography judgment; ${fmt(DATA.pool_labels.unclear||0)} remain unclear. This is a conditional pool comparison, not a global US top 100.` :
    `Exploratory US-evidence ranking across all credited researchers. Many articles outside the shared 120-person pool have not been reviewed. Sorting observed US counts may favor better-reviewed authors; missing evidence is not a non-US finding.`;
  $('ranking-explanation').textContent=explanation;
  $('table-status').textContent=`${fmt(rows.length)} researchers${rows.length>1000?' · First 1,000 rendered; CSV includes all':''}${search?' · Search includes researchers beyond the top 100':''} · Equal scores retain equal ranks.`;
  $('sort-total').setAttribute('aria-pressed',String(scope==='all'));
  $('sort-us').setAttribute('aria-pressed',String(scope!=='all'));
}

function csv(rows, keys) {
  const quote=x=>'"'+String(Array.isArray(x)?x.join('|'):x??'').replaceAll('"','""')+'"';
  return [keys.map(quote).join(','),...rows.map(r=>keys.map(k=>quote(r[k])).join(','))].join('\r\n');
}
function downloadCSV(rows, keys, name) {
  const url=URL.createObjectURL(new Blob([csv(rows,keys)],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=name;a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function copy(text,status) {
  try {await navigator.clipboard.writeText(text);$(status).textContent='Copied.';}
  catch {const area=$('copy-fallback');area.hidden=false;area.value=text;area.focus();area.select();$(status).textContent='Select and copy the text below (Command+C or Control+C).';}
}
function saved(sid) {try{return localStorage.getItem('survey-recruitment-pdf:'+sid)==='saved';}catch{return false;}}
function markSaved(sid,value) {try{if(value)localStorage.setItem('survey-recruitment-pdf:'+sid,'saved');else localStorage.removeItem('survey-recruitment-pdf:'+sid);}catch{}}

function articleCard(a, queueMode=false) {
  const names=a.authors.map(id=>AUTHORS.get(id)?.name||id).map(esc).join('; ');
  const available=a.pdf_available||saved(a.sid);
  const pending=a.alternative_copy_pending&&!available;
  return `<article class="${queueMode?'queue-card':'article-card'}${available?' downloaded':''}"><h3><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a></h3>
    <p class="article-meta">${esc(a.year)} · ${esc(a.journal)} · Scopus ${esc(a.sid)}</p>
    <p><span class="badge ${esc(a.geography)}">${esc(LABELS[a.geography]||a.geography)}</span>${a.mixed?' <span class="badge">Includes US and non-US samples</span>':''} · ${a.evidence==='full_text'?'Full-text evidence':a.evidence==='metadata'?'Title/abstract/keyword evidence':'Awaiting review'} · AI-assisted</p>
    <p>${esc(a.rationale)}</p><p><strong>First/last-author credits:</strong> ${names||'Unresolved byline; no author credit'}</p>
    ${pending?`<p class="review-note"><strong>Awaiting alternative copy.</strong> ${esc(a.access_note)}</p>`:available?'<p class="review-note">PDF recorded as saved; availability does not establish review completion.</p>':''}
    ${queueMode?`<div class="actions"><a class="button secondary" href="${esc(a.url)}" target="_blank" rel="noopener">${pending?'Reference record':'Open publisher record'} ↗</a><code>${esc(a.filename)}</code><button class="secondary copy-filename" data-filename="${esc(a.filename)}">Copy filename</button><label><input type="checkbox" data-saved="${esc(a.sid)}" ${available?'checked':''} ${a.pdf_available?'disabled':''}>${a.pdf_available?'PDF recorded as saved':'Saved in my folder'}</label></div>`:''}</article>`;
}

function renderQueue() {
  const scope=$('queue-scope').value, availability=$('queue-availability').value;
  const eligible=DATA.articles.filter(a=>a.geography==='unclear'&&(scope==='all'||a.in_pool));
  queue=eligible.filter(a=>{
    const available=a.pdf_available||saved(a.sid);
    return availability==='all'||(availability==='saved'?available:availability==='pending'?a.alternative_copy_pending&&!available:!available&&!a.alternative_copy_pending);
  });
  const current=Math.max(1,Number($('queue-batch').value)||1), pages=Math.max(1,Math.ceil(queue.length/20));
  const selected=Math.min(current,pages);
  $('queue-batch').innerHTML=Array.from({length:pages},(_,i)=>`<option value="${i+1}" ${selected===i+1?'selected':''}>${i+1} of ${pages} · up to 20 articles</option>`).join('');
  batch=queue.slice((selected-1)*20,selected*20);
  const pending=eligible.filter(a=>a.alternative_copy_pending&&!a.pdf_available&&!saved(a.sid)).length;
  $('queue-status').textContent=`${fmt(queue.length)} distinct articles · ${fmt(pending)} awaiting an alternative copy under this scope. ${availability==='pending'?'Reference links are retained for locating an alternative copy; no repeat publisher download is requested.':'First prioritize records credited to researchers in the total-count or US top 50 within the shared pool. A local copy still requires evidence review.'}`;
  $('queue-cards').innerHTML=batch.map(a=>articleCard(a,true)).join('')||'<p>No articles need downloading under these filters.</p>';
}

function renderArticles() {
  const scope=$('review-scope').value, label=$('review-label').value, q=$('article-search').value.trim().toLowerCase();
  const rows=DATA.articles.filter(a=>(scope==='all'||a.in_pool)&&
    (label==='all'||(label==='us'?['us_explicit','us_inferred'].includes(a.geography):a.geography===label))&&
    (!q||[a.title,a.journal,a.doi,a.sid].join(' ').toLowerCase().includes(q)));
  $('article-status').textContent=`${fmt(rows.length)} articles · Showing ${fmt(Math.min(articleLimit,rows.length))}.`;
  $('article-cards').innerHTML=rows.slice(0,articleLimit).map(a=>articleCard(a)).join('')||'<p>No matching articles.</p>';
  $('more-articles').hidden=rows.length<=articleLimit;
}

function showAuthor(aid) {
  const a=AUTHORS.get(aid);if(!a)return;
  $('author-title').textContent=a.name;
  $('author-profile').innerHTML=`<p>${esc(a.role||'Role unknown')} · ${esc(a.department||'Department unknown')} · ${esc(a.institution||'Institution unknown')} · ${esc(a.country||'Country unknown')}</p>
    <p>${a.profile_url?`<a href="${esc(a.profile_url)}" target="_blank" rel="noopener">Profile source ↗</a> · Checked ${esc(a.profile_date||'date not supplied')}`:'A sourced affiliation profile is not yet available.'}</p><p class="review-note">${esc(a.profile_notes)}</p>
    <div class="profile-counts"><span>${a.n_articles} candidate articles</span><span>${a.us_count} US-evidence articles</span><span>${a.unclear} unclear</span><span>${a.unreviewed} unreviewed</span></div>
    <p class="compact-note">If every unclear and unreviewed article supplied US evidence, the count would be ${a.us_upper}. This is a resolution scenario, not a confidence interval or a correction for annotation error. ${a.in_pool?'This researcher belongs to the shared 120-person comparison pool.':'This researcher is outside the shared 120-person geography pool.'}</p>
    <p><a href="https://www.scopus.com/authid/detail.uri?authorId=${esc(a.authid)}" target="_blank" rel="noopener">Scopus author profile ↗</a></p>`;
  const articles=DATA.articles.filter(r=>r.authors.includes(aid)).sort((x,y)=>Number(y.year)-Number(x.year)||Number(x.sid)-Number(y.sid));
  $('author-articles').innerHTML=articles.map(r=>articleCard(r)).join('')||'<p>No candidate articles receive a first/last-author credit under this query and frame. This does not establish an absence of relevant research.</p>';
  $('author-dialog').showModal();
}

function initialize() {
  const poolUS=(DATA.pool_labels.us_explicit||0)+(DATA.pool_labels.us_inferred||0);
  $('stats').innerHTML=`<div class="stat"><strong>${fmt(DATA.retrieved)}</strong><span>Distinct articles retrieved in journal frame</span></div><div class="stat"><strong>${fmt(DATA.articles.filter(a=>a.authors.length).length)}</strong><span>Articles with complete first/last-author credits</span></div><div class="stat us"><strong>${fmt(poolUS)}</strong><span>Distinct US-evidence articles · same 120 researchers</span></div><div class="stat pending"><strong>${fmt(DATA.pool_labels.unclear||0)}</strong><span>Unclear sample geography · same 120 researchers</span></div>`;
  $('build-date').textContent=`Shared evidence snapshot ${DATA.snapshot_date}. Query version fixed on this page; annotations remain provisional.`;
  for(const tab of TABS)$(tab+'-tab').addEventListener('click',()=>switchTab(tab));
  document.querySelector('.tabs').addEventListener('keydown',e=>{if(!['ArrowRight','ArrowLeft','Home','End'].includes(e.key))return;e.preventDefault();const i=TABS.findIndex(t=>$(t+'-tab').getAttribute('aria-selected')==='true');const n=e.key==='Home'?0:e.key==='End'?TABS.length-1:(i+(e.key==='ArrowRight'?1:-1)+TABS.length)%TABS.length;switchTab(TABS[n]);$(TABS[n]+'-tab').focus();});
  $('headers').addEventListener('click',e=>{const b=e.target.closest('[data-sort]');if(!b)return;const key=b.dataset.sort;direction=key===sortKey?-direction:key==='view_rank'||typeof (DATA.authors[0][key])==='string'?1:-1;sortKey=key;renderRanking();});
  $('people-rows').addEventListener('click',e=>{const b=e.target.closest('[data-author]');if(b)showAuthor(b.dataset.author);});
  $('close-author').addEventListener('click',()=>$('author-dialog').close());
  for(const id of ['ranking-scope','ranking-limit'])$(id).addEventListener('change',()=>{sortKey=$('ranking-scope').value==='all'?'n_articles':'us_count';direction=-1;renderRanking();});
  $('search').addEventListener('input',renderRanking);
  $('sort-total').addEventListener('click',()=>{$('ranking-scope').value='all';sortKey='n_articles';direction=-1;renderRanking();});
  $('sort-us').addEventListener('click',()=>{$('ranking-scope').value='pool';sortKey='us_count';direction=-1;renderRanking();});
  $('export-people').addEventListener('click',()=>downloadCSV(displayed,Object.keys(DATA.authors[0]).concat('view_rank'),`researchers-${DATA.key}-${$('ranking-scope').value}.csv`));
  $('copy-query').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(DATA.query);$('query-copy-status').textContent='Literal query copied.';}catch{const area=$('query-copy-fallback');area.hidden=false;area.value=DATA.query;area.focus();area.select();$('query-copy-status').textContent='Literal query selected below. Press Command+C or Control+C to copy.';}});
  for(const id of ['queue-scope','queue-availability','queue-batch'])$(id).addEventListener('change',renderQueue);
  $('copy-queue').addEventListener('click',()=>copy(batch.map(a=>`${a.filename}\n${a.title}\n${a.url}`).join('\n\n'),'queue-status'));
  $('export-queue').addEventListener('click',()=>downloadCSV(queue,['sid','filename','title','year','journal','doi','url','geography','rationale','pdf_available','alternative_copy_pending','access_note'],`fulltext-queue-${DATA.key}.csv`));
  $('queue-cards').addEventListener('change',e=>{if(e.target.matches('[data-saved]')){markSaved(e.target.dataset.saved,e.target.checked);renderQueue();}});
  $('queue-cards').addEventListener('click',e=>{const b=e.target.closest('[data-filename]');if(b)copy(b.dataset.filename,'queue-status');});
  for(const id of ['review-scope','review-label'])$(id).addEventListener('change',()=>{articleLimit=50;renderArticles();});
  $('article-search').addEventListener('input',()=>{articleLimit=50;renderArticles();});
  $('more-articles').addEventListener('click',()=>{articleLimit+=50;renderArticles();});
  renderRanking();
}
initialize();
