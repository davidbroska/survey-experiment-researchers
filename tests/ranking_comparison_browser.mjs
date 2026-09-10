// Isolated-browser integration checks; standard-library Node and local CDP only.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const pages=await(await fetch((process.env.CDP_URL||'http://127.0.0.1:9237')+'/json/list')).json();
const ws=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
let sequence=0;const pending=new Map(),errors=[];
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);};
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await call('Runtime.enable');await call('Page.enable');
await call('Emulation.setDeviceMetricsOverride',{width:1550,height:1050,deviceScaleFactor:1,mobile:false});
await call('Page.navigate',{url:pathToFileURL(path.join(root,'RANKING_COMPARISON.html')).href});
for(let i=0;i<60;i++){if(await evaluate('document.querySelectorAll("#rows tr[data-author]").length===100'))break;await new Promise(r=>setTimeout(r,100));}
assert.equal(await evaluate('document.querySelectorAll("#rows tr[data-author]").length'),100);
assert.equal(await evaluate('shown[0].name'),'Thomas Bernauer');
assert.equal(await evaluate('shown[0].full_all_count'),35);
assert.equal(await evaluate('DATA.authors.find(r=>r.authid==="7003917566").full_all_count'),0);
assert.equal(await evaluate('DATA.authors.find(r=>r.authid==="15520639300").current_all_count'),0);
assert.equal(await evaluate('DATA.authors.find(r=>r.authid==="15520639300").current_us_count'),null);
for(const metric of ['all','pool','us']){
  await evaluate(`$('metric').value='${metric}';$('metric').dispatchEvent(new Event('change'));`);
  for(const variant of ['full','narrow','current']){
    await evaluate(`$('variant').value='${variant}';$('variant').dispatchEvent(new Event('change'));`);
    assert.equal(await evaluate('shown.length'),100);
    const keys=await evaluate('columns($("metric").value,$("variant").value).map(c=>c[0])');
    for(const key of keys){for(let i=0;i<2;i++){
      await evaluate(`document.querySelector('[data-sort="${key}"]').click()`);
      const state=await evaluate(`({direction:sortDir,values:shown.map(r=>r[${JSON.stringify(key)}])})`);
      let missing=false;
      for(let j=0;j<state.values.length;j++){
        const value=state.values[j];if(value===null||value===undefined||value===''){missing=true;continue;}
        assert.equal(missing,false,'Unavailable values sort last');
        if(j===0)continue;
        const previous=state.values[j-1];
        const delta=key==='name'?new Intl.Collator('en',{sensitivity:'base',numeric:true}).compare(value,previous):Number(value)-Number(previous);
        assert.ok(delta*state.direction>=0,`${metric}/${variant}/${key}`);
      }
    }}
  }
}
await evaluate(`$('metric').value='all';$('variant').value='full';$('membership').value='ties';sortKey=null;draw();`);
assert.equal(await evaluate('shown.length'),114);
await evaluate(`$('membership').value='in';draw();`);assert.equal(await evaluate('shown.length'),16);
await evaluate(`$('membership').value='out';draw();`);assert.equal(await evaluate('shown.length'),16);
await evaluate(`$('membership').value='changed';draw();`);assert.equal(await evaluate('shown.length'),0);
await evaluate(`$('membership').value='all';$('search').value='Richeson';draw();`);
assert.equal(await evaluate('shown.length'),1);assert.equal(await evaluate('shown[0].full_all_count'),0);
await evaluate(`$('search').value='NO_MATCH_587143';draw();`);assert.equal(await evaluate('shown.length'),0);
await evaluate(`$('search').value='';$('metric').value='pool';$('membership').value='all';sortKey=null;draw();`);
assert.equal(await evaluate('shown.length'),120);
assert.equal(await evaluate('shown.every(r=>r.full_unreviewed===0&&r.narrow_unreviewed===0)'),true);
assert.equal(await evaluate('shown.every(r=>r.full_pool_count===r.narrow_pool_count)'),true);
assert.equal(await evaluate('csv(shown).split("\\r\\n").length'),121);
const out=path.join(root,'private/browser_checks');await fs.mkdir(out,{recursive:true});
await fs.writeFile(path.join(out,'ranking-comparison-desktop.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
await evaluate('window.scrollTo(0,0)');
assert.equal(await evaluate('document.documentElement.scrollWidth<=window.innerWidth'),true,'Mobile page does not overflow');
await fs.writeFile(path.join(out,'ranking-comparison-mobile.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
assert.deepEqual(errors,[]);
const result={passed:true,html_sha256:createHash('sha256').update(await fs.readFile(path.join(root,'RANKING_COMPARISON.html'))).digest('hex'),
  checks:['3 metrics and3 variants','all columns both directions','historical zeros versus missing US labels','114 cutoff-inclusive leaders','16 entrants and16 exits','no new-query membership differences','searchable zero-count diagnostic case','empty search','120-author uniform US coverage','identical known-US counts within pool','CSV content','desktop and mobile layout','no uncaught exceptions']};
await fs.writeFile(path.join(root,'results/query_rankings_2026_09_10/browser_check.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));ws.close();
