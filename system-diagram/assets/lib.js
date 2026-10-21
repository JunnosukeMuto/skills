// 構成図の描画部品。図ごとの本体 JS からこれらの関数を呼んで、座標を指定して描く。
const NS='http://www.w3.org/2000/svg';
const svg=document.querySelector('svg');
function el(t,a,parent=svg){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);parent.appendChild(e);return e}
// 複数行テキスト。lines は文字列か文字列の配列
function txt(x,y,lines,cls,anchor='middle',lh=18){const t=el('text',{x,y,class:cls,'text-anchor':anchor});(Array.isArray(lines)?lines:[lines]).forEach((l,i)=>{const s=el('tspan',{x,dy:i?lh:0},t);s.textContent=l});return t}
// システムの枠。titlePos='bottom' にすると見出しを枠の下端に置き、上側を矢印の通り道に空けられる
function panel(x,y,w,h,title,sub,titlePos='top'){el('rect',{x,y,width:w,height:h,rx:16,class:'panel'});
 const ty=titlePos==='bottom'?y+h-40:y+34;txt(x+22,ty,title,'ptitle','start');if(sub)txt(x+22,ty+22,sub,'psub','start')}
// 箱。cls は ''/'new'/'warn'/'ext'。badge は {t:'新設', c:'#12b76a'} の形（文字列を渡すと描画が止まる）
function box(x,y,w,h,title,subs=[],cls='',badge){el('rect',{x,y,width:w,height:h,rx:10,class:'box '+cls});const n=subs.length;const top=y+h/2-(n*18)/2+6;txt(x+w/2,top,title,'bt');if(n)txt(x+w/2,top+24,subs,'bs','middle',18);
 if(badge){const bw=badge.t.length*13+16;el('rect',{x:x+w-bw-8,y:y-11,width:bw,height:22,rx:11,fill:badge.c});const b=txt(x+w-bw/2-8,y+4.5,badge.t,'badge');b.setAttribute('fill','#fff')}}
// DB の円柱
function db(x,y,w,h,title,subs=[]){const ry=14;el('path',{d:`M${x},${y+ry} A${w/2},${ry} 0 0 1 ${x+w},${y+ry} V${y+h-ry} A${w/2},${ry} 0 0 1 ${x},${y+h-ry} Z`,class:'db'});el('path',{d:`M${x},${y+ry} A${w/2},${ry} 0 0 0 ${x+w},${y+ry}`,class:'db',fill:'none'});txt(x+w/2,y+h/2+8,title,'bt');if(subs.length)txt(x+w/2,y+h/2+30,subs,'bs')}
function marker(cls){return cls.includes('cross')?'mr':cls.includes('good')?'mg':'m'}
// 矢印。d は SVG パス（縦横の線だけで書く: 'M x,y V y2 H x2'）。cls は ''/'cross'/'good' に 'dash' を足せる
function arrow(d,cls=''){return el('path',{d,class:'a '+cls,'marker-end':`url(#${marker(cls)})`})}
// 両方向の矢印
function arrow2(d,cls=''){const m=marker(cls);return el('path',{d,class:'a '+cls,'marker-end':`url(#${m})`,'marker-start':`url(#${m})`})}
// 矢印の先端なしの線（複数の線を合流させるとき）
function line(d,cls=''){return el('path',{d,class:'a '+cls})}
// 線に添えるラベル。cls は ''/'cross'/'good'
function lbl(x,y,lines,cls='',anchor='middle'){txt(x,y,lines,'lbl '+cls,anchor,17)}
// 凡例。kind は 'line'/'line:good'/'line:cross'/'line:dash' か、箱の cls（'new'/'warn'/'ext'）
function legendItem(x,y,kind,label){if(kind.startsWith('line')){const c=kind.split(':')[1]||'';el('path',{d:`M${x},${y} H${x+44}`,class:'a '+c,'marker-end':`url(#${marker(c)})`})}else{el('rect',{x,y:y-11,width:44,height:22,rx:6,class:'box '+kind})}txt(x+56,y+5,label,'legend','start')}
