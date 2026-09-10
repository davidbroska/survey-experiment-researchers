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
const pages = await (await fetch('http://127.0.0.1:9224/json/list')).json();
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
assert.deepEqual(errors,[],'No uncaught browser exceptions');
const result={browser:'Google Chrome via local CDP',html_sha256:createHash('sha256').update(await fs.readFile(path.join(root,'TOP100.html'))).digest('hex'),researcher_rows:100,columns_checked_both_directions:columns.length,
  checks:['Ranking label','Methodology tab','four selection steps','literal query fidelity','copy query','three-tab keyboard navigation','downloaded PDFs omitted from manual queue','all column sorts','US maximum first','author evidence drilldown','US-only article filter','country search','empty search','ten-paper batches','last batch','download checkbox storage','CSV batch contents','mobile overflow'],uncaught_exceptions:0};
await fs.writeFile(path.join(root,'results/dashboard_browser_check.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));ws.close();
