import os
from pathlib import Path
import base64,bisect,hashlib,json,re,shutil,subprocess,sys,time,wave
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
from concurrent.futures import ThreadPoolExecutor
from collections import deque

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('EVA_PROMO_ROOT', ROOT/'assets/private/promo'))
SRC=OUT/'sources';PROJECT=OUT/'project';PROJECT.mkdir(parents=True,exist_ok=True)
FF=imageio_ffmpeg.get_ffmpeg_exe();FPS=60;DURATION=0;SR=48000
W,H=1980,1198;CW,CH=1584,958.4;DPR=1.25
BOX=(40,36,1840,904);BASE=BOX[3]/CH
GOLD='#d3ae50';WHITE='#eee6e0';MUTED='#aa9690';BG='#0b0a0d'
DATA=json.loads((SRC/'edit-events.json').read_text());EVENTS=DATA['events'];EV={e['name']:e for e in EVENTS}
CUT=0;OFFSET=0;EXTENSIONS=[]
def at(name):return EV[name]['at']
def old_at(name):return at(name)
def source_time(t):return t
MAIN=DATA['main'];DURATION=__import__('math').ceil(MAIN+4)
SOURCE_END=MAIN;KNOT_SOURCE=[0,MAIN];KNOT_EDIT=KNOT_SOURCE
CN={s:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',s) for s in [16,18,20,24,28,32,34,40]}
EN={s:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',s) for s in [16,18,22,28,36,42,58,64,72,170]}
CAPTIONS=[
 (0,4.17,'CODEX-THEME-EVA02','VERSION / 1.0.0','实装片头重播'),
 (4.17,9.42,'机械刻度与光学网格，建立启动仪式。','STARTUP / GRID & OPTICS','实装片头重播'),
 (9.42,at('overall'),'波形合一，蜂窝逐层让出工作台。','STARTUP / SYNCHRONIZE & REVEAL','实装片头重播'),
 (at('overall'),at('sidebar'),'酒红框架与暖黄标识，贯穿整个工作台。','01 / NATIVE WORKSPACE','原生 Codex · R7-installed-6'),
 (at('sidebar'),at('conversation'),'底板升起、锁扣合拢，点击在同一镜头中落定。','02 / HANGAR SELECTION','原生点击 · 原速动效'),
 (at('conversation'),at('palette'),'暖白正文与暗红引用，拉开阅读层级。','03 / TYPOGRAPHY & QUOTE','全样式展示 · 原生实机'),
 (at('palette'),at('feedback'),'红色建立身份，暖黄提示关注，状态色各司其职。','03 / PALETTE & TABLE','全样式展示 · 原生实机'),
 (at('feedback'),at('code_diff'),'细边框与柔和底色，托住说明和反馈。','03 / FEEDBACK & SURFACE','全样式展示 · 原生实机'),
 (at('code_diff'),at('syntax'),'代码保留语法色，增删用红绿与符号共同区分。','03 / CODE & DIFF','全样式展示 · 原生实机'),
 (at('syntax'),at('checklist'),'低亮背景承托高亮代码，让内容成为焦点。','03 / SYNTAX & CONTRAST','全样式展示 · 原生实机'),
 (at('checklist'),at('composer'),'清单、标题与段落间距，维持清楚的阅读节奏。','03 / LIST & RHYTHM','全样式展示 · 原生实机'),
 (at('composer'),at('open_attachment'),'暖黄焦点线勾出输入区，红色按钮给出行动落点。','04 / COMPOSER & FOCUS','原生输入框'),
 (at('open_attachment'),at('prototype'),'从会话附件进入标签页，再展开设计语言。','05 / ATTACHMENT & EXPAND','原生打开 · R7 设计原型'),
 (at('prototype'),at('prototype_shell'),'切角、双层亮边和锁扣，共同构成机库语言。','06 / DESIGN LANGUAGE','R7 交互原型 · 独立页面'),
 (at('prototype_shell'),at('prototype_states'),'深酒红承托结构，暖黄只出现在需要关注的位置。','06 / STRUCTURE & SIGNAL','R7 交互原型 · 独立页面'),
 (at('prototype_states'),at('prototype_scroll'),'从安静条目到稳定选中，状态逐层加重。','06 / CONVERSATION STATES','R7 交互原型 · 独立页面'),
 (at('prototype_scroll'),at('prototype_projects'),'暗红导轨与克制滑块，延续纵向秩序。','06 / SCROLL RAIL','R7 交互原型 · 独立页面'),
 (at('prototype_projects'),at('prototype_navigation'),'文件夹、分组和缩进，让项目层级清楚可辨。','06 / PROJECT GROUPS','R7 交互原型 · 独立页面'),
 (at('prototype_navigation'),at('prototype_composer'),'搜索与浮层沿用细红框，统一临时界面。','06 / NAVIGATION & OVERLAYS','R7 交互原型 · 独立页面'),
 (at('prototype_composer'),at('prototype_tools'),'附件、模型菜单与输入焦点，保持同一套反馈。','06 / COMPOSER & ATTACHMENTS','R7 交互原型 · 独立页面'),
 (at('prototype_tools'),at('prototype_content'),'执行、审批和结果，靠边框与状态色分出轻重。','06 / TOOLS & FEEDBACK','R7 交互原型 · 独立页面'),
 (at('prototype_content'),at('restore_tab'),'代码、差异和输出面板，延续内容优先的层次。','06 / CONTENT & DETAIL','R7 交互原型 · 独立页面'),
 (at('restore_tab'),MAIN,'红色描边与深色卡片，让插件页保持统一。','07 / PLUGIN DIRECTORY','原生公开目录'),
]
CAMERA=[(0,1,CW/2,CH/2),(at('overall'),1,CW/2,CH/2),
 (at('sidebar'),1.04,780,470),(at('select_showcase'),1.85,530,290),
 (at('conversation')-.1,1.85,530,290),(at('conversation')+.8,1.32,995,475),
 (at('palette'),1.34,995,480),(at('feedback'),1.33,990,485),
 (at('code_diff'),1.34,995,480),(at('syntax'),1.33,995,485),
 (at('checklist'),1.34,995,480),(at('composer'),1.36,990,620),
 (at('focus_composer'),1.46,985,680),(at('open_attachment')-.8,1.39,990,620),
 (at('open_attachment'),1.08,820,478),(at('maximize_tab')-.9,1.025,800,478),
 (at('maximize_tab'),1.02,800,478),(at('prototype'),1.01,792,479),
 (at('prototype_intro')+2,1.025,795,477),
 (at('prototype_shell'),1.018,792,479),(at('prototype_states'),1.024,797,477),
 (at('prototype_scroll'),1.017,792,479),(at('prototype_projects'),1.024,796,477),
 (at('prototype_navigation'),1.017,792,479),(at('prototype_composer'),1.024,796,477),
 (at('prototype_tools'),1.017,792,479),(at('prototype_content'),1.024,796,477),
 (at('restore_tab'),1.01,792,479),(at('open_plugins'),1.015,800,477),(MAIN,1.055,840,470)]
assert all(b[0]>a[0] for a,b in zip(CAMERA,CAMERA[1:]))
P=np.array(DATA['pointer'],dtype=float)
CLICK_NAMES=['select_showcase','focus_composer','open_attachment','maximize_tab','restore_tab','open_plugins']
CLICKS=[(at(n),EV[n]['x'],EV[n]['y'],n) for n in CLICK_NAMES]
BACKGROUND=SRC/'official-nishigori-asuka.png'
POSTER=Image.open(BACKGROUND).convert('RGB')

def ff(args):
    p=subprocess.run([FF,'-hide_banner','-nostdin',*map(str,args)],capture_output=True)
    assert p.returncode==0,p.stderr.decode(errors='replace')[-5000:]
    return p
def ease(x):x=max(0,min(1,x));return x*x*(3-2*x)
def camera(t):
    k=max(0,min(len(CAMERA)-2,bisect.bisect_right([a[0] for a in CAMERA],t)-1));a,b=CAMERA[k:k+2]
    q=ease((t-a[0])/(b[0]-a[0]));z,cx,cy=[a[i]+(b[i]-a[i])*q for i in range(1,4)]
    s=BASE*z;vw=BOX[2]/s;vh=BOX[3]/s
    cx=min(CW-vw/2,max(vw/2,cx)) if vw<CW else CW/2
    cy=min(CH-vh/2,max(vh/2,cy)) if vh<CH else CH/2
    return s,cx-vw/2,cy-vh/2
def point(x,y,cam):s,l,top=cam;return BOX[0]+(x-l)*s,BOX[1]+(y-top)*s
def pointer(d,t,cam):
    if t<at('overall') or t>MAIN:return
    i=max(0,min(len(P)-2,np.searchsorted(P[:,0],t)-1));a,b=P[i:i+2];q=max(0,min(1,(t-a[0])/max(.001,b[0]-a[0])))
    x,y=point(a[1]+(b[1]-a[1])*q,a[2]+(b[2]-a[2])*q,cam)
    if not BOX[0]+2<x<BOX[0]+BOX[2]-24 or not BOX[1]+2<y<BOX[1]+BOX[3]-35:return
    d.polygon([(x+2,y+3),(x+2,y+29),(x+9,y+23),(x+15,y+35),(x+21,y+31),(x+15,y+20),(x+25,y+20)],fill='#000000')
    d.polygon([(x,y),(x,y+26),(x+7,y+20),(x+13,y+32),(x+18,y+29),(x+12,y+18),(x+23,y+18)],fill=GOLD,outline=WHITE,width=1)
    for sec,xx,yy,name in CLICKS:
        u=(t-sec)/.32
        if 0<=u<=1:
            px,py=point(xx,yy,cam);r=6+23*u;d.ellipse((px-r,py-r,px+r,py+r),outline=GOLD,width=max(1,round(3*(1-u))))
def caption(i):
    a,b,title,sub,tag=CAPTIONS[i];im=Image.new('RGBA',(1920,1080));d=ImageDraw.Draw(im)
    d.rectangle((0,956,1920,1080),fill=BG);d.line((72,965,1848,965),fill='#4b242b')
    d.rectangle((72,983,77,1021),fill=GOLD);d.text((96,979),title,font=EN[42] if i==0 else CN[34],fill=WHITE)
    d.text((98,1033),sub,font=EN[18],fill=MUTED)
    d.text((72,10),'CODEX-THEME-EVA02',font=EN[16],fill=MUTED)
    tw=d.textlength(tag,font=CN[16]);d.text((1848-tw,8),tag,font=CN[16],fill=GOLD)
    return im
CAP_IMAGES=[caption(i) for i in range(len(CAPTIONS))]
def endcard(t):
    u=max(0,min(1,(t-(MAIN-.25))/(DURATION-MAIN+.25)))
    # Use the exact installed conversation backdrop, with a slow editorial move.
    scale=(1080/POSTER.height)*(1.31+.035*u)
    iw,ih=round(POSTER.width*scale),round(POSTER.height*scale)
    poster=POSTER.resize((iw,ih),Image.Resampling.BICUBIC)
    bg=Image.new('RGBA',(1920,1080),BG)
    bg.paste(poster,(round(1920-iw-12*u),round(-35-18*u)))
    shade=np.zeros((1080,1920,4),dtype=np.uint8);shade[:,:,:3]=[11,10,13]
    shade[:,:,3]=np.tile(np.interp(np.arange(1920),[0,900,1250,1920],[250,242,148,140]).astype(np.uint8),(1080,1));bg=Image.alpha_composite(bg,Image.fromarray(shade))
    d=ImageDraw.Draw(bg);slide=round(18*(1-ease((t-MAIN+.25)/.65)))
    d.text((112,94),'02',font=EN[170],fill='#6f3037')
    d.text((120,345),'PERSONAL CODEX THEME',font=EN[22],fill=GOLD)
    d.line((120,399,1050,399),fill=GOLD,width=2)
    d.text((116+slide,439),'CODEX-THEME-EVA02',font=EN[64],fill=WHITE)
    d.text((122+slide,550),'lilin.',font=EN[58],fill=GOLD)
    d.text((124,641),'酒红结构 / 暖黄反馈 / 机库动效',font=CN[28],fill=WHITE)
    d.text((124,889),'原生 Codex 主题实录  ·  v1.0.0',font=CN[20],fill=WHITE)
    d.text((124,938),'MUSIC / 鷺巣詩郎 · EM20#070720',font=CN[18],fill=MUTED)
    d.text((124,978),'BACKGROUND / 錦織敦史 · ©khara',font=CN[18],fill=MUTED)
    return bg.convert('RGB')
def frame(im,t):
    if t>=MAIN:return endcard(t)
    out=Image.new('RGB',(1920,1080),BG);cam=camera(t);s,l,top=cam
    view=im.transform((BOX[2],BOX[3]),Image.Transform.AFFINE,(DPR/s,0,l*DPR,0,DPR/s,top*DPR),Image.Resampling.BICUBIC,fillcolor=(11,10,13))
    out.paste(view,BOX[:2]);d=ImageDraw.Draw(out);pointer(d,t,cam)
    for i,(a,b,*_) in enumerate(CAPTIONS):
        if a<=t<b:
            opacity=min(1,(t-a)/.13,(b-t)/.10);layer=CAP_IMAGES[i]
            if opacity<1:
                layer=layer.copy();layer.putalpha(layer.getchannel('A').point(lambda x:round(x*max(0,opacity))))
            out.paste(layer,(0,0),layer);break
    if t>MAIN-.25:out=Image.blend(out,endcard(t),ease((t-MAIN+.25)/.25))
    return out
def source_frame(t):
    raw=ff(['-v','error','-ss',min(source_time(t)+CUT,MAIN-.02),'-i',SRC/'native-continuous.mp4','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','pipe:1']).stdout
    assert len(raw)==W*H*3,len(raw)
    return Image.frombytes('RGB',(W,H),raw)
def contact(folder,path):
    files=sorted(folder.glob('*.jpg'));sheet=Image.new('RGB',(1920,((len(files)+3)//4)*294),BG);d=ImageDraw.Draw(sheet)
    for i,f in enumerate(files):
        im=Image.open(f);im.thumbnail((480,270));x=i%4*480;y=i//4*294;sheet.paste(im,(x,y));d.text((x+8,y+270),f.stem,font=EN[16],fill=GOLD)
    sheet.save(path,quality=94)
def sample():
    folder=OUT/'samples-final';folder.mkdir(exist_ok=True)
    times=[.5,8,13.8,at('overall')+.5,at('select_showcase')+.3,at('conversation')+1.1,at('palette')+1,at('code_diff')+1.5,at('syntax')+1,at('focus_composer')+.9,at('tabs')+.7,at('prototype')+1,at('prototype_states')+2,at('prototype_projects')+2,at('prototype_composer')+2,at('prototype_content')+2,at('plugins')+.6,MAIN+2]
    for t in times:frame(source_frame(t) if t<MAIN else None,t).save(folder/f'{t:06.2f}.jpg',quality=96)
    contact(folder,OUT/'sample-contact.jpg');print('SAMPLE',MAIN,CUT,flush=True)
def render():
    dec=subprocess.Popen([FF,'-v','error','-ss',str(CUT),'-i',str(SRC/'native-continuous.mp4'),'-t',str(SOURCE_END+1/FPS),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    log=(OUT/'render.log').open('wb')
    enc=subprocess.Popen([FF,'-hide_banner','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1920x1080','-framerate','60','-i','pipe:0','-vf','scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p','-an','-c:v','libx264','-preset','fast','-crf','16','-color_range','tv','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart',str(PROJECT/'picture-master.mp4')],stdin=subprocess.PIPE,stderr=log)
    last=None;begun=time.perf_counter();source_frames=0;source_index=-1
    pool=ThreadPoolExecutor(max_workers=4);pending=deque()
    try:
        for n in range(DURATION*FPS):
            if n<MAIN*FPS:
                wanted=round(source_time(n/FPS)*FPS)
                while source_index<wanted:
                    raw=dec.stdout.read(W*H*3)
                    if not raw:break
                    assert len(raw)==W*H*3
                    last=Image.frombytes('RGB',(W,H),raw);source_frames+=1;source_index+=1
                assert last is not None
            pending.append(pool.submit(lambda im,t:frame(im,t).tobytes(),last,n/FPS))
            if len(pending)>=12:enc.stdin.write(pending.popleft().result())
            if n%180==0:print('RENDER',n,'/',DURATION*FPS,'wall',round(time.perf_counter()-begun,1),flush=True)
        while pending:enc.stdin.write(pending.popleft().result())
        enc.stdin.close();assert enc.wait(timeout=120)==0
        dec.stdout.close();dec.wait(timeout=20)
    finally:
        pool.shutdown(wait=True,cancel_futures=True)
        if enc.poll() is None:enc.kill()
        if dec.poll() is None:dec.kill()
        log.close()
    (OUT/'render-report.json').write_text(json.dumps({'frames':DURATION*FPS,'source_frames':source_frames,'size':[1920,1080],'source_size':[W,H],'fps':FPS,'duration':DURATION,'main_seconds':MAIN,'conversation_seconds':at('tabs')-at('conversation'),'source_time_knots':KNOT_SOURCE,'edit_time_knots':KNOT_EDIT,'plugin_source_end':SOURCE_END,'plugin_scroll_included':False,'cut_source_seconds':CUT,'clock_offset':OFFSET,'wall_seconds':time.perf_counter()-begun},indent=2))
def decode(path):return np.frombuffer(ff(['-v','error','-i',path,'-ac','2','-ar',SR,'-f','f32le','pipe:1']).stdout,dtype='<f4').reshape(-1,2).copy()
def wav(path,a):
    assert np.isfinite(a).all() and np.max(np.abs(a))<1,np.max(np.abs(a))
    with wave.open(str(path),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(SR);f.writeframes((a*32767).astype('<i2').tobytes())