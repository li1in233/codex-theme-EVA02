(() => {
  if(window.__evaStartup) return;
  const config=__EVA_CONFIG__;
  const preparationStarted=performance.now(),hold=!!window.__evaStartupHold;
  delete window.__evaStartupHold;
  const result={version:'S4-C3-1.5s-installed-10.10',started:false,prepared:false,completed:false,ready:false,reason:'preparing',phases:[],phaseTiming:{},longTasks:[],audioCues:[],seekCorrections:0,progressSemantics:'stage-weighted estimate; 100 requires verified host readiness'};
  const progressPace=2+Math.random()*4;result.progressPace=progressPace;
  let progressFloor=18,displayedProgress=18;
  let host=null,restore=()=>{},finished=false,watch=0,deadline=0,frameId=0,hexPlayer=null,hexVideoStarted=false,handoffPending=hold;
  const longTasks=new PerformanceObserver(list=>{for(const task of list.getEntries())result.longTasks.push({at:task.startTime,duration:task.duration,phase:result.phase||result.reason});result.longTasks=result.longTasks.slice(-16);});
  longTasks.observe({type:'longtask',buffered:true});
  const savedFocus=document.activeElement;
  function finish(reason){
    if(finished)return;finished=true;clearInterval(watch);clearTimeout(deadline);cancelAnimationFrame(frameId);longTasks.disconnect();
    if(hexVideoStarted){const q=videos['hex-open'].getVideoPlaybackQuality?.();if(q)result.hexVideoQuality={total:q.totalVideoFrames,dropped:q.droppedVideoFrames,time:videos['hex-open'].currentTime};}
    try{hexPlayer?.dispose();stopSounds();stopVideos();audioContext?.close().catch(()=>{});for(const video of Object.values(videos)){video.removeAttribute('src');video.load();}}catch{}
    restore();host?.remove();document.removeEventListener('keydown',key,true);window.removeEventListener('resize',resize);
    result.reason=reason;result.completed=reason==='completed';result.finishedAt=performance.now();
    if(savedFocus?.isConnected&&typeof savedFocus.focus==='function')savedFocus.focus({preventScroll:true});
    if(document.activeElement===document.body)document.querySelector('.ProseMirror[contenteditable="true"]')?.focus({preventScroll:true});
  }
  const key=e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();finish('skipped');}};
  function release(){if(finished)return;handoffPending=false;result.coverReleasedAtMs=performance.now();if(result.ready){readyAt=elapsed();result.readyAt=readyAt;}}
  window.__evaStartup={state:()=>({...result,phases:result.phases.slice()}),play:options=>begin(options),release,skip:()=>finish('skipped')};
  if(!window.__evaTheme?.motion()){longTasks.disconnect();result.reason='reduced-motion';finished=true;return;}
  host=document.createElement('div');host.id='eva-startup-overlay';
  const root=host.attachShadow({mode:'closed'});
  const css=document.createElement('style');css.textContent=`:host{position:fixed;inset:0;z-index:2147483645;display:block;pointer-events:auto;-webkit-app-region:no-drag;background:transparent;font:13px/1.6 'Segoe UI','Microsoft YaHei',sans-serif;color:#eee6e0}
    *{box-sizing:border-box}canvas{width:100%;height:100%;display:block;background:transparent}button{position:absolute;right:24px;top:48px;width:112px;height:40px;border:1px solid #9b7457;background:#0c0c0ccc;color:#eee6e0;padding:8px 14px;cursor:pointer;border-radius:4px;font:inherit;-webkit-app-region:no-drag}button:hover{background:#4b3814e6;border-color:#d3ae50}button:focus-visible{outline:2px solid #d3ae50;outline-offset:3px}
    button{z-index:3}#progress{position:absolute;left:89.583333%;top:94.444444%;width:6.944444%;height:2.962963%;display:flex;align-items:center;justify-content:flex-end;background:transparent;color:#bc9a56;font-family:Consolas,monospace;line-height:1;white-space:pre;pointer-events:none;z-index:2}#status{position:absolute;left:24px;bottom:16px;color:#d4b7a8;pointer-events:none}#status:empty{display:none}.hidden{display:none}`;
  root.append(css);
  const canvas=document.createElement('canvas');canvas.id='screen';canvas.width=1440;canvas.height=810;canvas.setAttribute('aria-label','二号机启动动画');root.append(canvas);
  const skip=document.createElement('button');skip.textContent='跳过 · Esc';skip.onclick=()=>finish('skipped');root.append(skip);
  const percent=document.createElement('div');percent.id='progress';percent.textContent='000 %';percent.style.visibility='hidden';percent.setAttribute('aria-label','启动进度估计');root.append(percent);
  const status=document.createElement('div');status.id='status';status.textContent='正在准备本地影音…';status.setAttribute('role','status');root.append(status);
  for(const id of ['wave-study','hex-study','study-description']){const node=document.createElement('span');node.id=id;node.className='hidden';root.append(node);}
  document.body.append(host);document.addEventListener('keydown',key,true);
  const appRoot=document.querySelector('#root');if(appRoot){const wasInert=appRoot.inert;appRoot.inert=true;restore=()=>{appRoot.inert=wasInert;};}
  const ctx=canvas.getContext('2d'),W=1440,H=810;
  function resize(){
    const ratio=window.devicePixelRatio||1,bounds=host.getBoundingClientRect();
    canvas.width=Math.max(1,Math.round(bounds.width*ratio));canvas.height=Math.max(1,Math.round(bounds.height*ratio));
    ctx.setTransform(canvas.width/W,0,0,canvas.height/H,0,0);
    ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';
    result.surface={width:canvas.width,height:canvas.height,dpr:ratio};
    percent.style.fontSize=(bounds.width/1440*16)+'px';hexPlayer?.resize();
  }
  resize();window.addEventListener('resize',resize);
  const clamp=(v,a=0,b=1)=>Math.min(b,Math.max(a,v)),mix=(a,b,t)=>a+(b-a)*t,ease=t=>{t=clamp(t);return t*t*(3-2*t)};
  const T={entry:7.5/1.8,lcl:2.4,grid:2.15,minimum:11,merge:1.85,fade:.25};
  T.gridAt=T.entry+T.lcl;T.confirmAt=T.gridAt+T.grid;T.bridgeAt=T.confirmAt+.20;T.waveAt=T.bridgeAt+.50;
  const A=__EVA_ASSETS__;
  const videos={},sounds=new Map(),playing=new Set(),opticalTexture=new Image();opticalTexture.src=A.optical;
  let audioContext=null,muted=!!config.muted,lastPhase='',currentVideo=null,started=0,readyAt=null,stable=0,lastObservation=0,lastFrame=0,beginning=false,nativeTimeline=null;
  const correctedAt=new WeakMap();
  for(const [name,url]of Object.entries(A.videos)){const video=document.createElement('video');video.src=url;video.muted=true;video.playsInline=true;video.preload='auto';video.load();videos[name]=video;}
  const imagesReady=Promise.all([opticalTexture.decode(),...Object.values(videos).map(video=>new Promise((ok,no)=>{
    if(video.readyState>=2)return ok();video.addEventListener('loadeddata',ok,{once:true});video.addEventListener('error',()=>video===videos['hex-open']?ok():no(Error('media-decode-failed')),{once:true});
  }))]);
  __EVA_ENGINE__
  __EVA_HEX_PLAYER__
  function prepareHex(){
    const at=T.minimum+T.merge+T.fade;
    opticalScene(at,{phase:'hex',progress:100,releaseAt:T.minimum,hexAt:at});
    shot.width=canvas.width;shot.height=canvas.height;shotCtx.setTransform(shot.width/W,0,0,shot.height/H,0,0);shotCtx.drawImage(canvas,0,0,W,H);
    const video=videos['hex-open'];
    if(video?.readyState>=2){
      video.style.cssText='position:absolute;inset:0;width:100%;height:100%;object-fit:fill;pointer-events:none;visibility:hidden;transform:translateZ(0)';root.append(video);
      video.addEventListener('error',()=>{result.hexFailure='alpha-video-playback';video.style.visibility='hidden';canvas.style.visibility='visible';});
      result.hexBackend='compositor-alpha-video';return;
    }
    try{hexPlayer=createHexPlayer();result.hexBackend=hexPlayer?'webgl-batched':'canvas-recovery';}
    catch(error){result.hexFailure=String(error.message);result.hexBackend='canvas-recovery';}
  }
  function elapsed(){return (performance.now()-started)/1000;}
  const visible=node=>!!node&&node.getBoundingClientRect().width>0&&node.getBoundingClientRect().height>0&&getComputedStyle(node).visibility!=='hidden';
  function observeHost(){
    if(finished)return;
    const editor=[...document.querySelectorAll('.ProseMirror[contenteditable="true"]')].find(visible);
    const nav=[...document.querySelectorAll('[data-app-action-sidebar-scroll],[data-app-action-sidebar-project-row],[data-app-action-sidebar-thread-row]')].find(visible);
    const blocking=[...document.querySelectorAll('[role="dialog"][aria-modal="true"]')].some(visible);
    if(blocking){finish('host-dialog');return;}
    if(!editor&&!nav){
      const login=[...document.querySelectorAll('button')].some(e=>visible(e)&&/^(log in|sign in|登录|登入|使用其他方式登录)/i.test(e.textContent.trim()));
      if(login){finish('host-login');return;}
    }
    const usable=!!editor&&!!nav&&!editor.hasAttribute('disabled')&&editor.getAttribute('aria-disabled')!=='true'&&document.readyState==='complete';
    const now=performance.now();
    if(usable){if(now-lastObservation>=220){stable++;lastObservation=now;}}else{stable=0;lastObservation=0;readyAt=null;result.ready=false;}
    if(stable>=2&&readyAt===null){readyAt=result.started?elapsed():0;result.ready=true;result.readyAt=readyAt;result.hostReadyAtMs=now;}
  }
  function simulation(t){
    const releaseAt=readyAt===null||handoffPending?null:Math.max(T.minimum,readyAt),hexAt=releaseAt===null?null:releaseAt+T.merge+T.fade;
    const progress=result.ready?100:Math.min(99,Math.max(displayedProgress,progressFloor+(99-progressFloor)*(1-Math.exp(-Math.max(0,t-(result.nativeHandoffSeconds||0))/progressPace))));
    displayedProgress=progress;
    const phase=hexAt!==null&&t>=hexAt?'hex':releaseAt!==null&&t>=releaseAt?'merge':t<T.entry?'entry':t<T.gridAt?'lcl':t<T.confirmAt?'grid':t<T.bridgeAt?'confirm':t<T.waveAt?'bridge':'sync';
    const media=phase==='entry'?{key:'entry-02',at:t}:['grid','confirm','bridge'].includes(phase)?{key:'system-grid',at:Math.min(T.grid-.06,t-T.gridAt),freeze:phase!=='grid'}:null;
    let motionTime=t;
    if(nativeTimeline){
      const fps=nativeTimeline.fps;
      const tick=Math.max(0,Math.floor((nativeTimeline.position+(Date.now()-nativeTimeline.sampleMs)/1000)*fps));
      const first=11*fps,span=29*fps;
      motionTime=(tick<first?tick:first+(tick-first)%span)/fps;
    }
    return {phase,progress,readyAt,releaseAt,hexAt,media,motionTime,hostStatus:result.ready?'WORKBENCH READY':'CHECKING INTERACTION',done:hexAt!==null&&t>hexAt+hexDuration+.25};
  }
  function draw(t,s){
    if(s.phase==='entry'){ctx.fillStyle='#040607';ctx.fillRect(0,0,W,H);const v=videos['entry-02'];if(v.readyState>=2)ctx.drawImage(v,0,0,W,H);text('EVA-02 / ENTRY PLUG',W-36,H-28,12,'#e6c9a6','right');}
    else if(['grid','confirm','bridge'].includes(s.phase)){opticalScene(t,s,{display:false,hud:false,shade:false});opticalGrid(t,s);smallHUD(t,s);vignette(.35);}
    else if(s.phase==='hex'){
      if(result.hexBackend==='compositor-alpha-video'&&!result.hexFailure){
        if(!hexVideoStarted){
          hexVideoStarted=true;result.hexPlaybackStartAtMs=performance.now();const video=videos['hex-open'];video.style.visibility='visible';canvas.style.visibility='hidden';
          video.play().catch(()=>{result.hexFailure='alpha-video-play';video.style.visibility='hidden';canvas.style.visibility='visible';});
        }
      }else{drawWorkbench();if(!hexPlayer?.draw(t-s.hexAt)){result.hexBackend='canvas-recovery';studyHex(t-s.hexAt);}}
    }
    else opticalScene(t,s);
  }
  function stopSounds(){for(const sound of [...playing])sound.stop();}
  function stopVideos(){for(const video of Object.values(videos))video.pause();currentVideo=null;}
  let cueOffset=0;
  function playSound(name,{loop=false,gain=.8,delay=0}={}){
    const buffer=sounds.get(name);if(!buffer||!audioContext||muted)return;
    if(audioContext.state!=='running'){audioContext.resume().then(()=>{if(!finished)playSound(name,{loop,gain,delay});}).catch(()=>{});return;}
    let offset=Math.max(0,cueOffset-delay);delay=Math.max(0,delay-cueOffset);
    if(loop)offset%=buffer.duration;else if(offset>=buffer.duration)return;
    const source=audioContext.createBufferSource(),volume=audioContext.createGain();source.buffer=buffer;source.loop=loop;volume.gain.value=gain;source.connect(volume);volume.connect(audioContext.destination);
    let ended=false;const track={name,loop,stop(fade=false){if(ended)return;if(fade){volume.gain.setValueAtTime(volume.gain.value,audioContext.currentTime);volume.gain.linearRampToValueAtTime(0,audioContext.currentTime+.02);try{source.stop(audioContext.currentTime+.025)}catch{}return;}ended=true;try{source.stop()}catch{}source.disconnect();volume.disconnect();playing.delete(track);}};
    source.onended=()=>track.stop();playing.add(track);source.start(audioContext.currentTime+delay,offset);
    result.audio=audioContext.state;result.audioCues.push({name,phase:result.phase,offset,delay,gain,state:audioContext.state,time:elapsed()});
  }
  async function prepareAudio(){
    if(muted)return;audioContext=new(window.AudioContext||window.webkitAudioContext)();
    await audioContext.resume();
    await Promise.all(Object.entries(A.sounds).map(async([name,url])=>{const bytes=Uint8Array.from(atob(url.split(',')[1]),c=>c.charCodeAt(0));sounds.set(name,await audioContext.decodeAudioData(bytes.buffer));}));
    result.audio=audioContext.state;
  }
  function cue(s){
    if(handoffPending)return;
    if(s.phase===lastPhase)return;lastPhase=s.phase;
    if(result.phases.at(-1)?.phase!==s.phase)result.phases.push({phase:s.phase,time:elapsed()});
    const phaseAt={entry:0,lcl:T.entry,grid:T.gridAt,confirm:T.confirmAt,bridge:T.bridgeAt,sync:T.waveAt,merge:s.releaseAt,hex:s.hexAt}[s.phase];
    cueOffset=Math.max(0,elapsed()-(phaseAt??elapsed()));
    for(const sound of [...playing])if(sound.loop)sound.stop();
    if(s.phase==='entry'){playSound('entry-original',{gain:.78});playSound('voice-plug',{gain:.7,delay:.12});}
    if(s.phase==='lcl'){playSound('lcl-water',{gain:.53});playSound('voice-lcl',{gain:.88});}
    if(s.phase==='grid'){playSound('grid-original',{gain:.45});playSound('voice-system',{gain:.88});}
    if(s.phase==='confirm')playSound('system-confirm',{gain:.72});
    if(s.phase==='sync')playSound('voice-sync',{gain:.88});
    if(s.phase==='merge')playSound('voice-complete',{gain:.88,delay:1.5});
    if(s.phase==='hex'){for(const sound of [...playing])sound.stop(true);cueOffset=0;playSound('hex-open',{gain:.8});}
  }
  function updateVideo(s){
    if(!s.media){if(currentVideo){videos[currentVideo].pause();currentVideo=null;}return;}
    const video=videos[s.media.key];
    if(s.media.freeze){stopVideos();if(!video.seeking&&Math.abs(video.currentTime-s.media.at)>.01)video.currentTime=s.media.at;return;}
    if(currentVideo!==s.media.key){stopVideos();currentVideo=s.media.key;if(Math.abs(video.currentTime-s.media.at)>.06&&!video.seeking)video.currentTime=s.media.at;video.play().catch(()=>{});}
    // A pending seek must finish before another correction can be requested.
    if(!video.seeking&&Math.abs(video.currentTime-s.media.at)>.35&&performance.now()-(correctedAt.get(video)||0)>750){video.currentTime=s.media.at;correctedAt.set(video,performance.now());result.seekCorrections++;}
  }
  function frame(){
    if(finished)return;
    try{
      const now=performance.now(),t=elapsed(),state=simulation(t);result.time=t;result.phase=state.phase;result.progress=Math.floor(state.progress);
      if(lastFrame)result.maxFrameGapMs=Math.max(result.maxFrameGapMs||0,now-lastFrame);
      if(state.phase==='entry'&&lastFrame)result.entryMaxFrameGapMs=Math.max(result.entryMaxFrameGapMs||0,now-lastFrame);lastFrame=now;
      if(state.phase!=='entry'&&!result.entryVideoQuality){const q=videos['entry-02'].getVideoPlaybackQuality?.();if(q)result.entryVideoQuality={total:q.totalVideoFrames,dropped:q.droppedVideoFrames};}
      const hexVideo=videos['hex-open'];
      const hexStillPlaying=result.hexBackend==='compositor-alpha-video'&&!result.hexFailure&&(!hexVideoStarted||hexVideo.currentTime<hexDuration+.10&&now-result.hexPlaybackStartAtMs<5000);
      const hexSoundPlaying=[...playing].some(sound=>sound.name==='hex-open')&&now-result.hexPlaybackStartAtMs<2000;
      if(state.done&&!hexStillPlaying&&!hexSoundPlaying){finish('completed');return;}
      const timing=result.phaseTiming[state.phase]??={frames:0,firstMs:now,lastMs:now,maxGapMs:0,totalDrawMs:0,maxDrawMs:0};
      if(timing.frames)timing.maxGapMs=Math.max(timing.maxGapMs,now-timing.lastMs);timing.lastMs=now;timing.frames++;timing.fps=timing.frames>1?(timing.frames-1)*1000/(now-timing.firstMs):0;
      updateVideo(state);const drawAt=performance.now();draw(t,state);const drawMs=performance.now()-drawAt;timing.totalDrawMs+=drawMs;timing.maxDrawMs=Math.max(timing.maxDrawMs,drawMs);
      percent.style.visibility=t>=T.entry?'visible':'hidden';const value=String(Math.floor(state.progress)).padStart(3,'0')+' %';if(percent.textContent!==value)percent.textContent=value;percent.style.color=state.progress===100?'#d6e1c8':'#bc9a56';
      cue(state);frameId=requestAnimationFrame(frame);
    }catch(error){result.error=String(error.message);finish('render-error');}
  }
  deadline=setTimeout(()=>finish('media-timeout'),12000);
  ctx.fillStyle='#080a0d';ctx.fillRect(0,0,W,H);
  async function primeEntry(){
    if(finished)return;
    const video=videos['entry-02'];
    await new Promise((ok,no)=>{
      const timer=setTimeout(()=>no(Error('first-frame-timeout')),4000);
      const ready=()=>{clearTimeout(timer);video.pause();ok();};
      if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(ready);else video.addEventListener('playing',ready,{once:true});
      video.play().catch(error=>{clearTimeout(timer);no(error);});
    });
    if(finished)return;
    // Never leave the opening frame underneath a native cover already showing synchronization.
    draw(hold?T.waveAt+1:0,simulation(hold?T.waveAt+1:0));
    result.preparedFramePhase=hold?'sync':'entry';
    const hex=videos['hex-open'];
    if(result.hexBackend==='compositor-alpha-video'){
      try{
        await new Promise((ok,no)=>{const timer=setTimeout(()=>no(Error('hex-first-frame-timeout')),4000);hex.requestVideoFrameCallback(()=>{clearTimeout(timer);hex.pause();ok();});hex.play().catch(no);});
        if(hex.currentTime>.001)await new Promise(ok=>{hex.addEventListener('seeked',ok,{once:true});hex.currentTime=0;});
      }catch(error){hex.pause();result.hexFailure=String(error.message);result.hexBackend='canvas-recovery';}
    }
    await new Promise(ok=>requestAnimationFrame(()=>requestAnimationFrame(ok)));
  }
  async function begin(options={}){
    if(finished||beginning||result.started||!result.prepared)return;
    beginning=true;
    const offset=Math.max(0,Math.min(20,Number(options?.offsetSeconds)||0));
    progressFloor=Math.max(18,Math.min(99,Number(options?.initialProgress)||90));displayedProgress=progressFloor;
    result.initialProgress=progressFloor;result.nativeHandoffSeconds=offset;
    if(Number.isFinite(options.nativePlaybackSeconds)&&Number.isFinite(options.nativeSampleUnixMs)){
      nativeTimeline={position:options.nativePlaybackSeconds,sampleMs:options.nativeSampleUnixMs,fps:options.nativeFps===24?24:48};
      result.nativeTimeline={...nativeTimeline};
    }
    const state=simulation(offset);
    try{
      if(state.media){
        currentVideo=state.media.key;const video=videos[currentVideo];
        if(Math.abs(video.currentTime-state.media.at)>.02){
          await new Promise((ok,no)=>{const timer=setTimeout(()=>no(Error('handoff-seek-timeout')),2000);video.addEventListener('seeked',()=>{clearTimeout(timer);ok();},{once:true});video.currentTime=state.media.at;});
        }
        if(!state.media.freeze)await video.play();else video.pause();
      }else stopVideos();
    }
    catch(error){result.error=String(error.message);finish('media-error');return;}
    if(finished)return;
    started=performance.now()-offset*1000;lastFrame=0;result.started=true;result.reason='running';status.textContent='';
    if(result.ready){readyAt=offset;result.readyAt=readyAt;result.hostReadyBeforeHandoff=true;}
    if(offset){
      result.nativeHandoffSeconds=offset;
      for(const [phase,time]of [['entry',0],['lcl',T.entry],['grid',T.gridAt],['confirm',T.confirmAt],['bridge',T.bridgeAt],['sync',T.waveAt]]){
        if(time<=offset)result.phases.push({phase,time,native:true});
      }
    }
    observeHost();frame();
    await new Promise(ok=>requestAnimationFrame(()=>requestAnimationFrame(ok)));
    result.handoffFramePainted=!finished;
  }
  observeHost();watch=setInterval(observeHost,250);
  Promise.all([imagesReady,prepareAudio().catch(()=>{result.audio='unavailable';})]).then(prepareHex).then(primeEntry).then(()=>{
    if(finished)return;clearTimeout(deadline);result.prepared=true;result.preparationMs=performance.now()-preparationStarted;result.reason='prepared';status.textContent='';
    if(!hold)begin();
  }).catch(error=>{result.error=String(error.message);finish('media-error');});
  window.addEventListener('pagehide',()=>finish('pagehide'),{once:true});
})();
