from project_paths import ASSET_ROOT, MEDIA_ROOT, CACHE_ROOT, TEMP_ROOT, RELEASE_ROOT
"""Bake the immutable honeycomb once; playback must not depend on the host's JS frames."""
from pathlib import Path
import base64,hashlib,json,math,subprocess
import imageio_ffmpeg
from playwright.sync_api import sync_playwright

CACHE=ASSET_ROOT/'startup-clips'
FPS=60

def build(reference):
    CACHE.mkdir(parents=True,exist_ok=True)
    output=CACHE/'hex-open-1080p60.webm';meta=CACHE/'hex-open.json'
    signature=hashlib.sha256(reference.read_bytes()+Path(__file__).read_bytes()).hexdigest()
    if output.exists() and meta.exists() and json.loads(meta.read_text())['signature']==signature:return output
    hook='''window.__hexCapture=t=>{studyHex(t);return canvas.toDataURL('image/png').split(',')[1];};'''
    bundle=reference.read_text('utf8').replace("  window.addEventListener('pagehide'",hook+"\n  window.addEventListener('pagehide'")
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True)
        try:
            page=browser.new_page(viewport={'width':1920,'height':1080})
            page.set_content('<body style="margin:0"><div id="root"></div></body>')
            page.evaluate('window.__evaTheme={motion:()=>true};window.__evaStartupHold=true;')
            page.evaluate(bundle);page.wait_for_function('__evaStartup.state().prepared',timeout=30000)
            encoder=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-f','image2pipe','-framerate',str(FPS),'-vcodec','png','-i','pipe:0','-an','-c:v','libvpx-vp9','-b:v','0','-crf','18','-pix_fmt','yuva420p','-auto-alt-ref','0','-row-mt','1','-threads','4',str(output)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                for i in range(math.ceil(1.5*FPS)):
                    png=base64.b64decode(page.evaluate('t=>__hexCapture(t)',i/FPS));encoder.stdin.write(png)
                    if i in (0,18,36,54,75):(CACHE/f'hex-reference-{i:03}.png').write_bytes(png)
                encoder.stdin.close();error=encoder.stderr.read().decode();assert encoder.wait(timeout=60)==0,error
            finally:
                if encoder.poll() is None:encoder.kill();encoder.wait()
            page.evaluate('__evaStartup.skip()')
        finally:browser.close()
    meta.write_text(json.dumps({'signature':signature,'fps':FPS,'size':[1920,1080],'frames':90,'alpha':True,'codec':'VP9 CRF18; 4:2:0 chroma; alpha retained','referenceSha256':hashlib.sha256(reference.read_bytes()).hexdigest(),'bytes':output.stat().st_size},indent=2))
    return output

if __name__=='__main__':
    import sys
    print(build(Path(sys.argv[1])))
