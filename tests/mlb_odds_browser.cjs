// Offline browser regression for R1. Requires Playwright and installed Chrome.
// Run: NODE_PATH=<playwright packages> node tests/mlb_odds_browser.cjs
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../mlb_odds.html'),'utf8').replace('__BRAND_CSS__','').replace('__BRAND_MARK__','').replace('__TOKEN__','fixture');
const origin='http://127.0.0.1:59999';
const now=new Date(),at=now.toISOString();
const today=now.toLocaleDateString('en-CA',{timeZone:'America/New_York'});
const plus=days=>{const d=new Date(today+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+days);return d.toISOString().slice(0,10);};
function sheet(day=today,id='a'.repeat(32)){
 const q={cents:'56.0000',quantity:'2.00',started_at:at,completed_at:at,schedule_started_at:at,catalog_started_at:at,ticker:'KXMLBGAME-FIXTURE',raw_file:'raw/002.body',rules_primary:'Synthetic fixture',rules_secondary:'Synthetic fixture',transformation:'YES ask = 1 − NO bid',source_no_bid:'0.4400'};
 const g={id:'mlb:777',game_pk:777,away:{id:135,name:'Fixture Away'},home:{id:137,name:'Fixture Home'},start:new Date(+now+3600000).toISOString(),number:null,official_status:'Scheduled',reasons:[],away_quote:q,home_quote:q};
 return {day,today,now:at,clock_ok:true,selected:{id,digest:'fixture'},attempt:{id,state:'complete',message:'Two outcomes priced',completed_at:at},running:false,error:null,result:{games:[g],completed_at:at,schedule_started_at:at,catalog_started_at:at,requests:[],diagnostics:[]}};
}
const settle=page=>page.waitForFunction(()=>!readPending);
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 let cases=0;
 async function fixture(test){
  const page=await browser.newPage({viewport:{width:1280,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.clock.install({time:now});
  const io={reads:0,posts:0,get:async route=>route.fulfill({json:sheet(new URL(route.request().url()).searchParams.get('date')||today)}),post:async route=>route.fulfill({status:503,json:{error:'Refresh transport failure'}})};
  await page.route('**/*',route=>{
   const url=new URL(route.request().url());assert.equal(url.origin,origin,'No external requests permitted');
   if(url.pathname==='/mlb')return route.fulfill({contentType:'text/html',body:html});
   if(url.pathname==='/api/mlb/day'){io.reads++;return io.get(route);}
   if(url.pathname==='/api/mlb/refresh'){io.posts++;return io.post(route);}
   return route.abort();
  });
  try{await page.goto(origin+'/mlb');await settle(page);await test(page,io);assert.deepEqual(errors,[]);cases++;}
  finally{await page.close();}
 }
 try{
 await fixture(async(page,io)=>{
  io.get=route=>route.fulfill({status:503,json:{error:'Saved read failed'}});
  await page.locator('#day').fill(plus(1));await page.locator('#day').press('Tab');await settle(page);
  assert.equal(await page.locator('.price').count(),0);assert.equal(await page.locator('#gameCount').innerText(),'0');
  await page.locator('#team').selectOption('137');await page.locator('#include').uncheck();
  await page.clock.fastForward(301000);await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
  assert.match(await page.locator('#error').innerText(),/Saved read failed/);assert.equal(await page.locator('.price').count(),0);
  assert.equal(await page.locator('#day').inputValue(),plus(1));assert.equal(io.posts,0);
  assert(await page.locator('#refresh').isDisabled());
 });
 await fixture(async(page,io)=>{
  await page.locator('#refresh').click();await page.locator('#error').filter({hasText:'Refresh transport failure'}).waitFor();
  await page.locator('#team').selectOption('137');await page.locator('#include').uncheck();
  await page.clock.fastForward(301000);await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
  assert.match(await page.locator('#outcome').innerText(),/Refresh request failed/);assert.match(await page.locator('#error').innerText(),/Refresh transport failure/);
  assert.equal(await page.locator('.price').count(),0);assert.equal(io.posts,1);
  await page.locator('details[data-game] summary').click();assert.match(await page.locator('.details-grid').innerText(),/Historical saved ask: 56¢/);
  assert((await page.locator('.details-grid a').first().getAttribute('href')).includes(today));
 });
 await fixture(async(page,io)=>{
  let held;
  io.get=route=>{if(new URL(route.request().url()).searchParams.get('date')===plus(1)){held=route;return;}return route.fulfill({status:503,json:{error:'Latest read failed'}});};
  await page.locator('#day').fill(plus(1));await page.locator('#day').press('Tab');
  await page.waitForFunction(()=>readPending);assert.equal(await page.locator('.price').count(),0);assert(await page.locator('#refresh').isDisabled());
  await page.locator('#day').fill(plus(2));await page.locator('#day').press('Tab');await settle(page);
  await held.fulfill({json:sheet(plus(1))});await page.clock.runFor(1);
  assert.equal(await page.locator('#day').inputValue(),plus(2));assert.match(await page.locator('#error').innerText(),/Latest read failed/);assert.equal(await page.locator('.price').count(),0);
 });
 await fixture(async(page,io)=>{
  let held;
  io.get=route=>{if(new URL(route.request().url()).searchParams.get('date')===plus(1)){held=route;return;}return route.fulfill({json:sheet(plus(2))});};
  await page.locator('#day').fill(plus(1));await page.locator('#day').press('Tab');await page.waitForFunction(()=>readPending);
  await page.locator('#day').fill(plus(2));await page.locator('#day').press('Tab');await settle(page);
  await held.fulfill({status:503,json:{error:'Obsolete failure'}});await page.clock.runFor(1);
  assert.equal(await page.locator('#day').inputValue(),plus(2));assert.equal(await page.locator('#error').innerText(),'');assert.equal(await page.locator('.price').count(),2);
 });
 await fixture(async(page,io)=>{
  io.get=route=>route.fulfill({status:503,json:{error:'Read failure'}});
  await page.locator('#reload').click();await settle(page);assert.match(await page.locator('#error').innerText(),/Read failure/);
  io.get=route=>route.fulfill({json:sheet()});await page.locator('#reload').click();await settle(page);
  assert.equal(await page.locator('#error').innerText(),'');assert.equal(await page.locator('.price').count(),2);assert.equal(io.posts,0);
  await page.locator('#refresh').click();await page.locator('#error').filter({hasText:'Refresh transport failure'}).waitFor();
  await page.locator('#reload').click();await settle(page);assert.match(await page.locator('#error').innerText(),/Refresh transport failure/,'Old saved success cannot clear a failed action');
  io.post=route=>route.fulfill({json:{state:'running'}});io.get=route=>route.fulfill({json:sheet(today,'b'.repeat(32))});
  await page.locator('#refresh').click();await page.waitForFunction(()=>!readPending&&!action());
  assert.equal(await page.locator('#error').innerText(),'');assert.equal(await page.locator('.price').count(),2);assert.equal(io.posts,2);
 });
 await fixture(async(page,io)=>{
  let held;io.post=route=>{held=route;};
  await page.locator('#refresh').click();await page.waitForFunction(()=>action()?.state==='pending');
  await page.locator('#day').fill(plus(1));await page.locator('#day').press('Tab');await settle(page);
  await held.fulfill({status:503,json:{error:'Earlier day action failed'}});await page.waitForFunction(day=>actions.get(day)?.state==='failed',today);
  assert.equal(await page.locator('#day').inputValue(),plus(1));assert.equal(await page.locator('#error').innerText(),'');assert.equal(await page.locator('.price').count(),2);
  await page.locator('#today').click();await settle(page);assert.match(await page.locator('#error').innerText(),/Earlier day action failed/);assert.equal(await page.locator('.price').count(),0);
 });
 await fixture(async(page,io)=>{
  for(const state of ['partial','failed','interrupted','empty','stale','clock']){
   const value=sheet();
   if(state==='partial'){value.attempt.state='partial';value.result.games[0].home_quote=null;value.result.games[0].home_reason='Missing book';}
   if(['failed','interrupted'].includes(state))value.attempt={...value.attempt,id:'b'.repeat(32),state};
   if(state==='empty'){value.result.games=[];value.selected=null;value.attempt=null;}
   if(state==='stale')for(const q of [value.result.games[0].away_quote,value.result.games[0].home_quote])q.started_at=new Date(+now-300000).toISOString();
   if(state==='clock')value.clock_ok=false;
   io.get=route=>route.fulfill({json:value});await page.locator('#reload').click();await settle(page);
   assert.equal(await page.locator('.price').count(),state==='partial'?1:0,state);
   if(state==='clock')assert.match(await page.locator('#error').innerText(),/clock/);
  }
  assert.equal(io.posts,0);
 });
 console.log(`PASS: ${cases} offline browser scenarios (failed reads/actions, filters/timers/focus, pending and reordered responses, manual recovery, cross-date actions, existing states).`);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
