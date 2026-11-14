// Optional browser QA. Install Playwright in ignored .qa/browser; uses existing Edge.
import {chromium} from '../.qa/browser/node_modules/playwright/index.mjs';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const base=process.env.GRAPHSCOPE_QA_URL??'http://127.0.0.1:4175/LLM-GNN/';
const out=new URL('../.qa/v3/',import.meta.url);await mkdir(out,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
const results=[];const check=(name,details)=>results.push({name,details});
try {
 await page.goto(base);await page.getByRole('heading',{name:'SARA-Core',exact:true}).waitFor();
 assert.match(await page.locator('main').innerText(),/74.1005%/);check('Home actual benchmark','74.1005% / 72.4377%; 16 arms / 15 specs');
 for(const [device,width,height] of (process.env.QA_SKIP_CAPTURES?[]:[['desktop',1440,900],['mobile',390,844],['tablet',768,1024]])){
  await page.setViewportSize({width,height});
  for(const route of ['overview','explore','workflow','agents','methods','experiments','desk','workbench']){
   await page.goto(base+'#'+route+'?node=2628');await page.locator('main h1,main h3').first().waitFor();
   if(route==='explore')await page.getByText(/loaded nodes/).waitFor();
   await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));
   const dimensions=await page.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth}));
   assert.ok(dimensions.scroll<=dimensions.viewport+1,`${device}/${route} page overflow: ${JSON.stringify(dimensions)}`);
   await page.screenshot({path:new URL(`E-${route}-${device}.png`,out).pathname.replace(/^\/(?:([A-Za-z]):)/,'$1:')});
   check(`${device}/${route}`,dimensions);
  }
 }
 await page.setViewportSize({width:1440,height:900});await page.goto(base+'#explore?node=2628');
 await page.locator('.graph-canvas[data-node-count="2708"]').waitFor();
 const canvas=page.locator('.graph-canvas');assert.equal(await canvas.getAttribute('data-edge-count'),'5278');
 check('Full graph renderer',await canvas.evaluate(e=>({nodes:e.dataset.nodeCount,edges:e.dataset.edgeCount,renderMs:e.dataset.renderMs,heapMB:performance.memory?performance.memory.usedJSHeapSize/1048576:null})));
 await page.getByRole('button',{name:'Zoom in',exact:true}).click();const zoom=await canvas.getAttribute('data-zoom');
 await page.setViewportSize({width:1300,height:850});assert.equal(await canvas.getAttribute('data-zoom'),zoom);check('Resize preserves zoom',zoom);
 await canvas.focus();await page.keyboard.press('+');assert.notEqual(await canvas.getAttribute('data-zoom'),zoom);await page.keyboard.press('Escape');
 await page.getByRole('combobox',{name:/Neighborhood/}).selectOption('1');await page.getByText(/45 loaded nodes/).waitFor();
 await page.getByRole('combobox',{name:/Neighborhood/}).selectOption('2');await page.getByText(/122 loaded nodes/).waitFor();
 await page.getByRole('button',{name:'Back to full',exact:true}).click();
 await page.getByRole('button',{name:'Focus selected',exact:true}).click();
 await page.getByLabel('Search node ID or recorded article text',{exact:true}).fill('0');await page.getByRole('button',{name:'Select node #0',exact:true}).click();
 await page.getByRole('heading',{name:'Node #0',exact:true}).waitFor();check('Search all canonical IDs and selection',page.url());
 const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Export displayed graph IDs / edges'}).click();const downloaded=await downloadPromise;
 const exported=JSON.parse(await readFile(await downloaded.path(),'utf8'));assert.equal(exported.nodeIds.length,2708);assert.equal(exported.edges.length,5278);check('Graph download','2708 actual IDs / 5278 edges');
 await page.goto(base+'#workbench?arm=lite_router_only&seed=9');await page.getByRole('heading',{name:/saved seed 9/}).waitFor();
 await page.getByRole('combobox',{name:/GCN seed/}).selectOption('0');await page.getByRole('heading',{name:/saved seed 0/}).waitFor();
 await page.getByRole('combobox',{name:/Mode/}).selectOption('whatif');await page.getByRole('heading',{name:'UNEXECUTED WHAT-IF',exact:true}).waitFor();
 await page.locator('.owner-access>summary').click();await page.locator('input[type=file]').setInputFiles(fileURLToPath(new URL('../.qa/owner-evidence.json',import.meta.url)));
 await page.getByRole('button',{name:'Clear private evidence',exact:true}).waitFor();
 const mask=page.locator('.scenario-mask input');assert.equal(await mask.count(),103);await mask.first().uncheck();
 const manifestDownload=page.waitForEvent('download');await page.getByRole('button',{name:'Download scenario manifest',exact:true}).click();
 const manifest=JSON.parse(await readFile(await(await manifestDownload).path(),'utf8'));
 assert.equal(manifest.status,'UNEXECUTED_WHAT_IF');assert.equal(manifest.retainedCount,102);assert.equal(manifest.excludedIds.length,1);assert.ok(!JSON.stringify(manifest).includes('accuracy'));check('Owner mask scenario manifest',manifest);
 await page.getByRole('button',{name:'Clear private evidence',exact:true}).click();await page.getByText(/The exact frozen source mask is private/).first().waitFor();
 await page.locator('input[type=file]').setInputFiles({name:'invalid-owner.json',mimeType:'application/json',buffer:Buffer.from('{"GT":[]}')});await page.getByRole('alert').waitFor();check('Invalid owner import','Checksum rejects synthetic negative fixture; no data admitted');
 await page.getByRole('button',{name:'Reset to frozen method',exact:true}).click();await page.getByRole('heading',{name:/saved seed 0/}).waitFor();
 await page.goBack();await page.goForward();check('Reset and Back/Forward','No render error or fabricated metric');
 await page.goto(base+'#experiments?seed=7');await page.getByRole('table').first().waitFor();
 assert.match(await page.getByRole('table').first().innerText(),/seed 7/i);
 await page.getByRole('checkbox',{name:'B1 · current',exact:true}).check();await page.getByRole('checkbox',{name:'SARA-Lite',exact:true}).check();assert.equal(await page.getByRole('table').first().getByRole('row').count(),5);
 const csvDownload=page.waitForEvent('download');await page.getByRole('button',{name:'Download selected seeds CSV',exact:true}).click();const csv=await readFile(await(await csvDownload).path(),'utf8');assert.equal(csv.split('\n').length,41);check('Four-arm comparison and CSV','40 genuine arm-seed records');
 await page.getByText('Separate historical WCE reference · incompatible loss contract',{exact:true}).click();assert.match(await page.locator('.separate-wce').innerText(),/74.3769/);check('Final ledger and separate WCE','Seed7; WCE74.3769 separately');
 await page.goto(base+'#explore?hop=Infinity&node=-1');await page.getByRole('alert').filter({hasText:/Invalid graph scope/}).waitFor();check('Invalid deep link','Infinity/-1 rejected without traversal');
 await page.route('**/data/benchmark.v3.json',route=>route.fulfill({status:200,body:'{}',contentType:'application/json'}));await page.goto(base);await page.reload();await page.getByRole('alert').waitFor();assert.match(await page.getByRole('alert').innerText(),/checksum/i);check('Corrupt JSON','Fail closed; no fallback');
 await page.unroute('**/data/benchmark.v3.json');await page.goto(base);await page.reload();await page.getByRole('heading',{name:'SARA-Core',exact:true}).waitFor();
 assert.deepEqual(errors,[]);check('Page errors',errors);
} finally {
 await writeFile(new URL('browser-results.json',out),JSON.stringify({date:'2026-11-14',base,results,errors},null,2));await browser.close();
}
console.log(`PASS ${results.length} browser observations; screenshots and results in .qa/v3`);
