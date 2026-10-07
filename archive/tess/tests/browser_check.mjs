// Integration checks against a separately launched local headless Chrome (CDP port 9224).
// No npm packages, external websites, or user browser profile are used.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const out = path.join(root,'private/browser_checks');
await fs.mkdir(out,{recursive:true});
const pages = await (await fetch((process.env.CDP_URL || 'http://127.0.0.1:9224')+'/json/list')).json();
const ws = new WebSocket(pages.find(p => p.type === 'page').webSocketDebuggerUrl);
await new Promise((resolve,reject) => {ws.onopen=resolve;ws.onerror=reject;});
let seq=0;const pending=new Map(),errors=[];
ws.onmessage = event => {const msg=JSON.parse(event.data);if(msg.id){const p=pending.get(msg.id);pending.delete(msg.id);msg.error?p.reject(msg.error):p.resolve(msg.result);}if(msg.method==='Runtime.exceptionThrown')errors.push(msg.params.exceptionDetails);};
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await call('Runtime.enable');await call('Page.enable');
await call('Emulation.setDeviceMetricsOverride',{width:1600,height:1040,deviceScaleFactor:1,mobile:false});
await call('Page.navigate',{url:process.env.DASHBOARD_URL || pathToFileURL(path.join(root,'TOP100.html')).href});
for(let i=0;i<30;i++){if(await evaluate('document.querySelectorAll("#people-rows tr[data-author]").length===100'))break;await new Promise(r=>setTimeout(r,100));}
assert.equal(await evaluate('document.querySelectorAll("#people-rows tr[data-author]").length'),100);
assert.equal(await evaluate('document.getElementById("people-tab").textContent'),'Ranking');
assert.equal(await evaluate('document.getElementById("summary-tab").textContent'),'Methodology');
await evaluate('document.getElementById("summary-tab").click()');
assert.equal(await evaluate('document.getElementById("summary-view").hidden'),false);
assert.equal(await evaluate('document.querySelectorAll(".selection-steps > li").length'),4);
assert.equal(await evaluate('document.getElementById("summary-query").textContent'),await evaluate('DATA.query'));
assert.ok((await evaluate('DATA.query')).includes('PUBYEAR > 2009'));
await evaluate('Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:async text=>{window.testCopiedQuery=text;}}});document.getElementById("copy-query").click()');
assert.equal(await evaluate('window.testCopiedQuery'),await evaluate('DATA.query'));
await fs.writeFile(path.join(out,'coauthor-summary.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
await evaluate('document.getElementById("summary-tab").dispatchEvent(new KeyboardEvent("keydown",{key:"ArrowRight",bubbles:true}))');
assert.equal(await evaluate('document.getElementById("queue-view").hidden'),false);
await evaluate('document.getElementById("queue-tab").dispatchEvent(new KeyboardEvent("keydown",{key:"Home",bubbles:true}))');
assert.equal(await evaluate('document.getElementById("people-view").hidden'),false);
assert.equal(await evaluate('DATA.queue.length + DATA.downloaded_pending.length'),await evaluate('DATA.summary.n_unclear_articles'));
assert.equal(await evaluate('DATA.queue.some(r=>available.has(r.scopus_id))'),false);
const columns=await evaluate('COLS');
for(const [key,label,type] of columns){
  for(let click=0;click<2;click++){
    await evaluate(`document.querySelector('[data-sort="${key}"]').click()`);
    const check=await evaluate(`({sort:document.querySelector('[data-sort="${key}"]').closest('th').getAttribute('aria-sort'), values:[...document.querySelectorAll('#people-rows tr[data-author]')].map(r=>authors.get(r.dataset.author)[${JSON.stringify(key)}])})`);
    const direction=check.sort==='ascending'?1:-1;
    for(let i=1;i<check.values.length;i++){
      const delta=type==='number'?Number(check.values[i])-Number(check.values[i-1]):new Intl.Collator('en',{sensitivity:'base',numeric:true}).compare(check.values[i],check.values[i-1]);
      assert.ok(delta*direction>=0,`${label} sorted ${check.sort}`);
    }
  }
}
await evaluate('document.getElementById("sort-total").click()');
await fs.writeFile(path.join(out,'desktop.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
await evaluate('document.getElementById("sort-us").click()');
assert.equal(await evaluate('sortKey'),'n_us_articles');
const maximum=await evaluate('Math.max(...DATA.authors.map(a=>a.n_us_articles))');
assert.equal(await evaluate('authors.get(document.querySelector("#people-rows tr").dataset.author).n_us_articles'),maximum);
await evaluate('document.querySelector("[data-open-author]").click()');
assert.equal(await evaluate('document.getElementById("author-dialog").open'),true);
await evaluate('document.getElementById("article-filter").value="us";document.getElementById("article-filter").dispatchEvent(new Event("change"))');
assert.equal(await evaluate('document.querySelectorAll("#author-articles .article-card").length'),maximum);
await fs.writeFile(path.join(out,'article-evidence.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
await evaluate('document.getElementById("close-dialog").click();document.getElementById("search").value="Germany";document.getElementById("search").dispatchEvent(new Event("input"))');
assert.equal(await evaluate('document.querySelectorAll("#people-rows tr[data-author]").length'),await evaluate('DATA.authors.filter(a=>a.country==="Germany").length'));
await evaluate('document.getElementById("search").value="NO_MATCH_84620";document.getElementById("search").dispatchEvent(new Event("input"))');
assert.equal(await evaluate('document.querySelectorAll("#people-rows tr[data-author]").length'),0);
await evaluate('document.getElementById("search").value="";document.getElementById("search").dispatchEvent(new Event("input"));document.getElementById("queue-tab").click()');
assert.equal(await evaluate('document.getElementById("queue-view").hidden'),false);
assert.equal(await evaluate('document.querySelectorAll(".queue-card").length'),10);
const sid=await evaluate('DATA.queue[0].scopus_id');
await evaluate(`document.querySelector('[data-downloaded="${sid}"]').click()`);
assert.equal(await evaluate(`downloaded.has('${sid}')`),true);
assert.equal(await evaluate(`JSON.parse(localStorage.getItem('socialtune-downloaded-v1')).includes('${sid}')`),true);
await evaluate(`document.querySelector('[data-downloaded="${sid}"]').click()`);
await evaluate('document.getElementById("batch").value=String(DATA.summary.n_download_batches);document.getElementById("batch").dispatchEvent(new Event("change"))');
assert.equal(await evaluate('document.querySelectorAll(".queue-card").length'),await evaluate('DATA.queue.length % 10 || 10'));
await evaluate('document.getElementById("batch").value="1";document.getElementById("batch").dispatchEvent(new Event("change"))');
await fs.writeFile(path.join(out,'download-queue.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
assert.ok((await evaluate('csvText(batchRows(),["suggested_filename","article_url"])')).includes(sid+'.pdf'));
await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
await evaluate('document.getElementById("people-tab").click();document.getElementById("sort-total").click();window.scrollTo(0,0)');
assert.equal(await evaluate('document.documentElement.scrollWidth<=window.innerWidth'),true,'No page-level horizontal overflow on mobile');
await fs.writeFile(path.join(out,'mobile.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
await evaluate('document.getElementById("summary-tab").click();window.scrollTo(0,0)');
assert.equal(await evaluate('document.documentElement.scrollWidth<=window.innerWidth'),true,'No summary overflow on mobile');
await fs.writeFile(path.join(out,'mobile-summary.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
assert.equal(await evaluate('document.querySelector("#summary-view a[href=\\"QUERY_REVISION.html\\"]").textContent.includes("revised query")'),true);
assert.equal(await evaluate('document.querySelector("#summary-view a[href=\\"SEARCH_STRATEGY.html\\"]").textContent.includes("search audit")'),true);
assert.equal(await evaluate('document.querySelector("#summary-view .scope").textContent.includes("remains provisional")'),true);
const dashboardUrl=process.env.DASHBOARD_URL || pathToFileURL(path.join(root,'TOP100.html')).href;
await call('Page.navigate',{url:new URL('QUERY_REVISION.html',dashboardUrl).href});
for(let i=0;i<40;i++){if(await evaluate('location.pathname.endsWith("QUERY_REVISION.html") && !!document.querySelector("pre code")'))break;await new Promise(r=>setTimeout(r,100));}
const normalizeQuery=text=>text.replace(/\s+/g,' ').trim();
assert.equal(normalizeQuery(await evaluate('document.querySelector("pre code").textContent')),normalizeQuery(await fs.readFile(path.join(root,'queries/revision_2026_09_10/revised.txt'),'utf8')));
assert.ok(await evaluate('document.body.textContent.includes("8,074")'));
assert.equal(await evaluate('document.documentElement.scrollWidth<=window.innerWidth'),true,'No revision-report overflow on mobile');
await fs.writeFile(path.join(out,'revision-mobile.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
await call('Emulation.setDeviceMetricsOverride',{width:1600,height:1040,deviceScaleFactor:1,mobile:false});
await fs.writeFile(path.join(out,'revision-desktop.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
await call('Page.navigate',{url:new URL('SEARCH_STRATEGY.html',dashboardUrl).href});
for(let i=0;i<40;i++){if(await evaluate('location.pathname.endsWith("SEARCH_STRATEGY.html") && !!document.querySelector("pre code")'))break;await new Promise(r=>setTimeout(r,100));}
const candidateQuery=normalizeQuery(await fs.readFile(path.join(root,'queries/search_strategy_2026_09_10/candidate.txt'),'utf8'));
assert.equal(normalizeQuery(await evaluate('document.querySelector("pre code").textContent')),candidateQuery,'Audit shows the executed candidate query');
assert.ok(await evaluate('document.body.textContent.includes("18,054")'),'Audit shows the candidate retrieval count');
assert.ok(await evaluate('!!document.querySelector("a[href=\\"SEARCH_SUMMARY.html\\"]")'),'Audit links the coauthor note');
assert.ok(await evaluate('!!document.querySelector("a[href=\\"SEARCH_METHODS.html\\"]")'),'Audit links the supporting-information draft');
await fs.writeFile(path.join(out,'search-strategy-desktop.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
await evaluate('window.scrollTo(0,0)');
assert.equal(await evaluate('document.documentElement.scrollWidth<=window.innerWidth'),true,'No search-audit overflow on mobile');
await fs.writeFile(path.join(out,'search-strategy-mobile.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
await call('Page.navigate',{url:new URL('SEARCH_METHODS.html',dashboardUrl).href});
for(let i=0;i<40;i++){if(await evaluate('location.pathname.endsWith("SEARCH_METHODS.html") && !!document.querySelector("pre code")'))break;await new Promise(r=>setTimeout(r,100));}
assert.equal(normalizeQuery(await evaluate('document.querySelector("pre code").textContent')),candidateQuery,'SI draft shows the same executed query');
assert.equal(await evaluate('document.documentElement.scrollWidth<=window.innerWidth'),true,'No search-methods overflow on mobile');
await call('Page.navigate',{url:new URL('PROXIMITY_AUDIT.html',dashboardUrl).href});
for(let i=0;i<40;i++){if(await evaluate('location.pathname.endsWith("PROXIMITY_AUDIT.html") && document.querySelectorAll("pre code").length===2'))break;await new Promise(r=>setTimeout(r,100));}
const proximityQuery=normalizeQuery(await fs.readFile(path.join(root,'queries/proximity_audit_2026_09_10/targeted.txt'),'utf8'));
assert.equal(normalizeQuery(await evaluate('document.querySelectorAll("pre code")[1].textContent')),proximityQuery,'Proximity report query fidelity');
assert.ok(await evaluate('document.body.textContent.includes("9,675")'),'Proximity report retrieval count');
assert.equal(await evaluate('document.documentElement.scrollWidth<=window.innerWidth'),true,'No proximity-report mobile overflow');
await call('Page.navigate',{url:new URL('PROXIMITY_METHODS.html',dashboardUrl).href});
for(let i=0;i<40;i++){if(await evaluate('location.pathname.endsWith("PROXIMITY_METHODS.html") && !!document.querySelector("pre code")'))break;await new Promise(r=>setTimeout(r,100));}
const specificQuery=normalizeQuery(await fs.readFile(path.join(root,'queries/proximity_specific_2026_09_10/primary_plus_specific.txt'),'utf8'));
assert.equal(normalizeQuery(await evaluate('document.querySelector("pre code").textContent')),specificQuery,'Proximity SI development query fidelity');
assert.ok(await evaluate('document.body.textContent.includes("9,365")'),'Post-benchmark development retrieval count');
await call('Page.navigate',{url:new URL('FULLTEXT_BENCHMARK.html',dashboardUrl).href});
for(let i=0;i<40;i++){if(await evaluate('location.pathname.endsWith("FULLTEXT_BENCHMARK.html") && document.querySelectorAll(".card").length===60'))break;await new Promise(r=>setTimeout(r,100));}
assert.equal(await evaluate('DATA.length'),60,'Fixed benchmark retains all sampled articles');
assert.equal(await evaluate('document.querySelectorAll(".card").length'),60);
await evaluate('document.getElementById("filter").value="ready";document.getElementById("filter").dispatchEvent(new Event("change"))');
assert.equal(await evaluate('document.querySelectorAll(".card").length'),await evaluate('DATA.filter(r=>r.fulltext_readiness==="ready_for_fulltext_review").length'));
await evaluate('document.getElementById("filter").value="missing";document.getElementById("filter").dispatchEvent(new Event("change"))');
assert.equal(await evaluate('document.querySelectorAll(".card").length'),await evaluate('DATA.filter(r=>r.fulltext_readiness!=="ready_for_fulltext_review").length'));
await evaluate('Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:async text=>{window.testFilename=text;}}});document.querySelector("[data-copy]").click()');
assert.equal(await evaluate('window.testFilename'),await evaluate('document.querySelector("[data-copy]").dataset.copy'));
await evaluate('document.getElementById("search").value="NO_MATCH_9876";document.getElementById("search").dispatchEvent(new Event("input"))');
assert.equal(await evaluate('document.querySelectorAll(".card").length'),0);
await evaluate('document.getElementById("search").value="";document.getElementById("search").dispatchEvent(new Event("input"))');
assert.equal(await evaluate('document.documentElement.scrollWidth<=window.innerWidth'),true,'No fulltext-benchmark mobile overflow');
await fs.writeFile(path.join(out,'fulltext-benchmark-mobile.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
await call('Emulation.setDeviceMetricsOverride',{width:1600,height:1040,deviceScaleFactor:1,mobile:false});
await fs.writeFile(path.join(out,'fulltext-benchmark-desktop.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
assert.deepEqual(errors,[],'No uncaught browser exceptions');
const result={browser:'Google Chrome via local CDP',html_sha256:createHash('sha256').update(await fs.readFile(path.join(root,'TOP100.html'))).digest('hex'),researcher_rows:100,columns_checked_both_directions:columns.length,
  checks:['Ranking label','Methodology tab','four selection steps','literal query fidelity','copy query','three-tab keyboard navigation','downloaded PDFs omitted from manual queue','all column sorts','US maximum first','author evidence drilldown','US-only article filter','country search','empty search','ten-paper batches','last batch','download checkbox storage','CSV batch contents','mobile overflow','revision report link','revised query fidelity','revision report counts','revision report mobile overflow','search audit link','provisional cohort notice','candidate query fidelity','candidate retrieval count','coauthor and SI links','search audit mobile overflow','SI candidate query fidelity','SI mobile overflow'],uncaught_exceptions:0};
result.checks.push('proximity query and SI fidelity','proximity retrieval count','proximity mobile layout','all60 benchmark records','benchmark availability filters','benchmark filename copy','benchmark search','benchmark mobile layout');
await fs.writeFile(path.join(root,'results/dashboard_browser_check.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));ws.close();
