from project_paths import ASSET_ROOT, MEDIA_ROOT, CACHE_ROOT, TEMP_ROOT, RELEASE_ROOT
"""Encode the clean lossless 1080p master for Windows Media Foundation playback."""
from pathlib import Path
import hashlib,io,json,shutil,struct,subprocess,tempfile
import imageio_ffmpeg
from PIL import Image

CACHE=MEDIA_ROOT
BASE=CACHE
PROJECT=Path(__file__).resolve().parents[2]

def build(destination):
    CACHE.mkdir(parents=True,exist_ok=True)
    master=BASE/'startup-native-master.frames'
    assert master.is_file(),'The clean lossless v10.6 master is required, not a re-encoded preview.'
    movie=CACHE/'startup-native-visual.mp4';metadata=CACHE/'startup-native-video.json'
    signature=hashlib.sha256(Path(__file__).read_bytes()+str(master.stat().st_size).encode()+str(master.stat().st_mtime_ns).encode()).hexdigest()
    if movie.exists() and metadata.exists() and json.loads(metadata.read_text())['signature']==signature:
        shutil.copy2(movie,destination);return
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix='eva-mf-',dir=TEMP_ROOT) as temporary:
        work=Path(temporary);visual=work/'visual.mp4'
        with master.open('rb') as source:
            header,fps,count=struct.unpack('<4sII',source.read(12));assert (header,fps,count)==(b'EVA1',48,1920)
            offsets=[]
            for _ in range(count):
                length=struct.unpack('<I',source.read(4))[0];offsets.append((source.tell(),length));source.seek(length,1)
            # The clean input contains no progress; live transparent controls supply it.
            encoder=subprocess.Popen([ffmpeg,'-v','error','-y','-f','image2pipe','-framerate','48','-vcodec','png','-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p','-g','48',str(visual)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                first=11*fps;span=count-first
                for tick in range(48*45):
                    index=tick if tick<count else first+(tick-first)%span
                    at,length=offsets[index];source.seek(at);encoder.stdin.write(source.read(length))
                    if tick%480==0:print('Encoded native video',tick//48,'/45 seconds',flush=True)
                encoder.stdin.close();error=encoder.stderr.read().decode(errors='replace');assert encoder.wait(timeout=60)==0,error
            finally:
                if encoder.poll() is None:encoder.kill();encoder.wait()
        shutil.copy2(visual,movie)
    metadata.write_text(json.dumps({'signature':signature,'fps':48,'durationSeconds':45,'size':[1920,1080],'encoding':'H.264 CRF 16 from lossless master; original colors; audio remixed separately from original PCM','waiting':'29-second forward-only seamless wait; no seek during the 45-second cover lifetime','bytes':movie.stat().st_size},indent=2),encoding='utf-8')
    shutil.copy2(movie,destination)

def build_fallback(destination):
    """Keep a compact recovery path; normal playback remains 1080p/48 fps MF."""
    CACHE.mkdir(parents=True,exist_ok=True)
    output=CACHE/'startup-native.frames'
    if not output.exists():
        master=BASE/'startup-native-master.frames'
        with master.open('rb') as source,output.with_suffix('.partial').open('wb') as target:
            magic,fps,count=struct.unpack('<4sII',source.read(12));assert (magic,fps,count)==(b'EVA1',48,1920)
            target.write(struct.pack('<4sII',b'EVA1',24,count//2))
            for index in range(count):
                size=struct.unpack('<I',source.read(4))[0]
                if index%2:source.seek(size,1);continue
                with Image.open(io.BytesIO(source.read(size))) as frame:
                    frame=frame.convert('RGB').resize((960,540),Image.Resampling.LANCZOS)
                    buffer=io.BytesIO();frame.save(buffer,'JPEG',quality=82,optimize=True)
                data=buffer.getvalue();target.write(struct.pack('<I',len(data)));target.write(data)
        output.with_suffix('.partial').replace(output)
    shutil.copy2(output,destination)

if __name__=='__main__':build(Path(__file__).resolve().parent/'dist/startup-native-video.mp4')
