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
   ctx.beginPath();
   for(const col of columns)for(const offsets of rows[col.parity]){
    // Each shared edge belongs to one hex; its neighbour supplies the other half.
    const rids=[0,1,1,0];
    for(let k=0;k<4;k++){const b=col.profiles[k],n=offsets[rids[k]],x=b[0]+b[2]*n,y=b[1]+b[3]*n;k?ctx.lineTo(x,y):ctx.moveTo(x,y)}
   }
   ctx.strokeStyle=`rgba(${hemisphere?rgb:col.map(v=>Math.round(mix(v,255,.42))).join(',')},${visibility*(hemisphere?o.back:o.front)})`;
   ctx.lineWidth=o.line;ctx.stroke();
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
