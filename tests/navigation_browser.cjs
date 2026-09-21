// Run against a separate, POST-disabled candidate preview, never a refresh workflow.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const origin=process.env.POPS_PREVIEW_URL;
 assert(origin,'Set POPS_PREVIEW_URL to the read-only test server');
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try {
 const page=await browser.newPage({viewport:{width:1280,height:1000}});
 page.setDefaultTimeout(30000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let posts=0;
 await page.route('**/*',route=>{if(route.request().method()==='POST'){posts++;return route.abort();}return route.continue();});
 const nav=async(locator)=>{await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),locator.click()]);};
 await page.goto(origin+'/');
 await page.locator('#importTab').click();
 await page.waitForFunction(()=>document.querySelector('#forecast').options.length>1);
 const picked={};
 for(const id of ['forecast','activity','pnl']) {
   const el=page.locator('#'+id);await el.selectOption({index:1});picked[id]=await el.inputValue();
 }
 await page.locator('#sheetTab').click();
 const frame=page.frameLocator('#board');
 await frame.locator('#seasonWeek').selectOption('2');
 await frame.locator('#omitCompleted').check();
 await frame.locator('th button[data-column="1"]').click();
 const direction=await frame.locator('th button[data-column="1"]').evaluate(b=>b.closest('th').getAttribute('aria-sort'));
 const t=Date.now();await nav(page.locator('.product-nav').getByRole('link',{name:'Performance',exact:true}));
 console.log('First candidate Performance navigation ms',Date.now()-t);
 assert.equal(await page.locator('table[aria-label="Comparison with 50% reference"]').count(),1);
 assert.equal(await page.locator('table[aria-label="Match results"]').count(),1);
 assert.equal(await page.locator('select[name=week],select[name=season]').count(),0);
 assert.equal(await page.locator('select[name=period] option').count(),6);
 const metrics=await page.locator('table[aria-label="Comparison with 50% reference"]').innerText();
 await Promise.all([page.waitForNavigation(),page.locator('select[name=period]').selectOption('custom')]);
 await page.locator('input[name=from]').fill('2026-09-10');
 await page.locator('input[name=to]').fill('2026-09-21');
 await page.locator('select[name=team]').selectOption('ATL');
 await nav(page.getByRole('button',{name:'View matches',exact:true}));
 assert.equal(await page.locator('table[aria-label="Comparison with 50% reference"]').innerText(),metrics);
 await nav(page.locator('.sports').getByRole('link',{name:'MLB',exact:true}));
 assert.equal(await page.locator('select[name=period] option').count(),6);
 await Promise.all([page.waitForNavigation(),page.locator('select[name=period]').selectOption('14')]);
 const warm=Date.now();await nav(page.locator('.sports').getByRole('link',{name:'NFL',exact:true}));
 console.log('Warm NFL navigation ms',Date.now()-warm);
 assert.equal(await page.locator('select[name=period]').inputValue(),'custom');
 assert.equal(await page.locator('select[name=team]').inputValue(),'ATL');
 assert.equal(await page.locator('input[name=from]').inputValue(),'2026-09-10');
 await page.goBack();assert.equal(await page.locator('select[name=period]').inputValue(),'14');
 await nav(page.locator('.sports').getByRole('link',{name:'NFL',exact:true}));
 await nav(page.locator('.product-nav').getByRole('link',{name:'Bet Sheet',exact:true}));
 await page.waitForFunction(()=>document.querySelector('#sheetTab').getAttribute('aria-selected')==='true');
 assert.equal(await page.frameLocator('#board').locator('#seasonWeek').inputValue(),'2');
 assert(await page.frameLocator('#board').locator('#omitCompleted').isChecked());
 assert.equal(await page.frameLocator('#board').locator('th button[data-column="1"]').evaluate(b=>b.closest('th').getAttribute('aria-sort')),direction);
 await page.locator('#importTab').click();
 for(const id of Object.keys(picked))assert.equal(await page.locator('#'+id).inputValue(),picked[id]);
 // Emulate a replaced inbox file in the GET response; no actual source is changed.
 await page.route('**/api/state',async route=>{
   const response=await route.fetch();const state=await response.json();
   state.files.find(f=>f.id===picked.forecast).fingerprint='replacement';
   await route.fulfill({response,json:state});
 });
 await page.reload();await page.locator('#selectionNotice').filter({hasText:'missing or changed'}).waitFor();
 assert.equal(await page.locator('#forecast').inputValue(),'');
 assert.equal(await page.locator('#importTab').getAttribute('aria-selected'),'true');
 await page.unroute('**/api/state');
 await nav(page.locator('.sports').getByRole('link',{name:'MLB',exact:true}));
 await page.locator('#day').fill('2026-09-20');
 await Promise.all([page.waitForResponse(r=>r.url().includes('/api/mlb/day?date=2026-09-20')),page.locator('#day').dispatchEvent('change')]);
 await page.locator('#omitCompleted').check();
 await nav(page.locator('.sports').getByRole('link',{name:'NFL',exact:true}));
 await nav(page.locator('.sports').getByRole('link',{name:'MLB',exact:true}));
 await page.waitForFunction(()=>document.querySelector('#day').value==='2026-09-20');
 assert(await page.locator('#omitCompleted').isChecked());
 await page.goto(origin+'/performance/nfl?period=season');
 assert.equal(await page.locator('select[name=period]').inputValue(),'season');
 if(process.env.POPS_SCREENSHOT)await page.screenshot({path:process.env.POPS_SCREENSHOT,fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await Promise.all([page.waitForNavigation(),page.locator('select[name=period]').selectOption('custom')]);
 assert(await page.locator('input[name=from]').isVisible());
 assert.deepEqual(errors,[]);
 assert.equal(posts,0);
 console.log('Browser round trips, Back, filters, tabs, file-change warning, one-table layout and mobile controls passed');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
