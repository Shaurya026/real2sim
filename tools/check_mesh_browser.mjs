/* Optional real-browser QA. Uses an existing Playwright and Chromium installation.
   PLAYWRIGHT_MODULE=/absolute/path/to/playwright node tools/check_mesh_browser.mjs OUTPUT
   File-backed HTTPS routes avoid needing a local server. */
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const source=fileURLToPath(new URL('../docs/mesh/',import.meta.url)),out=path.resolve(process.argv[2]||'verification-work/mesh-browser');
if(fs.existsSync(out))throw Error('Use a fresh evidence directory');
const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.jpg':'image/jpeg','.glb':'model/gltf-binary'};
let browser;const errors=[],checks=[];
try{
 browser=await chromium.launch({headless:true,...(process.env.BROWSER_BIN?{executablePath:process.env.BROWSER_BIN}:{})});
 fs.mkdirSync(out,{recursive:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100},acceptDownloads:true});
 page.on('pageerror',e=>errors.push(e.message));
 await page.context().route('https://real2sim.local/**',async route=>{
  const name=decodeURIComponent(new URL(route.request().url()).pathname),file=path.resolve(source,'.'+(name==='/'?'/index.html':name));
  if(!file.startsWith(source)||!fs.existsSync(file)||!fs.statSync(file).isFile())return route.fulfill({status:404,body:''});
  return route.fulfill({status:200,contentType:types[path.extname(file)]||'application/octet-stream',body:fs.readFileSync(file)});
 });
 await page.goto('https://real2sim.local/analysis.html',{waitUntil:'load'});
 await page.waitForFunction(()=>window.real2simInspector?.ready&&window.real2simInspector.asset==='office',undefined,{timeout:120000});
 const inventory=JSON.parse(fs.readFileSync(path.join(source,'assets.json'),'utf8'));
 for(const {id,triangles} of inventory.assets){
  await page.locator(`[data-asset=${id}]`).click();
  await page.waitForFunction(id=>window.real2simInspector?.ready&&window.real2simInspector.asset===id,id,{timeout:120000});
  const state=await page.evaluate(()=>window.real2simInspector);
  if(state.error||state.stats.triangles!==triangles||!state.sha256Verified)throw Error(`Artifact failed: ${id}`);
  await page.locator('#wire').click();if(await page.locator('#wire').getAttribute('aria-pressed')!=='true')throw Error('Wireframe did not enable');
  await page.locator('#wire').click();await page.locator('#bounds').click();await page.locator('#neutral').click();await page.locator('#neutral').click();
  await page.locator('#mesh-select').selectOption('0');await page.locator('#mesh-select').selectOption('');await page.locator('#fit').click();
  if(id==='office'){
   await page.locator('#object-select').selectOption('bottle');await page.locator('#object-focus').click();
   const bottleBefore=await page.evaluate(()=>window.real2simInspector.objectEditor.snapshot());
   if(!bottleBefore.objects.find(o=>o.id==='bottle').parts.every(p=>p.visible))throw Error('Bottle geometry is hidden');
   await page.locator('#object-lift').click();await page.locator('#object-turn').click();
   if(JSON.stringify(bottleBefore)===JSON.stringify(await page.evaluate(()=>window.real2simInspector.objectEditor.snapshot())))throw Error('Bottle controls did not change pose');
   await page.locator('#object-reset').click();if(JSON.stringify(bottleBefore)!==JSON.stringify(await page.evaluate(()=>window.real2simInspector.objectEditor.snapshot())))throw Error('Bottle reset did not restore pose');
  }
  await page.waitForTimeout(700);await page.screenshot({path:path.join(out,`${id}-desktop.png`),fullPage:true});checks.push({asset:id,...state.stats});
 }
 const pending=page.waitForEvent('download');await page.locator('#report').click();const download=await pending;await download.saveAs(path.join(out,'inspection.json'));
 const report=JSON.parse(fs.readFileSync(path.join(out,'inspection.json'),'utf8'));if(report.artifact.id!=='chair'||report.metric_scale_verified!==false)throw Error('Invalid exported report');

 await page.goto('https://real2sim.local/booth/',{waitUntil:'load'});
 await page.waitForFunction(()=>window.sceneExample?.state.ready,undefined,{timeout:120000});
 const booth=await page.evaluate(()=>{window.sceneExample.setTime(0);const before=window.sceneExample.snapshot();window.sceneExample.setTime(4);return {before,after:window.sceneExample.snapshot(),state:window.sceneExample.state};});
 if(!booth.state.hashVerified||booth.state.duration!==9||JSON.stringify(booth.before.seat)===JSON.stringify(booth.after.seat))throw Error('Yellow-room animation did not move original chair geometry');
 await page.locator('#play').click();await page.waitForFunction(()=>window.sceneExample.state.time>4.1);await page.locator('#play').click();
 await page.locator('#reset').click();if(await page.evaluate(()=>window.sceneExample.state.time)!==0)throw Error('Chair reset failed');
 await page.locator('#cutaway').click();if(await page.locator('#cutaway').getAttribute('aria-pressed')!=='true')throw Error('Cutaway did not enable');
 await page.locator('#interior').click();await page.locator('#walk').click();
 const beforeWalk=await page.evaluate(()=>window.sceneExample.snapshot().camera);await page.keyboard.down('KeyW');await page.waitForTimeout(250);await page.keyboard.up('KeyW');
 if(JSON.stringify(beforeWalk)===JSON.stringify(await page.evaluate(()=>window.sceneExample.snapshot().camera)))throw Error('Walk camera did not move');
 await page.keyboard.press('Escape');await page.screenshot({path:path.join(out,'yellow-room.png')});
 checks.push({scene:'yellow_room',animation:true,reset:true,walking:true});
 await page.goto('https://real2sim.local/pantry/',{waitUntil:'load'});
 const frame=await (await page.locator('#pantry').elementHandle()).contentFrame();
 await frame.waitForFunction(()=>window.viewerReady&&window.textureReady&&window.objectMotionReady,undefined,{timeout:120000});
 const pickup=await frame.evaluate(()=>{window.objectMotion.setTime(0);const before=window.objectMotionState.pose;window.objectMotion.setTime(7);return {before,after:window.objectMotionState.pose};});
 if(JSON.stringify(pickup.before)===JSON.stringify(pickup.after))throw Error('Original pantry pickup did not change pose');
 await frame.locator('#objectReset').click();await frame.locator('#tour').click();await frame.waitForFunction(()=>window.navigationState?.tour);
 await page.screenshot({path:path.join(out,'pantry.png')});checks.push({scene:'pantry',original_viewer:true,pickup:true,guided_tour:true});

 await page.locator('#object-mode').click();
 const editorFrame=await (await page.locator('#pantry').elementHandle()).contentFrame();
 await editorFrame.waitForFunction(()=>window.sceneExample?.state.ready,undefined,{timeout:120000});
 await editorFrame.locator('#object-select').selectOption('bottles');await editorFrame.locator('#object-focus').click();
 const bottlesBefore=await editorFrame.evaluate(()=>window.sceneExample.objectEditor.snapshot());await editorFrame.locator('#object-lift').click();
 if(JSON.stringify(bottlesBefore)===JSON.stringify(await editorFrame.evaluate(()=>window.sceneExample.objectEditor.snapshot())))throw Error('Pantry bottles did not move');
 await editorFrame.locator('#object-reset').click();if(JSON.stringify(bottlesBefore)!==JSON.stringify(await editorFrame.evaluate(()=>window.sceneExample.objectEditor.snapshot())))throw Error('Pantry bottle reset failed');
 checks.push({scene:'pantry_objects',bottles_visible:true,movement:true,reset:true});
 await page.goto('https://real2sim.local/',{waitUntil:'load'});
 if(await page.locator('.scene-card').count()!==3)throw Error('Expected office reference and two interactive scene cards');
 await page.screenshot({path:path.join(out,'gallery.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.waitForTimeout(500);
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile page overflows horizontally');
 await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify({status:'passed',checks,page_errors:errors,export_verified:true,mobile_overflow:false},null,2));
 console.log(`Browser checks passed: ${out}`);
}finally{if(browser)await browser.close();}
