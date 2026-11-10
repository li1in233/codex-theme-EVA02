from project_paths import ASSET_ROOT, MEDIA_ROOT, CACHE_ROOT, TEMP_ROOT, RELEASE_ROOT
"""Mix clean startup audio and copy the newly rendered visual stream."""
from pathlib import Path
import base64,hashlib,json,shutil,subprocess,tempfile
import imageio_ffmpeg

PROJECT=Path(__file__).resolve().parents[2]
CACHE=MEDIA_ROOT
VIDEO=CACHE/'startup-native-visual.mp4'

def build(destination):
    CACHE.mkdir(parents=True,exist_ok=True)
    assets_path=PROJECT/'previews/startup-s4-waiting/assets.js'
    assets=json.loads(assets_path.read_text('utf8').split('=',1)[1].strip().removesuffix(';'))
    cues=[('entry-original',0,.78),('voice-plug',.12,.7),('lcl-water',7.5/1.8,.53),('voice-lcl',7.5/1.8,.88),('grid-original',7.5/1.8+2.4,.45),('voice-system',7.5/1.8+2.4,.88),('system-confirm',7.5/1.8+2.4+2.15,.72),('voice-sync',7.5/1.8+2.4+2.15+.7,.88)]
    signature=hashlib.sha256(Path(__file__).read_bytes()+assets_path.read_bytes()+str(VIDEO.stat().st_mtime_ns).encode()).hexdigest()
    wave=CACHE/'startup-native.wav';movie=CACHE/'startup-native-video.mp4';meta=CACHE/'audio.json'
    if not (movie.exists() and wave.exists() and meta.exists() and json.loads(meta.read_text())['signature']==signature):
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
        with tempfile.TemporaryDirectory(prefix='eva-audio-',dir=TEMP_ROOT) as tmp:
            work=Path(tmp);command=[ffmpeg,'-v','error','-y'];filters=[]
            for i,(name,delay,gain) in enumerate(cues):
                path=work/(name+'.wav');path.write_bytes(base64.b64decode(assets['sounds'][name].split(',',1)[1]));command+=['-i',str(path)]
                filters.append(f'[{i}:a]volume={gain},adelay={round(delay*1000)}:all=1[a{i}]')
            filters.append(''.join(f'[a{i}]' for i in range(len(cues)))+f'amix=inputs={len(cues)}:normalize=0,apad,atrim=0:15.5[a]')
            subprocess.run([*command,'-filter_complex',';'.join(filters),'-map','[a]','-c:a','pcm_s16le','-ar','44100','-ac','2',str(wave)],check=True,capture_output=True)
            subprocess.run([ffmpeg,'-v','error','-y','-i',str(VIDEO),'-i',str(wave),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(movie)],check=True,capture_output=True)
        meta.write_text(json.dumps({'signature':signature,'cues':cues,'removed':['wait-loop','merge-original'],'video':'stream copy; no color or quality changes','silenceAfterSeconds':10.589},indent=2),encoding='utf8')
    shutil.copy2(wave,destination/wave.name);shutil.copy2(movie,destination/movie.name)

if __name__=='__main__':build(Path(__file__).resolve().parent/'dist')
