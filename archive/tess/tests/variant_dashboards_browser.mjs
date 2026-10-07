// Local isolated Chrome/CDP checks. No external publisher or profile links open.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const pages=await(await fetch((process.env.CDP_URL||'http://127.0.0.1:9239')+'/json/list')).json();
const ws=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
let sequence=0;const pending=new Map(),errors=[];
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);};
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await call('Runtime.enable');await call('Page.enable');
const hashes={};
for(const key of ['original','complete','narrower']) {
  const file=`DASHBOARD_${key.toUpperCase()}.html`;
  await call('Emulation.setDeviceMetricsOverride',{width:1600,height:1050,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:pathToFileURL(path.join(root,file)).href});
  for(let i=0;i<100;i++){if(await evaluate(`typeof DATA!=='undefined'&&DATA.key==='${key}'&&document.querySelectorAll('#people-rows tr').length===100`))break;await new Promise(r=>setTimeout(r,100));}
  assert.equal(await evaluate('displayed.length'),100);
  assert.equal(await evaluate('displayed[0].name'),'Douglas L. Kriner');
  assert.equal(await evaluate('rankingMode'), 'us');
  assert.equal(await evaluate('displayed.every(a=>a.in_pool&&a.unreviewed===0)'),true);
  assert.deepEqual(await evaluate('columns().slice(2,4).map(c=>c[0])'),['us_count','n_articles']);
  assert.ok(await evaluate(`document.querySelector('[data-sort="us_count"]').closest('th').classList.contains('primary')`));
  assert.deepEqual(await evaluate(`Array.from(document.querySelectorAll('[role="tab"]')).map(n=>n.textContent)`),['Ranking','Methodology']);
  assert.equal(await evaluate(`$('review-tools').open`),false);
  assert.equal(await evaluate(`$('ranking-scope')`),null);
  assert.equal(await evaluate(`$('stats').closest('#ranking-view')!==null`),true);
  assert.equal(await evaluate(`!!(document.querySelector('.table-wrap').compareDocumentPosition($('stats'))&Node.DOCUMENT_POSITION_FOLLOWING)`),true);
  assert.equal(await evaluate(`document.body.innerText.toLowerCase().includes('cohort')`),false);
  assert.equal(await evaluate(`Array.from(document.querySelectorAll('a[href]')).some(a=>/DASHBOARD_|TOP100|COMPARISON|BENCHMARK/.test(a.getAttribute('href')))`),false);
  for(const [column] of await evaluate('columns()')) {
    for(let j=0;j<2;j++) {
      await evaluate(`document.querySelector('[data-sort="${column}"]').click()`);
      const state=await evaluate(`({direction,values:displayed.map(a=>a[${JSON.stringify(column)}])})`);
      let missing=false;
      for(let i=0;i<state.values.length;i++) {
        const value=state.values[i];if(value===null||value===''){missing=true;continue;}
        assert.equal(missing,false,'Unknowns must sort after known values');
        if(!i)continue;const previous=state.values[i-1];
        const delta=typeof value==='string'?new Intl.Collator('en',{sensitivity:'base',numeric:true}).compare(value,previous):value-previous;
        assert.ok(delta*state.direction>=0,`${key}/${column}`);
      }
    }
  }
  await evaluate(`$('sort-total').click()`);
  const totalView=await evaluate('displayed.map(a=>[a.authid,a.view_rank])');
  await evaluate(`$('sort-us').click()`);
  const usView=await evaluate('displayed.map(a=>[a.authid,a.view_rank])');
  await evaluate(`document.querySelector('[data-sort="n_articles"]').click()`);
  assert.deepEqual(await evaluate('displayed.map(a=>[a.authid,a.view_rank])'),totalView);
  await evaluate(`document.querySelector('[data-sort="us_count"]').click()`);
  assert.deepEqual(await evaluate('displayed.map(a=>[a.authid,a.view_rank])'),usView);
  await evaluate(`$('sort-total').click()`);
  assert.equal(await evaluate('displayed[0].name'),'Thomas Bernauer');
  assert.equal(await evaluate('displayed[0].n_articles'),key==='original'?33:35);
  assert.equal(await evaluate('displayed.every(a=>a.in_pool)'),true);
  await evaluate(`$('ranking-limit').value='ties';$('ranking-limit').dispatchEvent(new Event('change'))`);
  assert.equal(await evaluate('displayed.length'),key==='original'?110:114);
  await evaluate(`$('search').value='Willer';$('search').dispatchEvent(new Event('input'))`);
  assert.equal(await evaluate('displayed.length'),1);
  assert.equal(await evaluate('displayed[0].name'),'Robb Willer');
  await evaluate(`document.querySelector('[data-author]').click()`);
  assert.equal(await evaluate(`$('author-dialog').open`),true);
  assert.ok(await evaluate(`document.querySelectorAll('#author-articles .article-card').length===displayed[0].n_articles`));
  await evaluate(`$('close-author').click();$('search').value='';$('ranking-limit').value='100';$('sort-us').click()`);
  assert.equal(await evaluate('displayed.length'),100);
  assert.equal(await evaluate('displayed[0].name'),'Douglas L. Kriner');
  await evaluate(`$('ranking-limit').value='all';$('ranking-limit').dispatchEvent(new Event('change'))`);
  assert.equal(await evaluate('displayed.length'),120);
  assert.equal(await evaluate('displayed.every(a=>a.in_pool&&a.unreviewed===0)'),true);
  assert.equal(await evaluate(`csv(displayed,['authid','name','n_articles','us_count']).split('\\r\\n').length`),121);
  await evaluate(`$('methodology-tab').click()`);
  assert.equal(await evaluate(`$('methodology-view').hidden`),false);
  assert.equal(await evaluate(`$('literal-query').checkVisibility()`),true);
  assert.equal(await evaluate(`document.querySelector('.methods-details')`),null);
  assert.equal(await evaluate(`$('methodology-view').textContent.includes('Counting and affiliation details')`),false);
  assert.equal(await evaluate(String.raw`JSON.stringify($('literal-query').textContent.match(/"[^"\\]*(?:\\.[^"\\]*)*"|\{[^}]*\}|[()]|[^\s(){}"]+/g))===JSON.stringify(DATA.query.match(/"[^"\\]*(?:\\.[^"\\]*)*"|\{[^}]*\}|[()]|[^\s(){}"]+/g))`),true);
  assert.ok(await evaluate(`$('literal-query').textContent.includes('PUBYEAR > 2009')`));
  await evaluate(`Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw new Error('Clipboard unavailable in test')}}});$('copy-query').click()`);
  await new Promise(r=>setTimeout(r,30));
  assert.equal(await evaluate(`!$('query-copy-fallback').hidden&&$('query-copy-fallback').value===DATA.query`),true);
  await evaluate(`$('ranking-tab').click();$('review-tools').open=true;$('downloads-tab').click()`);
  assert.equal(await evaluate('batch.every(a=>a.geography==="unclear"&&a.in_pool)'),true);
  assert.equal(await evaluate('queue.every(a=>!a.pdf_available&&!a.alternative_copy_pending&&!saved(a.sid))'),true);
  assert.ok(await evaluate('new Set(queue.map(a=>a.sid)).size===queue.length'));
  await evaluate(`Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.copiedText=text}}});$('copy-queue').click()`);
  await new Promise(r=>setTimeout(r,50));
  assert.equal(await evaluate(`window.copiedText===batch.map(a=>a.filename+'\\n'+a.title+'\\n'+a.url).join('\\n\\n')`),true);
  await evaluate(`$('queue-availability').value='pending';$('queue-availability').dispatchEvent(new Event('change'))`);
  assert.ok(await evaluate('queue.length>0&&queue.every(a=>a.alternative_copy_pending&&!a.pdf_available&&!saved(a.sid))'));
  assert.ok(await evaluate(`$('queue-cards').textContent.includes('Awaiting alternative copy')`));
  assert.equal(await evaluate(`$('queue-cards').textContent.includes('Open publisher record')`),false);
  await evaluate(`$('queue-availability').value='needed';$('queue-availability').dispatchEvent(new Event('change'))`);
  await evaluate(`$('review-tab').click();$('review-label').value='unclear';$('review-label').dispatchEvent(new Event('change'))`);
  assert.equal(await evaluate(`document.querySelectorAll('#article-cards .badge.unclear').length`),50);
  await evaluate(`$('ranking-tab').click();$('review-tools').open=false;$('sort-us').click();$('ranking-limit').value='100';$('ranking-limit').dispatchEvent(new Event('change'));window.scrollTo(0,0)`);
  const out=path.join(root,'private/variant_dashboard_browser');await fs.mkdir(out,{recursive:true});
  await fs.writeFile(path.join(out,key+'-desktop.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert.equal(await evaluate('document.documentElement.scrollWidth<=window.innerWidth'),true,'Mobile page width');
  await fs.writeFile(path.join(out,key+'-mobile.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  hashes[file]=createHash('sha256').update(await fs.readFile(path.join(root,file))).digest('hex');
}
assert.deepEqual(errors,[]);
const result={passed:true,output_sha256:hashes,checks:['three standalone query presentations with no comparison links','US default within120 and primary US column before total','both ranking modes within same120','every ranking column in both directions','110/114/114 cutoff-inclusive total leaders within120','Robb Willer detail dialog','same120 with no unreviewed articles','readable methodology and exact query copying','collapsed secondary review tools','deduplicated unresolved download queue','saved and unavailable articles omitted from routine batches','alternative-copy filter with reference links','batch copy and CSV contents','article evidence filter','desktop and mobile layouts','no uncaught exceptions']};
await fs.writeFile(path.join(root,'results/variant_dashboards_2026_09_10/browser_check.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));ws.close();
