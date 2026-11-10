from project_paths import ASSET_ROOT, MEDIA_ROOT, CACHE_ROOT, TEMP_ROOT, RELEASE_ROOT
"""Build the installed renderer from the approved sources, without touching MSIX."""

from pathlib import Path

import base64, hashlib, json, os, re, subprocess

import imageio_ffmpeg

import numpy as np

from PIL import Image

from build_native_intro import high_resolution_assets
from build_native_video import build as build_native_video, build_fallback



ROOT = Path(__file__).resolve().parents[2]

SOURCE = ROOT / 'native/runtime'

OUT = SOURCE / 'dist'

OUT.mkdir(exist_ok=True)
required=[ASSET_ROOT/'artwork/poster.jpg', ROOT/'previews/startup-s4-waiting/assets.js', MEDIA_ROOT/'startup-native-master.frames', ASSET_ROOT/'startup-clips/hex-open-1080p60.webm']
missing=[str(p) for p in required if not p.is_file()]
if missing: raise SystemExit('Full startup build requires rights-cleared private inputs. See docs/BUILD.md. Missing: '+', '.join(missing))

art = Image.open(ASSET_ROOT/'artwork/poster.jpg').convert('RGB')

assert art.size == (3508,2481)

art = art.crop((1754,0,3508,2481))

art.thumbnail((1000,1500),Image.Resampling.LANCZOS)

pixels=np.asarray(art).astype(float)

matte=np.clip((255-pixels.min(2))/20,0,1)

# The exterior printer rule is not part of the poster content.

matte[:3,:]=0;matte[-3:,:]=0;matte[:,:3]=0;matte[:,-3:]=0

rgba=np.dstack([pixels,matte*.32*255]).astype('uint8')

art_path=OUT/'official-nishigori-asuka.png'

Image.fromarray(rgba).save(art_path)

art_url='data:image/png;base64,'+base64.b64encode(art_path.read_bytes()).decode()

config={'motion':'on','muted':False}

css=(SOURCE/'theme.css').read_text(encoding='utf8').replace('__EVA_ART__',art_url)
css=css.replace('__EVA_HEADER_FONT__','data:font/ttf;base64,'+base64.b64encode((SOURCE/'fonts/eva-heading.ttf').read_bytes()).decode())

theme=(SOURCE/'theme.js').read_text(encoding='utf8').replace('__EVA_CSS__',json.dumps(css)).replace('__EVA_CONFIG__',json.dumps(config))

(OUT/'theme.bundle.js').write_text(theme,encoding='utf8')

assets=(ROOT/'previews/startup-s4-waiting/assets.js').read_text(encoding='utf8')

assets=re.sub(r'^\s*window\.S4_ASSETS\s*=\s*','',assets).strip().removesuffix(';')

parsed_assets=high_resolution_assets(json.loads(assets))
for removed_sound in ('wait-loop','merge-original'):parsed_assets['sounds'].pop(removed_sound,None)
hex_video=ASSET_ROOT/'startup-clips/hex-open-1080p60.webm'
assert hex_video.is_file(), 'Run build_hex_video.py against the approved v10.6 bundle first'
parsed_assets['videos']['hex-open']='data:video/webm;base64,'+base64.b64encode(hex_video.read_bytes()).decode()
assets=json.dumps(parsed_assets,ensure_ascii=True)

entry_bytes=base64.b64decode(parsed_assets['videos']['entry-02'].split(',',1)[1])

frame=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-i','pipe:0','-frames:v','1','-q:v','3','-f','image2pipe','-vcodec','mjpeg','pipe:1'],input=entry_bytes,capture_output=True,check=True)

(OUT/'startup-first-frame.jpg').write_bytes(frame.stdout)

source=(ROOT/'previews/startup-s4-waiting/s4.js').read_text(encoding='utf8')

engine=source[source.index('function text('):source.index('function simulation(')]

engine=engine.replace('document.querySelector(', 'root.querySelector(')
# Source rectangles use physical pixels; scene geometry stays in the approved 1440x810 coordinates.
engine=engine.replace('ctx.drawImage(canvas,0,surface+yy,W,4,dx,surface+yy+2,W,5)',
    'ctx.drawImage(canvas,0,(surface+yy)*canvas.height/H,canvas.width,4*canvas.height/H,dx,surface+yy+2,W,5)')
engine=engine.replace('shot.width=W;shot.height=H;', 'shot.width=canvas.width;shot.height=canvas.height;')
engine=engine.replace("const shotCtx=shot.getContext('2d');", "const shotCtx=shot.getContext('2d');shotCtx.setTransform(shot.width/W,0,0,shot.height/H,0,0);")
engine=engine.replace('ctx.drawImage(shot,0,0)', 'ctx.drawImage(shot,0,0,W,H)')
engine=engine.replace('ctx.drawImage(image,0,0)', 'ctx.drawImage(image,0,0,W,H)')
engine=engine.replace("text(String(Math.floor(s.progress)).padStart(3,'0')+' %',1390,785,16,s.progress===100?'#d6e1c8':'#bc9a56','right');",'')
hud_at=engine.index('  const x=1210,y=659;')
engine=engine[:hud_at]+engine[engine.index('\n}',hud_at):]
engine=engine.replace('alpha*=birth;', 'alpha*=birth;if(alpha<=.001)return;')
engine=engine.replace('studyTubes(t,s.progress,c,a);','studyTubes(s.motionTime??t,s.progress,c,a);')
engine=engine[:engine.index('function waitingOffset(')]+(SOURCE/'tube-loop.js').read_text('utf8')+'\n'+engine[engine.index('function curveProfile('):]
engine=engine.replace('((t-T.waveAt+(3-syncDuration)*c)*180+channel*330)%(W+300)-150','tubeFlow(t,c,channel)')
engine=engine.replace("if(c>.96){ctx.globalAlpha=alpha*Math.sin(clamp((c-.96)/.04)*Math.PI)*.07;ctx.fillStyle='#c0d9d9';ctx.fillRect(0,98,W,602);}",'')

# No iframe handshake, fixture controls, fake host events or global assets.

assert 'r7Frame' not in engine

startup=(SOURCE/'startup.js').read_text(encoding='utf8').replace('__EVA_CONFIG__',json.dumps(config)).replace('__EVA_ASSETS__',assets).replace('__EVA_ENGINE__',engine).replace('__EVA_HEX_PLAYER__',(SOURCE/'hex-player.js').read_text('utf-8'))

(OUT/'startup.bundle.js').write_text(startup,encoding='utf8')

# Capture without baked progress so both players use the same live number.
from build_clean_master import build as build_clean_master, CACHE as CLEAN_CACHE
build_clean_master(OUT/'startup.bundle.js')
import shutil
shutil.copy2(CLEAN_CACHE/'startup-first-frame.jpg',OUT/'startup-first-frame.jpg')
build_fallback(OUT/'startup-native.frames')
build_native_video(OUT/'startup-native-video.mp4')
from build_startup_audio import build as build_startup_audio
build_startup_audio(OUT)


compiler=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
subprocess.run([str(compiler),'/nologo','/target:winexe','/platform:x64','/win32manifest:'+str(SOURCE/'app.manifest'),
               '/out:'+str(OUT/'CodexEVA.exe'),'/reference:System.Web.Extensions.dll',
               '/reference:System.Drawing.dll','/reference:System.Windows.Forms.dll','/reference:Accessibility.dll',str(SOURCE/'Launcher.cs'),str(SOURCE/'NativeVideo.cs')],check=True)

runtime_assets={'theme.bundle.js','startup.bundle.js','startup-first-frame.jpg','startup-native.frames','startup-native.wav','startup-native-video.mp4','official-nishigori-asuka.png'}

manifest={'version':'R7-S4-installed-10.10','motion':config,'nativePlayer':'windows-media-foundation; compact CPU recovery','nativeFps':48,'nativeSize':[1920,1080],'recoverySize':[960,540],'recoveryFps':24,'entryColor':'original; text edits only','progressSemantics':'stage-weighted estimate; 100 requires verified host readiness','artSource':'user-supplied; see assets/private/credits.json','attribution':'User-supplied assets retain their own terms; see credits.json and docs/ASSETS.md.','files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in OUT.iterdir() if p.is_file() and p.name in runtime_assets}}
manifest['themeVersion']='R7-installed-6'
manifest['launcher']={'sourceSha256':hashlib.sha256((SOURCE/'Launcher.cs').read_bytes()).hexdigest(),
                      'manifestSha256':hashlib.sha256((SOURCE/'app.manifest').read_bytes()).hexdigest(),
                      'videoSourceSha256':hashlib.sha256((SOURCE/'NativeVideo.cs').read_bytes()).hexdigest(),
                      'sha256':hashlib.sha256((OUT/'CodexEVA.exe').read_bytes()).hexdigest()}

(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')

print(json.dumps({k:v['bytes'] for k,v in manifest['files'].items()}))
