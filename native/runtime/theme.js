(() => {
  if (window.__evaTheme) return;
  const config = __EVA_CONFIG__;
  const style = document.createElement('style');
  style.id = 'eva-r7-theme';
  style.textContent = __EVA_CSS__;
  document.documentElement.append(style);
  document.documentElement.dataset.evaTheme = 'r7';
  const rowSelector = '[data-app-action-sidebar-thread-row]';
  const records = new Map(), headers = new Map(), wallpaperNodes = new Set();
  const wallpaperLayout=entries=>{
    for(const entry of entries){const node=entry.target,w=node.clientWidth,h=node.clientHeight;
      if(w<=0||h<=0)continue;
      const height=Math.min(h*(1-145/1385),w*2481/1754),width=height*1754/2481;
      node.style.setProperty('--eva-art-size',`${width}px ${height}px`);
      node.style.setProperty('--eva-art-position',`${(w-width)*.48}px ${h-height-h*12/1385}px`);
    }
  };
  const wallpaperObserver=new ResizeObserver(wallpaperLayout);
  const systemMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const loadMotion=()=>{try{return localStorage.getItem('eva-r7-motion')}catch{return null}};
  const saveMotion=value=>{try{localStorage.setItem('eva-r7-motion',value)}catch{}};
  let preference = loadMotion() || config.motion || 'system';
  let pending = false, destroyed = false, selections = 0;
  const motion = () => preference === 'on' || (preference === 'system' && !systemMotion.matches);
  const selected = row => row.getAttribute('data-app-action-sidebar-thread-active') === 'true';
  const decorationCSS = `:host{position:absolute;inset:0;pointer-events:none;z-index:-1;overflow:hidden;border-radius:inherit;display:block}
    i{position:absolute;display:block;pointer-events:none}.plate{inset:0;background:#9b3238;border:1px solid #9e3b40;clip-path:polygon(7px 0,100% 0,100% calc(100% - 7px),calc(100% - 7px) 100%,0 100%,0 7px);transform:translateY(105%)}
    .rail{left:2px;top:5px;bottom:5px;width:1px;background:#6f3438}.rail.r{left:auto;right:2px}.lock{left:2px;top:calc(50% - 5px);width:3px;height:10px;background:#d3ae50;transform:translateX(-16px)}.lock.r{left:auto;right:2px;transform:translateX(16px)}
    .lamp{left:7px;top:calc(50% - 2px);width:3px;height:4px;background:#75433a}.lift{left:10px;right:10px;bottom:2px;height:2px;background:#ce4c42;transform:translateY(18px)}
    :host(:not([selected]):not([hover])) i{opacity:0}:host([hover]:not([selected])){background:#392127;box-shadow:inset 0 0 0 1px #82404a}:host([hover]:not([selected])) .plate,:host([hover]:not([selected])) .lift{opacity:0}
    :host([hover]:not([selected])) .rail{background:#ad554f;opacity:.9}:host([hover]:not([selected])) .lamp{background:#bb6953;opacity:.8}:host([hover]:not([selected])) .lock{background:#ad554f;opacity:.45;transform:translateX(-4px)}:host([hover]:not([selected])) .lock.r{transform:translateX(4px)}
    :host-context([data-app-action-sidebar-thread-row]:has(:focus-visible)){box-shadow:inset 0 0 0 2px #edca87}:host-context([data-app-action-sidebar-thread-row]:has(:focus-visible)) .rail,:host-context([data-app-action-sidebar-thread-row]:has(:focus-visible)) .lamp{opacity:.9}
    :host([selected]) .plate,:host([selected]) .lock,:host([selected]) .lift{transform:translate(0)}:host([selected]) .rail{background:#d3ae50}:host([selected]) .lamp{background:#f1c96e}:host([selected][hover]) .plate{background:#ad3a3d}`;
  function decorate(row) {
    let rec = records.get(row);
    if (rec && rec.host.parentNode === row) return rec;
    rec?.animations.forEach(a => a.cancel());
    const host = document.createElement('span');
    host.dataset.evaDecoration = '';
    host.setAttribute('aria-hidden', 'true');
    const root = host.attachShadow({mode:'closed'});
    const css = document.createElement('style'); css.textContent = decorationCSS; root.append(css);
    for (const name of ['plate','rail','rail r','lamp','lift','lock','lock r']) {
      const item = document.createElement('i'); item.className = name; root.append(item);
    }
    row.append(host);
    rec = {host, root, active:selected(row), animations:[], generation:0};
    host.toggleAttribute('selected', rec.active);
    records.set(row,rec);
    return rec;
  }
  function animate(row) {
    const rec = decorate(row), generation = ++rec.generation;
    rec.animations.forEach(a => a.cancel());rec.animations=[];
    if (!selected(row)) return;
    rec.host.setAttribute('selected','');
    if (!motion()) return;
    selections++;
    const add = (selector, frames) => rec.animations.push(rec.root.querySelector(selector).animate(frames,{duration:540,easing:'linear',fill:'both'}));
    add('.plate',[{transform:'translateY(105%)',offset:0},{transform:'translateY(105%)',offset:.07},{transform:'translateY(0)',offset:2/3},{transform:'translateY(0)',offset:1}]);
    add('.lift',[{transform:'translateY(18px)',opacity:0,offset:0},{transform:'translateY(0)',opacity:1,offset:2/3},{transform:'translateY(0)',opacity:1,offset:1}]);
    add('.lock:not(.r)',[{transform:'translateX(-16px)',offset:0},{transform:'translateX(-16px)',offset:2/3},{transform:'translateX(0)',offset:8/9},{transform:'translateX(0)',offset:1}]);
    add('.lock.r',[{transform:'translateX(16px)',offset:0},{transform:'translateX(16px)',offset:2/3},{transform:'translateX(0)',offset:8/9},{transform:'translateX(0)',offset:1}]);
    add('.lamp',[{background:'#75433a',offset:0},{background:'#75433a',offset:2/3},{background:'#ffe8a1',offset:8/9},{background:'#f1c96e',offset:1}]);
    Promise.all(rec.animations.map(a=>a.finished.catch(()=>null))).then(()=>{
      if(rec.generation===generation){rec.animations.forEach(a=>a.cancel());rec.animations=[];}
    });
  }
  function refresh() {
    pending=false;if(destroyed)return;
    document.querySelectorAll(rowSelector).forEach(row=>{
      const rec=decorate(row),active=selected(row);
      rec.host.toggleAttribute('selected',active);
      if(active!==rec.active){rec.active=active;if(active)animate(row);else{++rec.generation;rec.animations.forEach(a=>a.cancel());rec.animations=[];}}
    });
    for(const [row,rec]of records)if(!row.isConnected){rec.animations.forEach(a=>a.cancel());records.delete(row);}
    const activeProject=document.querySelector(`${rowSelector}[data-app-action-sidebar-thread-active=true]`)?.closest('[data-app-action-sidebar-project-list-id]')?.getAttribute('data-app-action-sidebar-project-list-id');
    for(const project of document.querySelectorAll('[data-app-action-sidebar-project-id]'))project.toggleAttribute('data-eva-current-project',!!activeProject&&project.getAttribute('data-app-action-sidebar-project-id')===activeProject);
    for(const timeline of document.querySelectorAll('[data-app-action-timeline-scroll]')) {
      // Mark existing containers only; no message text, controls or layout is replaced.
      let node=timeline.parentElement;
      for(let i=0;node&&i<3;i++,node=node.parentElement)node.dataset.evaConversation='';
      if(!wallpaperNodes.has(timeline)){wallpaperNodes.add(timeline);wallpaperObserver.observe(timeline);}
    }
    for(const header of document.querySelectorAll('[data-app-shell-main-titlebar]')){
      if(headers.get(header)?.isConnected)continue;
      const actions=header.querySelector('[data-app-shell-header-toolbar]')?.lastElementChild;
      if(!actions)continue;
      const mark=document.createElement('span');mark.dataset.evaHeaderMark='';mark.textContent='EVA 02';mark.setAttribute('aria-hidden','true');actions.prepend(mark);headers.set(header,mark);
    }
  }
  const schedule=()=>{if(!pending){pending=true;requestAnimationFrame(refresh);}};
  const observer=new MutationObserver(schedule);
  observer.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['data-app-action-sidebar-thread-active','data-app-action-sidebar-thread-selected']});
  const click=e=>{const row=e.target.closest?.(rowSelector);if(row){setTimeout(()=>{if(selected(row))animate(row)},0);}};
  const hover=e=>{const row=e.target.closest?.(rowSelector);if(row)decorate(row).host.toggleAttribute('hover',e.type==='pointerover');};
  document.addEventListener('click',click,true);
  document.addEventListener('pointerover',hover,true);document.addEventListener('pointerout',hover,true);
  let panel=null;
  function settings(){
    if(panel){panel.remove();panel=null;return;}
    panel=document.createElement('div');panel.dataset.evaSettings='';
    const shadow=panel.attachShadow({mode:'closed'});
    const css=document.createElement('style');css.textContent=':host{position:fixed;right:28px;top:64px;z-index:2147483646;display:block;font:14px/1.7 "Segoe UI","Microsoft YaHei",sans-serif;color:#eee6e0;background:#23181b;border:1px solid #9e3b40;padding:20px;box-shadow:0 12px 48px #0009}button,select{font:inherit;background:#391b20;color:inherit;border:1px solid #9e3b40;padding:6px 10px;margin-left:10px}p{margin:10px 0}small{color:#bfaaa3}';shadow.append(css);
    const title=document.createElement('strong');title.textContent='EVA 02 · R7';shadow.append(title);
    const label=document.createElement('p');label.textContent='机库与片头动效';
    const select=document.createElement('select');
    for(const [value,text]of [['system','跟随系统'],['on','启用主题动效'],['off','减少动态']]){const option=document.createElement('option');option.value=value;option.textContent=text;select.append(option);}
    select.value=preference;select.onchange=()=>{preference=select.value;saveMotion(preference);if(!motion())for(const rec of records.values()){++rec.generation;rec.animations.forEach(a=>a.cancel());rec.animations=[];}};
    label.append(select);shadow.append(label);
    const replay=document.createElement('button');replay.textContent='重播机库升降';replay.onclick=()=>{preference='on';saveMotion('on');select.value='on';for(const row of records.keys())if(selected(row))animate(row);};shadow.append(replay);
    const close=document.createElement('button');close.textContent='关闭';close.onclick=settings;shadow.append(close);
    const note=document.createElement('p');const small=document.createElement('small');small.textContent='Ctrl + Alt + E 打开设置 · 冷启动播放片头 · Esc 跳过';note.append(small);shadow.append(note);document.body.append(panel);
  }
  const key=e=>{if(e.ctrlKey&&e.altKey&&e.code==='KeyE'){e.preventDefault();settings();}else if(e.key==='Escape'&&panel)settings();};document.addEventListener('keydown',key);
  window.__evaTheme={version:'R7-installed-6',motion,settings,replay:()=>{for(const row of records.keys())if(selected(row))animate(row);},motionState:()=>[...records].filter(([row])=>selected(row)).map(([row,rec])=>({plate:getComputedStyle(rec.root.querySelector('.plate')).transform,lock:getComputedStyle(rec.root.querySelector('.lock')).transform,lamp:getComputedStyle(rec.root.querySelector('.lamp')).backgroundColor,animations:rec.animations.filter(a=>a.playState==='running').length})),state:()=>({version:'R7-installed-6',rows:records.size,selected:[...records.keys()].filter(selected).length,selections,motion:motion(),preference,style:style.isConnected}),
    destroy(){destroyed=true;observer.disconnect();wallpaperObserver.disconnect();document.removeEventListener('click',click,true);document.removeEventListener('pointerover',hover,true);document.removeEventListener('pointerout',hover,true);document.removeEventListener('keydown',key);for(const rec of records.values()){rec.animations.forEach(a=>a.cancel());rec.host.remove();}for(const mark of headers.values())mark.remove();for(const node of wallpaperNodes){node.style.removeProperty('--eva-art-size');node.style.removeProperty('--eva-art-position');}panel?.remove();style.remove();delete document.documentElement.dataset.evaTheme;document.querySelectorAll('[data-eva-conversation]').forEach(e=>delete e.dataset.evaConversation);document.querySelectorAll('[data-eva-current-project]').forEach(e=>e.removeAttribute('data-eva-current-project'));delete window.__evaTheme;}};
  refresh();
})();
