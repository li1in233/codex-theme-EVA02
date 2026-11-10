// One immutable texture and one mesh submission replace hundreds of Canvas clips per frame.
function createHexPlayer(){
  const surface=document.createElement('canvas');surface.id='hex-surface';
  surface.style.cssText='position:absolute;inset:0;width:100%;height:100%;pointer-events:none;visibility:hidden';root.append(surface);
  const gl=surface.getContext('webgl',{alpha:true,premultipliedAlpha:false,antialias:true,depth:false,stencil:false});
  if(!gl){surface.remove();return null;}
  let lost=false,disposed=false;
  surface.addEventListener('webglcontextlost',e=>{e.preventDefault();if(disposed)return;lost=true;surface.style.visibility='hidden';result.hexFailure='context-lost';});
  function shader(type,source){const value=gl.createShader(type);gl.shaderSource(value,source);gl.compileShader(value);if(!gl.getShaderParameter(value,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(value));return value;}
  const vertex=shader(gl.VERTEX_SHADER,`attribute vec2 position;attribute vec2 uv;attribute vec4 color;attribute float textured;varying vec2 vUv;varying vec4 vColor;varying float vTextured;void main(){gl_Position=vec4(position.x/720.-1.,1.-position.y/405.,0.,1.);vUv=uv;vColor=color;vTextured=textured;}`);
  const fragment=shader(gl.FRAGMENT_SHADER,`precision mediump float;uniform sampler2D image;varying vec2 vUv;varying vec4 vColor;varying float vTextured;void main(){vec4 pixel=vTextured>.5?texture2D(image,vUv):vec4(1.);gl_FragColor=pixel*vColor;}`);
  const program=gl.createProgram();gl.attachShader(program,vertex);gl.attachShader(program,fragment);gl.linkProgram(program);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
  gl.deleteShader(vertex);gl.deleteShader(fragment);gl.useProgram(program);
  const buffer=gl.createBuffer(),texture=gl.createTexture();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
  for(const [name,size,offset]of [['position',2,0],['uv',2,2],['color',4,4],['textured',1,8]]){const at=gl.getAttribLocation(program,name);gl.enableVertexAttribArray(at);gl.vertexAttribPointer(at,size,gl.FLOAT,false,36,offset*4);}
  gl.bindTexture(gl.TEXTURE_2D,texture);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
  gl.uniform1i(gl.getUniformLocation(program,'image'),0);gl.enable(gl.BLEND);gl.blendFuncSeparate(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA,gl.ONE,gl.ONE_MINUS_SRC_ALPHA);gl.clearColor(0,0,0,0);
  const data=new Float32Array(cells.length*180*9);let cursor=0,ordered=[...cells].sort((a,b)=>b.d-a.d);
  function point(p,uv,col,textured){data.set([p[0],p[1],uv[0]/W,uv[1]/H,col[0]/255,col[1]/255,col[2]/255,col[3],textured],cursor);cursor+=9;}
  function polygon(points,col,source=null){for(let i=1;i<points.length-1;i++)for(const j of [0,i,i+1])point(points[j],source?source[j]:[0,0],col,source?1:0);}
  function edge(a,b,col,width){const dx=b[0]-a[0],dy=b[1]-a[1],d=Math.hypot(dx,dy)||1,x=-dy/d*width/2,y=dx/d*width/2;polygon([[a[0]+x,a[1]+y],[b[0]+x,b[1]+y],[b[0]-x,b[1]-y],[a[0]-x,a[1]-y]],col);}
  function resize(){const ratio=Math.min(1,1920/canvas.width,1080/canvas.height);surface.width=Math.round(canvas.width*ratio);surface.height=Math.round(canvas.height*ratio);gl.viewport(0,0,surface.width,surface.height);}
  function upload(){gl.bindTexture(gl.TEXTURE_2D,texture);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,shot);}
  function draw(elapsed){
    if(lost)return false;cursor=0;const o=flipOptions[study.hex];
    for(const cell of ordered){
      const m=cellMesh(cell,elapsed);if(m.f>=1)continue;
      const source=m.verts.map(v=>[cell.x+v[0],cell.y+v[1]]);
      if(m.f===0){polygon(m.front,[255,255,255,1],source);continue;}
      const {front,back,co,si,normal}=m,opacity=1-ease((m.f-.72)/.28),rim=study.hex==='c'?[158,191,183]:study.hex==='a'?[134,188,210]:[204,178,113],active=Math.sin(m.f*Math.PI);
      for(let i=0;i<6;i++){const j=(i+1)%6,n=si*(.45+.35*Math.cos(i*Math.PI/3-normalAngle(cell)));polygon([front[i],front[j],back[j],back[i]],[...rim.map(v=>Math.round(v*(.26+Math.abs(n)*.32))),.96*opacity]);}
      if(co>.015){polygon(front,[3,5,7,opacity]);for(let i=0;i<6;i++)for(const j of [-1,i,(i+1)%6])point(j<0?m.center:front[j],j<0?[cell.x,cell.y]:source[j],[255,255,255,opacity],1);polygon(front,[3,9,14,Math.abs(si)*.44*opacity]);}
      else polygon(back,study.hex==='a'?[10,23,32,opacity]:study.hex==='b'?[25,27,27,opacity]:[12,25,26,opacity]);
      const face=co>0?front:back;
      for(let i=0;i<6;i++)edge(face[i],face[(i+1)%6],[...rim,(.25+active*.48)*opacity],study.hex==='c'?.75:1.05);
      for(let i=0;i<3;i++)edge(face[i],face[(i+1)%6],[234,245,234,active*.55*opacity],.65);
      if(o.hinge){const nx=Math.cos(normal),ny=Math.sin(normal),r=o.radius;edge(m.project(nx*r*.866+ny*r*.19,ny*r*.866-nx*r*.19),m.project(nx*r*.866-ny*r*.19,ny*r*.866+nx*r*.19),[221,211,161,opacity],1.6);}
    }
    if(cursor>data.length)throw Error('Hex mesh exceeds bounded buffer');
    gl.clear(gl.COLOR_BUFFER_BIT);gl.bufferData(gl.ARRAY_BUFFER,data.subarray(0,cursor),gl.STREAM_DRAW);gl.drawArrays(gl.TRIANGLES,0,cursor/9);
    surface.style.visibility='visible';return true;
  }
  resize();upload();draw(0);surface.style.visibility='hidden';gl.finish();
  return {draw,resize,dispose(){disposed=true;gl.deleteTexture(texture);gl.deleteBuffer(buffer);gl.deleteProgram(program);gl.getExtension('WEBGL_lose_context')?.loseContext();surface.remove();}};
}
