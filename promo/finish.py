import os
from pathlib import Path
import base64, hashlib, json, re, shutil, sys
import numpy as np
from PIL import Image, ImageDraw
import film_common as v

BODY=v.OUT/'sources/body-original.mp4'
v.SRC=v.OUT/'sources';v.PROJECT=v.OUT/'project';v.PROJECT.mkdir(parents=True,exist_ok=True)
v.BOX=(8,6,1904,944);v.BASE=v.BOX[3]/v.CH
OPEN=v.at('overall');TRIM=38/60;GAIN=1.0339511011796003
CAPTURE=json.loads((v.SRC/'startup-capture.json').read_text(encoding='utf-8'))
STATE=CAPTURE['events'][1]['state']
VIDEO=v.OUT/'CODEX-THEME-EVA02_v1.0.0_107s_1080p60_v6.mp4'

def caption(i):
    a,b,title,sub,tag=v.CAPTIONS[i]
    im=Image.new('RGBA',(1920,1080));d=ImageDraw.Draw(im)
    d.rectangle((0,956,1920,1080),fill=v.BG);d.line((72,965,1848,965),fill='#4b242b')
    d.rectangle((72,983,77,1021),fill=v.GOLD)
    d.text((96,979),title,font=v.EN[42] if i==0 else v.CN[34],fill=v.WHITE)
    d.text((98,1033),sub,font=v.EN[18],fill=v.MUTED)
    tw=d.textlength(tag,font=v.CN[16]);d.text((1848-tw,1033),tag,font=v.CN[16],fill=v.GOLD)
    return im

v.CAP_IMAGES=[caption(i) for i in range(len(v.CAPTIONS))]
assert all(im.getbbox()[1]>=956 for im in v.CAP_IMAGES)

def prepare():
    # Match the first visible entry frame; retain the approved 107-second edit.
    v.ff(['-v','error','-y','-i',v.SRC/'startup-new-take.mp4','-i',BODY,
        '-filter_complex',f'[0:v]trim=start={TRIM}:duration={OPEN},setpts=PTS-STARTPTS[a];[1:v]trim=start={OPEN}:end={v.MAIN},setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0,format=yuv420p[out]',
        '-map','[out]','-an','-r',60,'-c:v','libx264','-preset','fast','-crf',15,v.SRC/'native-continuous.mp4'])
    (v.OUT/'source-alignment.json').write_text(json.dumps({'entry_first_frame':38,'trim_seconds':TRIM,'opening_seconds':OPEN,'native_speed':1,'body_source':str(BODY),'body_source_start':OPEN,'body_source_end':v.MAIN,'source_size':[v.W,v.H]},indent=2))
    print('PREPARED',flush=True)

def audio():
    folder=v.SRC/'audio';folder.mkdir(exist_ok=True)
    assets=json.loads(re.search(r'const A=(\{.*?\});\s*const videos=',(Path(os.environ.get('EVA_INSTALLED_ROOT','D:/Apps/CodexEVA'))/'startup.bundle.js').read_text(encoding='utf-8'),re.S).group(1))
    n=v.DURATION*v.SR
    sfx=np.zeros((n,2),dtype=np.float32);cues=[];voice_stem=np.zeros_like(sfx)
    hex_start=next(c['time']+c['delay'] for c in STATE['audioCues'] if c['name']=='hex-open')
    for cue in STATE['audioCues']:
        name=cue['name'];path=v.SRC/'sfx'/(name+'.wav')
        path.write_bytes(base64.b64decode(assets['sounds'][name].split(',',1)[1]))
        a=v.decode(path)[round(cue['offset']*v.SR):]
        sec=cue['time']+cue['delay'];start=round(sec*v.SR)
        a=a[:n-start]
        source_length=len(a)/v.SR
        if name not in ['voice-complete','hex-open']:
            t=np.arange(len(a))/v.SR+sec
            a*=np.clip(1-(t-hex_start)/.02,0,1)[:,None]
        sfx[start:start+len(a)]+=a*cue['gain']
        if name=='voice-complete':voice_stem[start:start+len(a)]=a*cue['gain']
        cues.append({'name':name,'seconds':sec,'gain':cue['gain'],'source_seconds':source_length})
    voice=next(c for c in cues if c['name']=='voice-complete')
    hexcue=next(c for c in cues if c['name']=='hex-open')
    original=v.decode(v.SRC/'sfx/voice-complete.wav')*voice['gain']
    # Keep the previously approved effects level and low music; no normalization.
    sfx*=.21*GAIN
    music=v.decode(v.SRC/'audio/music-edit.wav')*GAIN
    assert len(music)==n
    t=np.arange(n)/v.SR;u=np.clip((t-OPEN)/1.6,0,1);u=u*u*(3-2*u)
    db=-16+7*u;music*=np.power(10,db[:,None]/20)
    mix=music+sfx
    assert np.max(np.abs(mix))<.99
    assert len(original)==round(1.1613333333333333*v.SR)
    assert np.max(np.abs(voice_stem[round((hexcue['seconds']+.05)*v.SR):round((voice['seconds']+1.1)*v.SR)]))>.01
    for name,a in [('music-lowered.wav',music),('startup-effects.wav',sfx),('completion-voice-full.wav',voice_stem*.21*GAIN),('final-mix.wav',mix)]:v.wav(folder/name,a)
    (v.OUT/'audio-report.json').write_text(json.dumps({'baseline':'Original installed PCM assets aligned to new actual renderer audioCues; captured WebAudio archived separately','completion_voice_seconds':len(original)/v.SR,'completion_voice_start':voice['seconds'],'completion_voice_end':voice['seconds']+len(original)/v.SR,'hex_open_start':hexcue['seconds'],'hex_open_source_seconds':next(c['source_seconds'] for c in cues if c['name']=='hex-open'),'editorial_restoration':'Original completion voice kept in full across native transition fade; installed logic unmodified','music_db_relative_to_v5':{'startup':-16,'body':-9,'release_seconds':1.6},'previous_linear_gain':GAIN,'normalization':False,'peak':float(np.max(np.abs(mix))),'cues':cues},indent=2),encoding='utf-8')
    print('AUDIO COMPLETE',flush=True)

def finish():
    v.ff(['-v','error','-y','-i',v.PROJECT/'picture-master.mp4','-i',v.SRC/'audio/final-mix.wav','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','320k','-t',v.DURATION,'-movflags','+faststart','-metadata','title=CODEX-THEME-EVA02','-metadata','artist=lilin.','-metadata','comment=Latest installed native renderer replay; complete Japanese voice tail restored in film mix; no top corner editorial text.',VIDEO])
    for name in ['finish.py','film_common.py']:shutil.copy2(v.ROOT/'promo'/name,v.PROJECT/name)
    assert v.BACKGROUND.is_file()
    (v.OUT/'edit-decisions.json').write_text(json.dumps({'duration':v.DURATION,'fps':60,'frame_box':v.BOX,'top_corner_editorial_text':False,'captions':v.CAPTIONS,'body_reused_after_verifying_installed_theme':str(BODY),'new_startup':str(v.SRC/'startup-new-take.mp4'),'endcard':[v.MAIN,v.DURATION],'author':'lilin.','display_version':'1.0.0'},ensure_ascii=False,indent=2),encoding='utf-8')
    (v.OUT/'README.txt').write_text('CODEX-THEME-EVA02 / lilin. / v1.0.0\n107秒，1920×1080 / 60fps。\n本轮补录当前实装启动bundle的原生renderer重播；不是冷启动测速。当前启动bundle与最新v10.11工程一致，主题R7-installed-6。\n删除顶部左右角全部后期文字，实机区域扩大；底部保留设计讲解与原型标识。正文沿用已核验同版本的真实原片，维持对话区和HTML设计页慢速展示。\n按新录实际audioCues对齐实装原始PCM音轨。实装本身在蜂窝展开时淡出先前声音；成片混音保留完整1.161秒“同期、完了。”，尾音跨入完整蜂窝展开音效。没有修改已安装主题的声音行为。WebAudio捕获另存归档。\n音乐相对原v5开机降低16dB、正文降低9dB，1.6秒平滑释放；没有再次归一化响度。\nR7-interactive.html是会话附件内打开的独立设计原型，底部已标注。片尾使用实装对话背景图，作者lilin.，版本1.0.0。未公开发布。\n原片、真实捕获音轨、混音分轨在sources，工程在project。\n',encoding='utf-8')
    print('FINISHED',VIDEO,VIDEO.stat().st_size,flush=True)

def qc():
    p=v.ff(['-i',VIDEO,'-map','0:v:0','-an','-vf','vfrdet,freezedetect=n=-60dB:d=1','-progress','pipe:1','-f','null','-'])
    log=p.stderr.decode(errors='replace');(v.OUT/'video-qc.log').write_text(log,encoding='utf-8')
    assert re.findall(r'^frame=(\d+)',p.stdout.decode(),re.M)[-1]==str(v.DURATION*60)
    assert '1920x1080' in log and '60 fps' in log and 'VFR:0.000000' in log
    a=v.ff(['-i',VIDEO,'-vn','-af','loudnorm=I=-16:TP=-1:LRA=11:print_format=json','-f','null','-'])
    m=json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}',a.stderr.decode())[-1]);(v.OUT/'audio-qc.log').write_bytes(a.stderr)
    assert -28<float(m['input_i'])<-23 and float(m['input_tp'])<-8,m
    folder=v.OUT/'qc-frames';folder.mkdir(exist_ok=True)
    times=[1,8,12.8,13.4,14,14.7,v.at('overall')+.7,v.at('select_showcase')+.4,v.at('conversation')+1,v.at('palette')+1.5,v.at('code_diff')+2,v.at('composer')+1.2,v.at('tabs')+.8,v.at('prototype')+1,v.at('prototype_states')+2,v.at('prototype_composer')+2,v.at('plugins')+.8,v.MAIN+2]
    for t in times:v.ff(['-v','error','-y','-ss',t,'-i',VIDEO,'-frames:v',1,'-q:v',2,folder/f'{t:06.2f}.jpg'])
    v.contact(folder,v.OUT/'final-contact-sheet.jpg');v.endcard(v.MAIN+2).save(v.OUT/'cover.jpg',quality=96)
    freezes=[float(x) for x in re.findall(r'freeze_start: ([\d.]+)',log)]
    unexpected=[x for x in freezes if not v.at('select_showcase')<=x<=v.at('conversation')]
    assert not unexpected,unexpected
    report={'file':str(VIDEO),'bytes':VIDEO.stat().st_size,'sha256':hashlib.sha256(VIDEO.read_bytes()).hexdigest(),'duration':v.DURATION,'fps':60,'frames':v.DURATION*60,'size':[1920,1080],'decode_errors':0,'vfr_intervals':0,'audio_lufs':m['input_i'],'true_peak_dbtp':m['input_tp'],'top_corner_editorial_text':False,'full_original_completion_voice_in_mix':True,'no_loudness_renormalization':True,'freeze_start_over_1s':freezes,'unexpected_freezes':unexpected,'keyframes':times}
    (v.OUT/'QC-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True),flush=True)

if __name__=='__main__':{'prepare':prepare,'sample':v.sample,'render':v.render,'audio':audio,'finish':finish,'qc':qc}[sys.argv[1]]()
