/* The film is user-supplied. Host events in this study are explicitly simulated. */
'use strict';
const A=window.S4_ASSETS,canvas=document.querySelector('#screen'),ctx=canvas.getContext('2d'),W=1440,H=810;
const clamp=(v,a=0,b=1)=>Math.min(b,Math.max(a,v)),mix=(a,b,t)=>a+(b-a)*t,ease=t=>{t=clamp(t);return t*t*(3-2*t)};
const T={entry:7.5/1.8,lcl:2.4,grid:2.15,minimum:11,merge:1.85,fade:.25};
T.gridAt=T.entry+T.lcl;T.confirmAt=T.gridAt+T.grid;T.bridgeAt=T.confirmAt+.20;T.waveAt=T.bridgeAt+.50;
const status=document.querySelector('#status'),videos={},sounds=new Map(),playing=new Set();
const opticalTexture=new Image();opticalTexture.src=A.optical;
let audioContext=null,audioPrepared=null,audioEpoch=null,runId=0,running=false,starting=false,raf=0,manualReady=null,lastPhase='',currentVideo=null,lastState={},muted=false;
let started=0,audioFailed=false;const cueHistory=[];
/* Keep the accepted startup above the same live R7 document for every replay. */
const r7Frame=document.querySelector('#r7-workbench');
let r7Ready=false,r7ReadyAt=null,r7Error='',startupSurface=true;
function setStartupSurface(active){
 startupSurface=active;canvas.hidden=!active;r7Frame.inert=active;
 r7Frame.setAttribute('aria-hidden',String(active));
 document.querySelector('.viewer').classList.toggle('startup-active',active);
}
window.addEventListener('message',e=>{
 if(e.source!==r7Frame.contentWindow||!e.data||e.data.version!==1)return;
 if(e.data.type==='eva-r7-ready'){
  r7Ready=true;r7Error='';r7ReadyAt=running?elapsed():0;
 }else if(e.data.type==='eva-r7-error'){
  r7Ready=false;r7ReadyAt=null;r7Error='R7工作台未能完成初始化';
 }
});
const probeR7=()=>r7Frame.contentWindow?.postMessage({type:'eva-r7-probe'},'*');
r7Frame.addEventListener('load',probeR7);probeR7();
document.querySelector('#enter-workbench').addEventListener('click',()=>stop({skip:true}));
document.querySelector('#hangar-motion').addEventListener('click',()=>{
 const button=r7Frame.contentDocument?.querySelector('#replay');
 if(button)button.click();
});
window.s4Integration={state:()=>({ready:r7Ready,readyAt:r7ReadyAt,error:r7Error,overlay:startupSurface,frameBlocked:r7Frame.inert,readinessScope:'local R7 prototype'})};

for(const [key,url]of Object.entries(A.videos)){const v=document.createElement('video');v.src=url;v.muted=true;v.playsInline=true;v.preload='auto';v.load();videos[key]=v;}
const imagesReady=Promise.all([opticalTexture.decode(),...Object.values(videos).map(v=>new Promise((ok,no)=>{if(v.readyState>=2)return ok();v.addEventListener('loadeddata',ok,{once:true});v.addEventListener('error',()=>no(new Error('电影素材无法解码')),{once:true})}))]);
function text(s,x,y,size=14,color='#d9b47b',align='left',font='Consolas'){ctx.fillStyle=color;ctx.textAlign=align;ctx.font=`${size}px ${font},"Microsoft YaHei",sans-serif`;ctx.fillText(s,x,y)}
function path(points,fill,stroke,width=1){ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();if(fill){ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width;ctx.stroke()}}
function line(x,y,xx,yy,color,width=1){ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(xx,yy);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke()}
function oval(x,y,rx,ry,fill,stroke,width=1){ctx.beginPath();ctx.ellipse(x,y,rx,ry,0,0,Math.PI*2);if(fill){ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width;ctx.stroke()}}
function radial(x,y,r,inner,outer){const g=ctx.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,inner);g.addColorStop(1,outer);return g}
function gradient(y1,y2,colors){const g=ctx.createLinearGradient(0,y1,0,y2);colors.forEach(([at,c])=>g.addColorStop(at,c));return g}
function vignette(a=.8){ctx.fillStyle=radial(720,380,900,'#00000000',`rgba(0,0,0,${a})`);ctx.fillRect(0,0,W,H)}
function drawWorkbench(){ctx.clearRect(0,0,W,H);}

function opticalBase(t,light=0){
 if(t<T.waveAt)return previousOpticalBase(t,light);
 if(t<T.waveAt+.30){previousOpticalBase(t,light);ctx.save();ctx.globalAlpha=ease((t-T.waveAt)/.30);studyBase(t);ctx.restore();}
 else studyBase(t);
}
function previousOpticalBase(t,light=0){
  // A continuous cylindrical imaging surface.
  ctx.fillStyle=gradient(0,H,[[0,'#29291f'],[.23,'#756743'],[.52,'#595039'],[.8,'#292c2a'],[1,'#0b1118']]);ctx.fillRect(0,0,W,H);
  if(opticalTexture.naturalWidth){ctx.save();ctx.globalAlpha=.13;ctx.drawImage(opticalTexture,0,0,W,H);ctx.restore();}
  ctx.fillStyle=radial(720,310,950,'#ddc88c38','#060d1500');ctx.fillRect(0,0,W,H);
  // Five broad optical regions echo the Unit-01 screen plan at 04:12; the
  // user confirmed this arrangement is shared for the Unit-02 study.
  for(const [x0,y0,c1x,c1y,c2x,c2y,x1,y1] of [
    [605,655,515,455,430,220,390,0],[835,655,925,455,1010,220,1050,0],
    [575,675,390,610,155,430,0,280],[865,675,1050,610,1285,430,1440,280],
    [565,705,390,735,150,800,0,810],[875,705,1050,735,1290,800,1440,810]
  ]){ctx.beginPath();ctx.moveTo(x0,y0);ctx.bezierCurveTo(c1x,c1y,c2x,c2y,x1,y1);ctx.strokeStyle='#151b1b6b';ctx.lineWidth=2;ctx.stroke();}
  for(const y of [-220,490,1170]){ctx.beginPath();ctx.ellipse(720,y,1550,320,0,0,Math.PI*2);ctx.strokeStyle='#10181955';ctx.lineWidth=2;ctx.stroke();}
  ctx.fillStyle=radial(720,360,860,'#151a1800','#030a1244');ctx.fillRect(0,0,W,H);
}

function opticalGrid(t,s){
  const v=videos['system-grid'],u=s.phase==='bridge'?ease((t-T.bridgeAt)/.50):0;
  ctx.save();ctx.globalCompositeOperation='screen';ctx.globalAlpha=.66*(1-u*.7);
  if(u>0){ctx.beginPath();ctx.rect(0,H*u,W,H*(1-u));ctx.clip();}
  if(v.readyState>=2)ctx.drawImage(v,0,0,W,H);ctx.restore();
  if(s.phase==='confirm'){
    text('OPTICAL CALIBRATION COMPLETE',720,154,16,'#cbe7bf','center');
    line(585,173,855,173,'#b3d8a1',1.5);
  }
  if(s.phase==='bridge'){
    ctx.save();ctx.globalCompositeOperation='screen';ctx.globalAlpha=Math.sin(u*Math.PI)*.6;
    line(0,H*u,W,H*u,'#c7e6b7',2);ctx.restore();
    const colors=['#e991ce','#c5e07d','#83cee3'];
    for(let channel=0;channel<3;channel++){
      const k=ease((u-channel*.16)/.42);if(!k)continue;
      const phase=(channel-1)*1.48,y=H*.46+Math.sin((W/2-150)*.0058+(t-T.waveAt)*.78+phase)*H*.205;
      ctx.save();ctx.globalCompositeOperation='screen';ctx.globalAlpha=k*.65*(1-ease((u-.8)/.2));
      oval(720,y,8+k*5,8+k*5,null,colors[channel],1.5);line(720-k*W*.5,y,720+k*W*.5,y,colors[channel],.8);ctx.restore();
    }
    text('CALIBRATION COMPLETE / 3 CHANNELS ARMED',720,154,12,'#d4d8ab','center');
  }
}

function lcl(t){
  const u=clamp((t-T.entry)/T.lcl),surface=H+50-(H+135)*ease(u*.99);
  if(surface>25&&surface<H-25){ctx.save();ctx.globalAlpha=.5;for(let yy=-16;yy<=28;yy+=4){const dx=Math.sin(t*4+yy*.17)*5;ctx.drawImage(canvas,0,surface+yy,W,4,dx,surface+yy+2,W,5)}ctx.restore();}
  ctx.save();ctx.beginPath();ctx.moveTo(0,surface);for(let x=0;x<=W;x+=16)ctx.lineTo(x,surface+Math.sin(x*.008+t*2.8)*8+Math.sin(x*.027-t*3.2)*2);ctx.lineTo(W,H);ctx.lineTo(0,H);ctx.closePath();ctx.clip();
  ctx.fillStyle=gradient(surface,H,[[0,'#ffc35e6a'],[.18,'#e990296e'],[1,'#9f471e99']]);ctx.fillRect(0,0,W,H);
  for(let j=0;j<16;j++){ctx.beginPath();for(let x=0;x<=W;x+=20){const y=surface+30+j*40+Math.sin(x*.007+j*.65+t*.6)*24;x?ctx.lineTo(x,y):ctx.moveTo(x,y)}ctx.strokeStyle='#ffe19a14';ctx.lineWidth=1.2;ctx.stroke()}
  for(let i=0;i<48;i++){const x=(i*173.71+Math.sin(t*1.3+i)*18)%W,y=H-((t*72+i*69.2)%(H+100)),r=2+(i%5)*1.4;if(y<surface)continue;oval(x,y,r,r*1.22,null,'#ffe8ac77',1);oval(x-r*.2,y-r*.4,r*.2,r*.2,'#fff4c777')}
  ctx.restore();
  if(surface>0&&surface<H){ctx.beginPath();for(let x=0;x<=W;x+=10){let y=surface+Math.sin(x*.008+t*2.8)*8+Math.sin(x*.027-t*3.2)*2;x?ctx.lineTo(x,y):ctx.moveTo(x,y)}ctx.strokeStyle='#ffeab7bb';ctx.lineWidth=3;ctx.shadowColor='#ffd698';ctx.shadowBlur=14;ctx.stroke();ctx.shadowBlur=0;}
  text('L.C.L. FILLING',720,158,13,'#f8deb2','center');text(u<.8?'注水中':'光学補正',720,185,18,'#f9deae','center');
}

/* Procedural motion studies. Only stages 05–07 differ from the no-cockpit player. */
const studyParams=new URLSearchParams(location.search);
const study={wave:['a','b','c'].includes(studyParams.get('wave'))?studyParams.get('wave'):'c',hex:['a','b','c'].includes(studyParams.get('hex'))?studyParams.get('hex'):'c'};
const waveOptions={
 a:{label:'A 原片感',cell:9.8,radius:62,amplitude:196,k:.0059,phase:1.12,line:.90,front:.68,back:.16,fill:.30},
 b:{label:'B 清晰重绘',cell:13,radius:52,amplitude:174,k:.0059,phase:1.12,line:1.05,front:.74,back:.08,fill:.13},
 c:{label:'C3 渐进同步',cell:11.5,radius:58,amplitude:186,k:.0059,phase:1.12,line:.95,front:.69,back:.12,fill:.19}
};
const flipOptions={
 a:{label:'A 光学薄片',radius:65,duration:.60,spread:.56,thickness:1.2,hinge:false},
 b:{label:'B 机械铰接',radius:78,duration:.66,spread:.50,thickness:5.5,hinge:true},
 c:{label:'C 精密阵列',radius:46,duration:.50,spread:.66,thickness:2.2,hinge:false}
};
const waveColors=[[215,58,153],[141,196,42],[50,161,208]];

const syncDuration=1.5;

function waitingOffset(t,channel){
 const period=[2.1,2.7,2.35][channel],u=Math.max(0,t-T.waveAt)/period;
 const i=Math.floor(u),f=u-i,w=f*f*f*(f*(f*6-15)+10);
 const target=n=>{const h=Math.sin((n+1)*127.1+(channel+1)*311.7)*43758.5453;return (h-Math.floor(h))*144-72;};
 return mix(target(i),target(i+1),w)*ease((t-T.waveAt)/.8);
}
function channelState(t,c,channel){
 const o=waveOptions[study.wave],tau=t-T.waveAt+(3-syncDuration)*c;
 if(study.wave!=='c')return {k:o.k,amp:o.amplitude,phase:tau*.34+(channel-1)*o.phase*(1-c)-.35,offset:0,bend:0,bendPhase:0,radius:o.radius*(1+c*.08)};
 // One overlapping acquisition envelope keeps intermediate states visible.
 const lock=ease(c),frequencyLock=ease(c/.94),target=Math.PI/2-o.k*W/2;
 const dk=[-.025,.020,.008][channel],da=[-.03,.025,.005][channel];
 const seed=[.2,2.5,4.7][channel],rate=[1.05,.76,.90][channel];
 const drift=.20*Math.sin(tau*rate+seed),common=.12*Math.sin(tau*.38-.8);
 const phase=target+([ -1.12,.16,1.10 ][channel]+drift+common)*(1-lock);
 return {shiftX:waitingOffset(t,channel)*(1-lock),k:o.k*(1+dk*(1-frequencyLock)),amp:o.amplitude*(1+da*(1-lock)),phase,
  offset:[-5,3,2][channel]*(1-lock),bend:[3,-3,2][channel]*(1-frequencyLock),
  bendPhase:tau*[.60,-.40,.85][channel]+seed,
  radius:o.radius*(1+c*.08)*(1+[.01,-.01,0][channel]*(1-lock))};
}
function curveProfile(x,s){
 const angle=x*s.k+s.phase,bendAngle=x*.0027+s.bendPhase;
 const y=H*.49+s.offset-s.amp*Math.sin(angle)+s.bend*Math.sin(bendAngle);
 const slope=-s.amp*s.k*Math.cos(angle)+s.bend*.0027*Math.cos(bendAngle),len=Math.hypot(1,slope);
 return [x+(s.shiftX||0),y,-slope/len,1/len];
}
function waveGeometry(t,c,channel,x,a){
 const s=channelState(t,c,channel),b=curveProfile(x,s),n=Math.cos(a)*s.radius;
 return [b[0]+b[2]*n,b[1]+b[3]*n,Math.sin(a)*s.radius];
}

function studyBase(t){
 ctx.fillStyle='#030507';ctx.fillRect(0,0,W,H);
 if(study.wave==='c'){
  ctx.fillStyle=radial(720,390,800,'#153a422c','#02040700');ctx.fillRect(0,0,W,H);
  ctx.strokeStyle='#568a8315';ctx.lineWidth=.6;ctx.beginPath();
  for(let x=0;x<W;x+=72){ctx.moveTo(x,96);ctx.lineTo(x,H-110)}
  for(let y=110;y<H-100;y+=72){ctx.moveTo(0,y);ctx.lineTo(W,y)}ctx.stroke();
 }
}
function syncHud(t,s){
 const locked=s.releaseAt!==null&&t>=s.releaseAt+syncDuration;
 const gold=study.wave==='a'?'#cd922f':'#c8b878',red=study.wave==='a'?'#b5281b':'#77352c';
 for(const y of [92,704]){line(0,y,W,y,red,.8);line(0,y+4,W,y+4,red,.4)}
 for(let i=0;i<75;i++){
  const x=20+i*19;line(x,46,x,46+(i%5===0?27:13),i%3===0?'#438b3b':i%3===1?'#225777':'#673346',i%5===0?1.3:.7);
  line(x,711,x,718+(i%5===0?5:0),red,.8);
  if(i%5===0)text(((i-35)/5).toFixed(1),x,741,11,red,'center');
 }
 line(167,85,167,757,red,.8);
 for(let i=-5;i<=5;i++){const y=398+i*55;line(154,y,180,y,red,.7);if(i!==0)text((-i).toFixed(1),194,y+4,10,red)}
 text('Monitored Target Subject : EVA-02 Assigned Pilot',720,660,17,gold,'center');
 text(locked?'Neurological Link : Synchronization Established':'Verifying Neurological Linkup · Acquiring Frequency and Phase',720,684,16,gold,'center');
 text('EVA-02 / SYNCHRONIZATION',36,785,10,'#8d937c');
 text(String(Math.floor(s.progress)).padStart(3,'0')+' %',1390,785,16,s.progress===100?'#d6e1c8':'#bc9a56','right');
 if(study.wave==='c'){
  text(locked?'PHASE LOCK / CENTERED CREST':s.phase==='merge'?'PHASE ACQUISITION / GRADUAL ALIGNMENT':'ASYNCHRONOUS / 3 CHANNELS',1401,113,10,'#7eaca5','right');
  for(let i=0;i<3;i++){const col=`rgb(${waveColors[i]})`;line(1170+i*74,134,1216+i*74,134,col,2);}
 }
}
function studyTubes(t,p,converge=0,alpha=1){
 const o=waveOptions[study.wave],c=clamp(converge),birth=ease((t-T.waveAt)/.30);alpha*=birth;
 ctx.save();ctx.globalCompositeOperation='screen';
 // Cross sections follow the normal of one continuously deformed centerline.
 for(let channel=0;channel<3;channel++){
  const col=waveColors[channel].map(v=>Math.round(mix(v,225,ease((c-.65)/.35)))),rgb=col.join(',');
  const visibility=(1-c*.4)*alpha;
  ctx.beginPath();
  for(let side=0;side<2;side++)for(let j=0;j<=190;j++){
   const x=side?W+95-j*(W+190)/190:-95+j*(W+190)/190;
   const pt=waveGeometry(t,c,channel,x,side?Math.PI:0);if(side===0&&j===0)ctx.moveTo(pt[0],pt[1]);else ctx.lineTo(pt[0],pt[1]);
  }ctx.closePath();ctx.fillStyle=`rgba(${rgb},${o.fill*visibility})`;ctx.fill();
  const state=channelState(t,c,channel),rr=o.cell,radius=state.radius,da=Math.sqrt(3)*rr/radius;
  const profile=x=>curveProfile(x,state);
  const columns=[];
  for(let q=-9;q<Math.ceil((W+150)/(rr*1.5));q++){
   const x=q*rr*1.5;columns.push({parity:(q%2+2)%2,profiles:[profile(x+rr),profile(x+rr*.5),profile(x-rr*.5),profile(x-rr)]});
  }
  for(let hemisphere=0;hemisphere<2;hemisphere++){
   const rows=[[],[]];
   for(let parity=0;parity<2;parity++)for(let row=-2;row<Math.ceil(Math.PI/da)+2;row++){
    const a=(row+parity*.5)*da;if(a<0||a>Math.PI)continue;
    const base=a+hemisphere*Math.PI,d=Math.sqrt(3)*rr*.5/radius;
    rows[parity].push([Math.cos(base)*radius,Math.cos(base+d)*radius,Math.cos(base-d)*radius]);
   }
   ctx.strokeStyle=`rgba(${hemisphere?rgb:col.map(v=>Math.round(mix(v,255,.42))).join(',')},${visibility*(hemisphere?o.back:o.front)})`;
   ctx.lineWidth=o.line;
   // Small paths avoid rasterizing one screen-sized path with thousands of edges.
   for(const col of columns){ctx.beginPath();for(const offsets of rows[col.parity]){
    // Each shared edge belongs to one hex; its neighbour supplies the other half.
    const rids=[0,1,1,0];
    for(let k=0;k<4;k++){const b=col.profiles[k],n=offsets[rids[k]],x=b[0]+b[2]*n,y=b[1]+b[3]*n;k?ctx.lineTo(x,y):ctx.moveTo(x,y)}
   }
   ctx.stroke();}
  }
  if(study.wave!=='a'){
   for(const a of [0,Math.PI]){ctx.beginPath();for(let x=-70;x<W+70;x+=5){const pt=waveGeometry(t,c,channel,x,a);x===-70?ctx.moveTo(pt[0],pt[1]):ctx.lineTo(pt[0],pt[1]);}ctx.strokeStyle=`rgba(${rgb},${visibility*.58})`;ctx.lineWidth=1.2;ctx.stroke();}
  }
  if(study.wave==='c'){
   const flow=((t-T.waveAt+(3-syncDuration)*c)*180+channel*330)%(W+300)-150;
   for(let j=0;j<4;j++){const pt=waveGeometry(t,c,channel,flow-j*11,Math.PI*.48);oval(pt[0],pt[1],2.3-j*.4,2.3-j*.4,`rgba(${rgb},${visibility*(1-j*.2)})`);}
  }
 }
 // A brief exposure lift acknowledges the phase lock, without changing geometry.
 if(c>.96){ctx.globalAlpha=alpha*Math.sin(clamp((c-.96)/.04)*Math.PI)*.07;ctx.fillStyle='#c0d9d9';ctx.fillRect(0,98,W,602);}
 ctx.restore();
}

const cells=[],hexDuration=1.18;
const shot=document.createElement('canvas');shot.width=W;shot.height=H;const shotCtx=shot.getContext('2d');let shotAt=-1;
function planCells(){
 cells.length=0;const o=flipOptions[study.hex],R=o.radius,hh=Math.sqrt(3)*R;
 for(let q=-20;q<=20;q++)for(let r=-20;r<=20;r++){
  const x=W/2+q*R*1.5,y=H/2+(r+q/2)*hh;if(x<-R||x>W+R||y<-hh/2||y>H+hh/2)continue;
  cells.push({x,y,q,r,d:Math.max(Math.abs(q),Math.abs(r),Math.abs(-q-r))});
 }
 const max=Math.max(...cells.map(c=>c.d));
 for(const c of cells)c.delay=c.d/max*o.spread;
}
planCells();
function triangle(image,src,dst){
 const [s0,s1,s2]=src,[d0,d1,d2]=dst,den=(s1[0]-s0[0])*(s2[1]-s0[1])-(s2[0]-s0[0])*(s1[1]-s0[1]);
 const a=((d1[0]-d0[0])*(s2[1]-s0[1])-(d2[0]-d0[0])*(s1[1]-s0[1]))/den,c=((s1[0]-s0[0])*(d2[0]-d0[0])-(s2[0]-s0[0])*(d1[0]-d0[0]))/den,b=((d1[1]-d0[1])*(s2[1]-s0[1])-(d2[1]-d0[1])*(s1[1]-s0[1]))/den,d=((s1[0]-s0[0])*(d2[1]-d0[1])-(s2[0]-s0[0])*(d1[1]-d0[1]))/den;
 ctx.save();path(dst);ctx.clip();ctx.transform(a,b,c,d,d0[0]-a*s0[0]-c*s0[1],d0[1]-b*s0[0]-d*s0[1]);ctx.drawImage(image,0,0);ctx.restore();
}
function cellMesh(cell,elapsed){
 const o=flipOptions[study.hex],f=clamp((elapsed-cell.delay)/o.duration),u=f*f*(3-2*f),R=o.radius;
 const radial=Math.atan2(cell.y-H/2,cell.x-W/2),sector=Math.round((radial-Math.PI/6)/(Math.PI/3))*Math.PI/3+Math.PI/6;
 const normal=o.hinge?sector:(study.hex==='c'?(cell.q+cell.r)%2*Math.PI/3:0);
 const nx=Math.cos(normal),ny=Math.sin(normal),yaw=u*Math.PI*.91,co=Math.cos(yaw),si=Math.sin(yaw);
 const hinge=o.hinge?R*Math.sqrt(3)/2:0,offset=study.hex==='c'?Math.sin(f*Math.PI)*-9:0;
 function project(vx,vy,z=0){
  const along=vx*nx+vy*ny-hinge,across=-vx*ny+vy*nx;
  const axis=along*co+z*si+hinge,zz=-along*si+z*co+offset;
  const px=axis*nx-across*ny,py=axis*ny+across*nx,perspective=1100/(1100-zz);
  return [cell.x+px*perspective,cell.y+py*perspective,zz];
 }
 const verts=Array.from({length:6},(_,i)=>[Math.cos(i*Math.PI/3)*(R+.30),Math.sin(i*Math.PI/3)*(R+.30)]);
 return {f,u,co,si,normal,verts,front:verts.map(v=>project(...v)),back:verts.map(v=>project(...v,-o.thickness)),center:project(0,0),project};
}
function studyHex(elapsed){
 drawWorkbench();const o=flipOptions[study.hex];
 // Stationary cells share a single unmodified snapshot; no premature outline seams.
 for(const cell of [...cells].sort((a,b)=>b.d-a.d)){
  const m=cellMesh(cell,elapsed);if(m.f>=1)continue;
  if(m.f===0){ctx.save();path(m.front);ctx.clip();ctx.drawImage(shot,0,0);ctx.restore();continue;}
  const {front,back,verts,co,si}=m,opacity=1-ease((m.f-.72)/.28);
  ctx.save();ctx.globalAlpha=opacity;
  const rim=study.hex==='c'?[158,191,183]:study.hex==='a'?[134,188,210]:[204,178,113];
  const active=Math.sin(m.f*Math.PI);
  // Side walls, two surfaces, and a bevel remain visible through the edge-on pose.
  for(let i=0;i<6;i++){
   const j=(i+1)%6,n=si*(.45+.35*Math.cos(i*Math.PI/3-normalAngle(cell)));
   path([front[i],front[j],back[j],back[i]],`rgba(${rim.map(v=>Math.round(v*(.26+Math.abs(n)*.32))).join(',')},.96)`,null);
  }
  if(co>0.015){
   // The opaque undercoat prevents antialias cracks between UV triangles.
   path(front,'#030507',null);
   for(let i=0;i<6;i++){
    const j=(i+1)%6;
    triangle(shot,[[cell.x,cell.y],[cell.x+verts[i][0],cell.y+verts[i][1]],[cell.x+verts[j][0],cell.y+verts[j][1]]],[m.center,front[i],front[j]]);
   }
   path(front,`rgba(3,9,14,${Math.abs(si)*.44})`,null);
  }else path(back,study.hex==='a'?'#0a1720':study.hex==='b'?'#191b1b':'#0c191a',null);
  const face=co>0?front:back;
  path(face,null,`rgba(${rim.join(',')},${.25+active*.48})`,study.hex==='c'?.75:1.05);
  // The highlight follows the light-facing edges, not all six borders equally.
  for(let i=0;i<3;i++){const j=(i+1)%6;line(...face[i].slice(0,2),...face[j].slice(0,2),`rgba(234,245,234,${active*.55})`,.65);}
  if(o.hinge){
   const nx=Math.cos(m.normal),ny=Math.sin(m.normal),R=o.radius;
   const h1=m.project(nx*R*.866+ny*R*.19,ny*R*.866-nx*R*.19),h2=m.project(nx*R*.866-ny*R*.19,ny*R*.866+nx*R*.19);
   line(...h1.slice(0,2),...h2.slice(0,2),'#ddd3a1',1.6);
  }
  ctx.restore();
 }
}
function normalAngle(cell){return Math.atan2(cell.y-H/2,cell.x-W/2)}
function setStudy(wave,flip){
 if(waveOptions[wave])study.wave=wave;if(flipOptions[flip])study.hex=flip;planCells();shotAt=-1;
 document.querySelector('#wave-study').value=study.wave;document.querySelector('#hex-study').value=study.hex;
 document.querySelector('#study-description').textContent=`05/06：${waveOptions[study.wave].label} · 07：${flipOptions[study.hex].label}`;
}

function smallHUD(t,s){
  if(t>=T.waveAt&&s.phase!=='error'){syncHud(t,s);return;}
  const p=Math.floor(s.progress),done=p===100;
  text('EVA-02',46,59,23,'#eee1bb','left','Arial Narrow');text('ENTRY PLUG / OPTICAL INTERFACE',46,81,10,'#b4ab8b');
  text(s.phase==='error'?'HOST LINK LOST':s.phase==='lcl'?'LCL FILL / OPTICAL STANDBY':s.phase==='grid'?'OPTICAL CALIBRATION':s.phase==='confirm'?'OPTICAL CALIBRATION / COMPLETE':s.phase==='bridge'?'THREE CHANNELS / ARMING':'PILOT VIEW · LCL COMPENSATED',1394,63,11,s.phase==='error'?'#e86c5d':'#c4c4a4','right');
  const x=1210,y=659;ctx.fillStyle='#0b1115b8';ctx.fillRect(x-16,y-26,190,110);line(x-16,y-26,x+174,y-26,done?'#d9d9b5':'#a87051');
  text('SYNCHRONIZATION',x,y-7,10,'#b2a38b');text(String(p).padStart(3,'0'),x,y+37,35,done?'#f5e3b2':'#d8be8d','left','Consolas');text('%',x+75,y+37,15,'#bdab8a');
  for(let i=0;i<25;i++){ctx.fillStyle=i<p/4?'#dfaa63':'#39403c';ctx.fillRect(x+i*6.1,y+53,3.5,7)}
  text(done?'CONNECTION ESTABLISHED':s.phase==='error'?'RETRY / SKIP AVAILABLE':'WAITING FOR HOST',x,y+77,9,done?'#dfd5ad':'#c29c71');
}

function opticalScene(t,s,{display=true,liquid=true,hud=true,shade=true}={}){
  opticalBase(t,s.progress/100);
  if(display&&t>=T.waveAt){const c=s.releaseAt===null?0:clamp((t-s.releaseAt)/syncDuration),a=s.releaseAt===null?1:1-ease((t-s.releaseAt-T.merge)/T.fade);studyTubes(t,s.progress,c,a);}
  
  if(liquid&&s.phase==='lcl')lcl(t);
  if(hud)smallHUD(t,s);
  if(s.phase==='error'){ctx.fillStyle='#2b1112b0';ctx.fillRect(370,300,700,110);text('起動を確認できません',720,345,23,'#f4b5a0','center');text('未收到就绪确认 · 保持未合一 · 可跳过',720,380,14,'#ddc2a2','center')}
  if(shade)vignette(.35);
}

function simulation(t,scenario='normal',override=manualReady){
  let readyAt=scenario==='normal'?(r7Ready?r7ReadyAt:null):scenario==='slow'?(r7Ready?Math.max(18,r7ReadyAt??0):null):null;if(override!==null&&r7Ready)readyAt=override;
  const releaseAt=readyAt===null?null:Math.max(T.minimum,readyAt),events=[[.5,18,'宿主就绪'],[3.5,43,'渲染器就绪'],[7.4,73,'首批内容可见'],[9.5,96,'等待可交互确认']];
  let previous=0,target=0,at=0,name='等待启动';for(const e of events)if(t>=e[0]){previous=target;[at,target,name]=e;}
  if((scenario==='error'||r7Error)&&override===null&&t>=8){target=73;previous=73;name='启动失败，等待恢复';readyAt=null;}
  let progress=mix(previous,target,ease((t-at)/.35));if(releaseAt!==null&&t>=releaseAt){progress=100;name='工作台可交互';}
  const appUsable=readyAt!==null&&t>=readyAt,hexAt=releaseAt===null?null:releaseAt+T.merge+T.fade;
  const phase=hexAt!==null&&t>=hexAt?'hex':releaseAt!==null&&t>=releaseAt?'merge':t<T.entry?'entry':t<T.gridAt?'lcl':t<T.confirmAt?'grid':t<T.bridgeAt?'confirm':t<T.waveAt?'bridge':(scenario==='error'||r7Error)&&override===null?'error':'sync';
  const media=phase==='entry'?{key:'entry-02',at:t}:['grid','confirm','bridge'].includes(phase)?{key:'system-grid',at:Math.min(T.grid-.06,t-T.gridAt),freeze:phase!=='grid'}:null;
  return {phase,progress,name,appUsable,readyAt,releaseAt,hexAt,media,done:hexAt!==null&&t>hexAt+hexDuration+.25};
}
function draw(t,scenario='normal',override=manualReady){
  const s=simulation(t,scenario,override);setStartupSurface(!s.done);lastState={...s,time:t,running,starting};
  if(s.done){drawWorkbench();return s;}
  if(s.phase==='entry'){ctx.fillStyle='#040607';ctx.fillRect(0,0,W,H);const v=videos['entry-02'];if(v.readyState>=2)ctx.drawImage(v,0,0,W,H);text('EVA-02 / ENTRY PLUG',W-36,H-28,12,'#e6c9a6','right');}
  else if(['grid','confirm','bridge'].includes(s.phase)){
    opticalScene(t,s,{display:false,hud:false,shade:false});
    opticalGrid(t,s);smallHUD(t,s);vignette(.35);
  }else if(s.phase==='merge'){
    opticalScene(t,s);
  }else if(s.phase==='hex'){
    if(shotAt!==s.hexAt){opticalScene(s.hexAt,s,{display:false,hud:false});shotCtx.drawImage(canvas,0,0);shotAt=s.hexAt;}
    studyHex(t-s.hexAt);
  }else opticalScene(t,s);
  return s;
}

function stopSounds(){for(const a of [...playing])a.stop();}
function stopVideos(){for(const v of Object.values(videos))v.pause();currentVideo=null;}
function playSound(key,{loop=false,gain=.8,delay=0}={}){const buffer=sounds.get(key);if(!buffer||!audioContext||muted)return;const source=audioContext.createBufferSource(),volume=audioContext.createGain();source.buffer=buffer;source.loop=loop;volume.gain.value=gain;source.connect(volume);volume.connect(audioContext.destination);let ended=false;const track={key,loop,at:audioContext.currentTime+delay,stop(){if(ended)return;ended=true;try{source.stop()}catch{}source.disconnect();volume.disconnect();playing.delete(track)}};source.onended=()=>track.stop();playing.add(track);source.start(track.at);return track;}
async function prepareAudio(){if(!audioContext){audioContext=new(window.AudioContext||window.webkitAudioContext)();audioPrepared=Promise.all(Object.entries(A.sounds).map(async([key,url])=>{const bytes=Uint8Array.from(atob(url.split(',')[1]),c=>c.charCodeAt(0));sounds.set(key,await audioContext.decodeAudioData(bytes.buffer))}));}await Promise.all([audioPrepared,audioContext.resume()]);}
function elapsed(){return audioEpoch!==null&&audioContext?.state==='running'?audioContext.currentTime-audioEpoch:(performance.now()-started)/1000;}
function cue(s){if(s.phase===lastPhase)return;lastPhase=s.phase;cueHistory.push({phase:s.phase,time:elapsed()});
  // Every transition stops only the quiet waiting bed; spoken/film sounds finish naturally.
  for(const a of [...playing])if(a.loop)a.stop();
  if(s.phase==='entry'){playSound('entry-original',{gain:.78});playSound('voice-plug',{gain:.7,delay:.12});}
  if(s.phase==='lcl'){playSound('lcl-water',{gain:.53});playSound('voice-lcl',{gain:.88});}
  if(s.phase==='grid'){playSound('grid-original',{gain:.45});playSound('voice-system',{gain:.88});}
  if(s.phase==='confirm')playSound('system-confirm',{gain:.72});
  if(s.phase==='sync'){playSound('voice-sync',{gain:.88});playSound('wait-loop',{gain:.4,loop:true});}
  if(s.phase==='merge'){playSound('merge-original',{gain:.58});playSound('voice-complete',{gain:.88,delay:syncDuration});}
  if(s.phase==='hex')playSound('hex-open',{gain:.45});
}
function updateVideo(s){if(!s.media){if(currentVideo){videos[currentVideo].pause();currentVideo=null;}return;}
  if(s.media.freeze){stopVideos();const v=videos[s.media.key];if(Math.abs(v.currentTime-s.media.at)>.01)v.currentTime=s.media.at;return;}
  const v=videos[s.media.key];if(currentVideo!==s.media.key){stopVideos();currentVideo=s.media.key;v.currentTime=s.media.at;v.play().catch(()=>{status.textContent='浏览器阻止了视频播放，请重新点击播放。'});}
  if(Math.abs(v.currentTime-s.media.at)>.18)v.currentTime=s.media.at;
  if(s.phase==='merge'&&s.media.at>=T.merge-.05)v.pause();
}
function setStatus(s){const label={entry:'插入栓近景 · 原画幅',lcl:'LCL 注入 · 可控第一视角',grid:'系统起动 · 全屏透明栅格',confirm:'扫描完成 · 确认',bridge:'栅格收束 · 三通道点亮',sync:'三束校准 · 等待就绪',merge:'100% · 同组三束连续合一',hex:'快速淡出后 · 蜂窝逐片翻开',error:'未确认就绪 · 不合一'}[s.phase];const value=`模拟 · ${label} · ${Math.floor(s.progress)}%`+(audioFailed?' · 音频不可用':'');if(status.textContent!==value)status.textContent=value;}
async function start(){const id=++runId;cancelAnimationFrame(raf);stopSounds();stopVideos();running=false;starting=true;status.textContent='正在解码本地影音素材…';
  try{await Promise.all([imagesReady,prepareAudio().catch(()=>{audioFailed=true})]);}catch(e){starting=false;status.textContent=e.message;return;}
  if(id!==runId)return;
  running=true;starting=false;manualReady=null;r7ReadyAt=r7Ready?0:null;lastPhase='';cueHistory.length=0;shotAt=-1;started=performance.now();audioEpoch=audioContext?.state==='running'?audioContext.currentTime:null;document.querySelector('#start-overlay').hidden=true;document.querySelector('#skip').hidden=false;const scenario=document.querySelector('#scenario').value;
  function frame(){if(id!==runId)return;const t=elapsed(),s=simulation(t,scenario);updateVideo(s);draw(t,scenario);cue(s);setStatus(s);document.querySelector('#time').value=t.toFixed(2)+'s';document.querySelector('#scrub').value=t;
    if(s.done){running=false;stopVideos();stopSounds();drawWorkbench();document.querySelector('#skip').hidden=true;status.textContent='预演完成 · 已显露 R7 交互预览，可点击会话与项目。';return;}raf=requestAnimationFrame(frame);}
  frame();
}
function stop({skip=false}={}){++runId;cancelAnimationFrame(raf);running=false;starting=false;stopSounds();stopVideos();if(skip){setStartupSurface(false);drawWorkbench();document.querySelector('#start-overlay').hidden=true;document.querySelector('#skip').hidden=true;status.textContent='已跳过片头。跳过不代表启动成功；已解除片头，本页下层为 R7 交互预览。';}}
async function renderAt(t,scenario='normal',override=null){stop();await imagesReady;const s=simulation(t,scenario,override);if(s.media){const v=videos[s.media.key],at=clamp(s.media.at,0,Math.max(0,v.duration-.05));if(Math.abs(v.currentTime-at)>.001){await new Promise((ok,no)=>{v.addEventListener('seeked',ok,{once:true});v.addEventListener('error',no,{once:true});v.currentTime=at;});}}
  document.querySelector('#start-overlay').hidden=true;draw(t,scenario,override);setStatus(s);return {...s,time:t};
}
document.querySelector('#play').addEventListener('click',start);document.querySelector('#start-overlay').addEventListener('click',start);document.querySelector('#skip').addEventListener('click',()=>stop({skip:true}));document.addEventListener('keydown',e=>{if(e.key==='Escape'&&(running||starting))stop({skip:true})});
document.querySelector('#ready').addEventListener('click',()=>{if(running)manualReady=elapsed();else status.textContent='先选择等待手动就绪并播放，再发送模拟就绪确认。'});
document.querySelector('#mute').addEventListener('change',e=>{muted=e.target.checked;if(muted)stopSounds()});
document.querySelector('#fullscreen').addEventListener('click',()=>document.querySelector('.viewer').requestFullscreen().catch(()=>{}));
let scrubSerial=Promise.resolve();document.querySelector('#scrub').addEventListener('input',e=>{const t=Number(e.target.value);document.querySelector('#time').value=t.toFixed(2)+'s';scrubSerial=scrubSerial.then(()=>renderAt(t));});
window.addEventListener('pagehide',()=>{stop();audioContext?.close()});
window.s4Preview={start,stop,renderAt,simulation,setStudy,studyState:()=>({...study}),waveGeometry,channelState,curveProfile,waitingOffset,cellMesh:(i,t)=>cellMesh(cells[i],t),cues:()=>cueHistory.slice(),ready:()=>{if(running)manualReady=elapsed()},state:()=>({...lastState,running,starting,manualReady}),audioState:()=>({state:audioContext?.state,buffers:sounds.size,active:[...playing].map(a=>({key:a.key,loop:a.loop,age:audioContext.currentTime-a.at}))}),hexPlan:()=>cells.map(c=>({...c,distance:c.d,radius:flipOptions[study.hex].radius,duration:flipOptions[study.hex].duration})),timing:{...T,hexDuration,total:T.minimum+T.merge+T.fade+hexDuration+.25},mediaState:()=>Object.entries(videos).map(([key,v])=>({key,readyState:v.readyState,duration:v.duration,time:v.currentTime,paused:v.paused}))};
imagesReady.then(()=>{if(runId!==0)return;draw(0);status.textContent='素材已就绪 · 点击进入插入栓，播放真实镜头与声音。';}).catch(e=>status.textContent=e.message);

setStudy(study.wave,study.hex);
document.querySelector('#wave-study').addEventListener('change',async e=>{setStudy(e.target.value,study.hex);await renderAt(Number(document.querySelector('#scrub').value)||10.2);});
document.querySelector('#hex-study').addEventListener('change',async e=>{setStudy(study.wave,e.target.value);await renderAt(13.3);});
document.querySelectorAll('[data-moment]').forEach(b=>b.addEventListener('click',()=>renderAt(Number(b.dataset.moment))));
let focusLoop=0,focusStart=0;
document.querySelector('#loop-study').addEventListener('click',()=>{cancelAnimationFrame(focusLoop);stop();focusStart=performance.now();const tick=async()=>{const t=9.42+((performance.now()-focusStart)/1000)%5.15;await renderAt(t);focusLoop=requestAnimationFrame(tick);};tick();});
document.querySelector('#play').addEventListener('click',()=>cancelAnimationFrame(focusLoop),true);
document.querySelector('#start-overlay').addEventListener('click',()=>cancelAnimationFrame(focusLoop),true);
document.querySelector('#scrub').addEventListener('input',()=>cancelAnimationFrame(focusLoop),true);
document.querySelectorAll('[data-moment]').forEach(b=>b.addEventListener('click',()=>cancelAnimationFrame(focusLoop),true));
document.querySelectorAll('#skip,#wave-study,#hex-study').forEach(b=>b.addEventListener(b.tagName==='SELECT'?'change':'click',()=>cancelAnimationFrame(focusLoop),true));
document.addEventListener('keydown',e=>{if(e.key==='Escape')cancelAnimationFrame(focusLoop)},true);
window.addEventListener('pagehide',()=>cancelAnimationFrame(focusLoop));
