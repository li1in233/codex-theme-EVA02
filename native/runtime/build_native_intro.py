from project_paths import ASSET_ROOT, MEDIA_ROOT, CACHE_ROOT, TEMP_ROOT, RELEASE_ROOT
"""Build the native CPU prelude directly from the approved canvas, without video re-encoding loss."""
from pathlib import Path
import base64
import hashlib
import io
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
import imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import numpy as np
from playwright.sync_api import sync_playwright

SIZE=(2560,1440)
FPS=48
COUNT=744
CACHE=ASSET_ROOT/'startup-clips'
PROJECT=Path(__file__).resolve().parents[2]


def replace_number(im,polygon,text_at,size,angle):
    """Continue the local paint plane under a small printed identifier."""
    mask=Image.new('L',im.size);ImageDraw.Draw(mask).polygon(polygon,fill=255)
    box=mask.getbbox();left,top,right,bottom=box
    crop=(max(0,left-10),max(0,top-10),min(im.width,right+10),min(im.height,bottom+10))
    small=np.asarray(im.crop(crop)).astype(float);inside=np.asarray(mask.crop(crop))>0
    yy,xx=np.mgrid[crop[1]:crop[3],crop[0]:crop[2]]
    ring=(np.asarray(mask.filter(ImageFilter.MaxFilter(11)).crop(crop))>0)&~inside
    luminance=small.mean(axis=2);ring&=(luminance>small[inside].mean()*.7)&(luminance<small[inside].mean()*1.6)
    # Fitting a small paint plane avoids a rectangular patch on the native shell.
    design=np.stack([np.ones_like(xx),xx,yy],axis=-1)
    coef=np.linalg.lstsq(design[ring],small[ring],rcond=None)[0]
    plane=np.clip(design@coef,0,255).astype('uint8')
    fill=Image.fromarray(plane);im.paste(fill,crop[:2],mask.filter(ImageFilter.GaussianBlur(.45)).crop(crop))
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
    glyph=Image.new('RGBA',(size*2,size+12));d=ImageDraw.Draw(glyph);d.text((0,0),'02',font=font,fill=('#1b2021' if size>30 else '#667968'))
    glyph=glyph.crop(glyph.getbbox()).rotate(angle,expand=True,resample=Image.Resampling.BICUBIC)
    im.paste(glyph,(round(text_at[0]-glyph.width/2),round(text_at[1]-glyph.height/2)),glyph)


def high_resolution_assets(assets):
    """Repeat the approved edits at 2K using the original local 4K film."""
    CACHE.mkdir(parents=True,exist_ok=True)
    movie=ASSET_ROOT/'source-video/source.mkv'
    assert movie.is_file(),'Original local 4K film is required to rebuild the HD clips'
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    scale=SIZE[0]/1440
    for name,start,length,speed in [('entry-02',887.5,7.5,1.8),('system-grid',940,2.15,1)]:
        target=CACHE/(name+'-2560-original-color-v2.mp4')
        if not target.exists():
            # Keep the original film cadence; procedural motion is rendered separately at 48 fps.
            filters=f'scale={SIZE[0]}:{SIZE[1]}:flags=lanczos,setpts=(PTS-STARTPTS)/{speed},fps=24'
            decoder=subprocess.Popen([ffmpeg,'-v','error','-ss',str(start),'-t',str(length),'-i',str(movie),'-an','-sn','-vf',filters,'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
            encoder=subprocess.Popen([ffmpeg,'-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{SIZE[0]}x{SIZE[1]}','-r','24','-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','14','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],stdin=subprocess.PIPE)
            try:
                index=0
                while True:
                    raw=decoder.stdout.read(SIZE[0]*SIZE[1]*3)
                    if not raw:break
                    assert len(raw)==SIZE[0]*SIZE[1]*3
                    image=Image.frombytes('RGB',SIZE,raw)
                    if name=='entry-02':
                        if index/24*speed>=.73:
                            draw=ImageDraw.Draw(image)
                            draw.rectangle(tuple(round(v*scale) for v in (83,63,733,107)),fill='#060709')
                            draw.text((round(93*scale),round(69*scale)),'| Monitored Target Subject : EVA-02 Entry Plug |',font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',round(27*scale)),fill='#b18040')
                        else:
                            replace_number(image,[(round(x*scale),round(y*scale)) for x,y in [(1166,333),(1192,315),(1211,346),(1184,364)]],(1188*scale,341*scale),round(22*scale),34)
                    encoder.stdin.write(image.tobytes());index+=1
                encoder.stdin.close()
                assert decoder.wait(timeout=30)==0 and encoder.wait(timeout=30)==0
                assert index== (100 if name=='entry-02' else 52),(name,index)
            except BaseException:
                target.unlink(missing_ok=True)
                raise
            finally:
                decoder.stdout.close()
                for process in (decoder,encoder):
                    if process.poll() is None:process.kill();process.wait()
        assets['videos'][name]='data:video/mp4;base64,'+base64.b64encode(target.read_bytes()).decode()
    return assets
