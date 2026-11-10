from project_paths import ASSET_ROOT, MEDIA_ROOT, CACHE_ROOT, TEMP_ROOT, RELEASE_ROOT
"""Capture the approved scene without baked progress; live controls draw the number."""
from pathlib import Path
import base64,hashlib,io,json,struct,shutil
from PIL import Image
from playwright.sync_api import sync_playwright

CACHE=MEDIA_ROOT
SIZE=(1920,1080)

def build(startup):
    CACHE.mkdir(parents=True,exist_ok=True)
    master=CACHE/'startup-native-master.frames';meta=CACHE/'master.json'
    signature=hashlib.sha256(startup.read_bytes()+Path(__file__).read_bytes()).hexdigest()
    if master.exists() and meta.exists() and json.loads(meta.read_text())['signature']==signature:return master
    hook='''window.__evaCapture=async t=>{
      const state=simulation(t);
      if(state.media){const v=videos[state.media.key];if(Math.abs(v.currentTime-state.media.at)>.001){await new Promise(ok=>{v.addEventListener('seeked',ok,{once:true});v.currentTime=state.media.at;});}}
      draw(t,state);return canvas.toDataURL('image/png').split(',')[1];
    };'''
    instrumented=startup.read_text('utf8').replace("  window.addEventListener('pagehide'",hook+"\n  window.addEventListener('pagehide'")
    with sync_playwright() as pw,master.with_suffix('.partial').open('wb') as output:
        chrome=next(p for p in [Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')] if p.exists())
        browser=pw.chromium.launch(executable_path=str(chrome),headless=True)
        try:
            page=browser.new_page(viewport={'width':SIZE[0],'height':SIZE[1]})
            page.set_content('<html><body style="margin:0"><div id="root"></div></body></html>')
            page.evaluate('window.__evaTheme={motion:()=>true};window.__evaStartupHold=true;')
            page.evaluate(instrumented);page.wait_for_function('window.__evaStartup.state().prepared',timeout=30000)
            output.write(struct.pack('<4sII',b'EVA1',48,1920))
            # Preserve the approved entry/LCL/system frames byte for byte.
            with (CACHE/'startup-native-master.frames').open('rb') as approved:
                assert struct.unpack('<4sII',approved.read(12))==(b'EVA1',48,1920)
                for index in range(452):
                    size=struct.unpack('<I',approved.read(4))[0];output.write(struct.pack('<I',size));output.write(approved.read(size))
            for index in range(452,1920):
                png=base64.b64decode(page.evaluate('t=>__evaCapture(t)',index/48))
                output.write(struct.pack('<I',len(png)));output.write(png)
                
                if index%96==0:print('Captured clean 1080p master',index,'/1920',flush=True)
            page.evaluate('window.__evaStartup.skip()')
        finally:browser.close()
    master.with_suffix('.partial').replace(master)
    meta.write_text(json.dumps({'signature':signature,'size':SIZE,'fps':48,'frames':1920,'bakedProgress':False,'bytes':master.stat().st_size},indent=2))
    return master

if __name__=='__main__':build(Path(__file__).resolve().parent/'dist/startup.bundle.js')
