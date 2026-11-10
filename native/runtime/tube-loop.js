// A 29-second closed motion path; particles always travel left to right.
const tubeLoopSeconds=29;
function waitingOffset(t,channel){
 const slots=12,u=Math.max(0,t-T.waveAt)*slots/tubeLoopSeconds;
 const i=Math.floor(u),f=u-i,w=f*f*f*(f*(f*6-15)+10);
 const target=n=>{n=((n%slots)+slots)%slots;const h=Math.sin((n+1)*127.1+(channel+1)*311.7)*43758.5453;return (h-Math.floor(h))*96-48;};
 return mix(target(i),target(i+1),w)*ease((t-T.waveAt)/.8);
}
function channelState(t,c,channel){
 const o=waveOptions[study.wave],tau=t-T.waveAt+(3-syncDuration)*c;
 const lock=ease(c),frequencyLock=ease(c/.94),target=Math.PI/2-o.k*W/2;
 const dk=[-.025,.020,.008][channel],da=[-.03,.025,.005][channel];
 const seed=[.2,2.5,4.7][channel],cycle=tau*Math.PI*2/tubeLoopSeconds;
 const drift=.16*Math.sin(cycle*[5,3,4][channel]+seed)+.04*Math.sin(cycle*7+seed*2);
 const common=.12*Math.sin(cycle*2-.8);
 const phase=target+([-1.12,.16,1.10][channel]+drift+common)*(1-lock);
 return {shiftX:waitingOffset(t,channel)*(1-lock),k:o.k*(1+dk*(1-frequencyLock)),amp:o.amplitude*(1+da*(1-lock)),phase,
  offset:[-5,3,2][channel]*(1-lock),bend:[3,-3,2][channel]*(1-frequencyLock),
  bendPhase:cycle*[3,-2,4][channel]+seed,
  radius:o.radius*(1+c*.08)*(1+[.01,-.01,0][channel]*(1-lock))};
}
function tubeFlow(t,c,channel){
 const distance=(t-T.waveAt+(3-syncDuration)*c)*180+channel*330;
 return ((distance%(W+300))+(W+300))%(W+300)-150;
}
