(function(){
'use strict';
var BASE='https://bakerventuresstudio.com/nearvo/quiz/';
var STYLES=window.NV_STYLES,ORDER=window.NV_ORDER;
var S='steady-noticer',T='open-talker',D='side-by-side-doer',R='quiet-recharger',P='warm-sparker';
var Q=[
['After a hard day, what helps you feel close again?',[['Talking through the day, start to finish',T],['A little quiet time alone first, then company',R],['Doing something simple together, like dinner or a walk',D],['Them noticing I am off without me having to say so',S]]],
['When something has gone wrong between you, what do you reach for first?',[['Saying plainly what happened and how I felt',T],['Doing something kind to soften the air',D],['A hug or a held hand before any words',P],['Naming what I think they were feeling too',S]]],
['What makes you feel most noticed?',[['They remember a small detail I mentioned weeks ago',S],['They tell me, in words, what they appreciate',T],['They pull me close for no reason',P],['They give me space and do not take it personally',R]]],
['You have a free Saturday together. What sounds best?',[['A project or an outing, side by side',D],['A slow morning at home with no plans',R],['Something playful, like a silly game or dancing in the kitchen',P],['Something chosen with my tastes in mind',S]]],
['When you are stressed, what would you most like your partner to do?',[['Listen until I have said it all',T],['Take something off my plate',D],['Give me a little room and check in later',R],['Wrap me in a long hug',P]]],
['How do you like to be told you are appreciated?',[['A heartfelt note or a few sincere words',T],['Someone taking care of a chore I dislike',D],['Quietly remembering what I like',S],['Respecting my need to recharge',R]]],
['After a disagreement, what tells you it is really okay again?',[['We have talked it all the way through',T],['We are back to doing things together',D],['They are easy and affectionate again',P],['They did something that shows they understood me',S]]],
['What small thing from your partner could make your day?',[['A midday text showing they are thinking of me',S],['A kind sentence out of nowhere',T],['A playful squeeze as they walk by',P],['A calm evening with no demands',R]]],
['When you are apart for a few days, what do you miss most?',[['Their little habits and attentions',S],['Our usual things together',D],['Having them close, the touch and the laughter',P],['Our easy silences',R]]],
['How do you like to celebrate good news?',[['Telling them everything and hearing their reaction',T],['Planning something fun to mark it',D],['A big hug and a happy dance',P],['A quiet moment, just the two of us',R]]],
['You have twenty minutes together tonight. What do you pick?',[['Catch up properly, one question each',T],['Make something or tidy a corner together',D],['Sit in the same room, each doing our own thing',R],['Ask about something they have been quietly carrying',S]]],
['What does feeling understood look like to you?',[['They can say back what I told them',T],['They show up and help in a practical way',D],['They know my moods without a word',S],['They touch my arm, laugh with me and lighten things',P]]]
];
var $=function(id){return document.getElementById(id)};
var stage=$('stage'),cta=document.querySelector('[data-cta]'),intro=$('intro');
var answers=[],idx=0;
var defaultTitle=document.title;
var metaDesc=document.querySelector('meta[name="description"]');
var defaultDesc=metaDesc?metaDesc.getAttribute('content'):'';
function el(tag,attrs,kids){var e=document.createElement(tag);if(attrs)for(var k in attrs){if(k==='text')e.textContent=attrs[k];else e.setAttribute(k,attrs[k])}(kids||[]).forEach(function(c){e.appendChild(c)});return e}
function clear(n){while(n.firstChild)n.removeChild(n.firstChild)}
function img(name,cls,alt){return el('img',{'class':cls,src:'art/'+name+'.svg',alt:alt||'',width:'800',height:'450'})}
function setMeta(title,desc){document.title=title;if(metaDesc)metaDesc.setAttribute('content',desc);var a=document.querySelector('meta[property="og:title"]'),b=document.querySelector('meta[property="og:description"]');if(a)a.setAttribute('content',title);if(b)b.setAttribute('content',desc)}
function focusHeading(){var h=stage.querySelector('[data-focus]');if(h){h.setAttribute('tabindex','-1');h.focus({preventScroll:true});window.scrollTo(0,0)}}
function renderCta(){
 // CTA flip: set data-cta="on" and data-store-url on the <section data-cta> element in index.html. Nothing else.
 var on=cta.getAttribute('data-cta')==='on',url=cta.getAttribute('data-store-url')||'';
 var off=cta.querySelector('[data-cta-off]'),onBox=cta.querySelector('[data-cta-on]');
 if(on&&/^https:\/\/apps\.apple\.com\//.test(url)){off.hidden=true;onBox.hidden=false;onBox.querySelector('a').setAttribute('href',url)}else{off.hidden=false;onBox.hidden=true}
}
var LOCK='<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true" focusable="false"><rect x="3" y="7" width="10" height="7" rx="2" fill="currentColor"/><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
function start(refocus){
 answers=[];idx=0;if(location.hash)history.replaceState(null,'',location.pathname+location.search);setMeta(defaultTitle,defaultDesc);clear(stage);
 if(intro)intro.hidden=false;
 var trust=el('p',{'class':'trust'});trust.innerHTML=LOCK;trust.appendChild(el('span',{text:'Private by design. No account, no cookies, nothing leaves this page.'}));
 var c=el('div',{'class':'pad begin enter'},[
  el('div',{'class':'row'},[el('button',{'class':'btn big',type:'button',id:'go',text:'Start the quiz'})]),
  el('p',{'class':'once',text:'12 questions, about two minutes.'}),trust]);
 stage.appendChild(c);$('go').addEventListener('click',function(){ask(0)});cta.hidden=false;
 if(refocus){var h=document.querySelector('#intro h1');if(h){h.setAttribute('tabindex','-1');h.setAttribute('data-focus','');h.focus({preventScroll:true});window.scrollTo(0,0)}}
}
function ask(i){
 idx=i;clear(stage);cta.hidden=true;if(intro)intro.hidden=true;
 var q=Q[i],n=Q.length;
 var form=el('form',{'class':'enter',novalidate:''});
 var gp=Math.floor(i/3),band=img('band-'+['evening','bench','lane','morning'][gp],'band','');band.style.objectPosition=Math.round(i/(n-1)*100)+'% 50%';band.setAttribute('width','1200');band.setAttribute('height','270');form.appendChild(band);
 var pad=el('div',{'class':'pad'});form.appendChild(pad);
 pad.appendChild(el('div',{'class':'meta'},[el('span',{text:'Question '+(i+1)+' of '+n}),el('span',{text:Math.round((i+1)/n*100)+'%','aria-hidden':'true'})]));
 var fill=el('i');fill.style.width=(i/n*100)+'%';
 var bar=el('div',{'class':'bar',role:'progressbar','aria-label':'Quiz progress','aria-valuemin':'1','aria-valuemax':String(n),'aria-valuenow':String(i+1),'aria-valuetext':'Question '+(i+1)+' of '+n},[fill]);
 pad.appendChild(bar);
 requestAnimationFrame(function(){requestAnimationFrame(function(){fill.style.width=((i+1)/n*100)+'%'})});
 var fs=el('fieldset');var lg=el('legend',{text:q[0],'data-focus':''});fs.appendChild(lg);
 q[1].forEach(function(o,k){
  var id='q'+i+'o'+k;
  var inp=el('input',{type:'radio',name:'q'+i,id:id,value:o[1]});
  if(answers[i]===o[1])inp.checked=true;
  var w=el('div',{'class':'opt'},[inp,el('label',{'for':id,text:o[0]})]);
  inp.addEventListener('change',function(){answers[i]=o[1];next.disabled=false});
  fs.appendChild(w)});
 pad.appendChild(fs);
 var row=el('div',{'class':'qrow'});
 var back=el('button',{'class':'linkbtn',type:'button',text:i===0?'Cancel':'Back'});
 var next=el('button',{'class':'btn',type:'submit',text:i===n-1?'See my result':'Next'});
 next.disabled=!answers[i];
 back.addEventListener('click',function(){i===0?start(true):ask(i-1)});
 form.addEventListener('submit',function(e){e.preventDefault();if(!answers[i])return;i===n-1?finish():ask(i+1)});
 row.appendChild(next);row.appendChild(back);pad.appendChild(row);stage.appendChild(form);focusHeading();
}
function score(){
 var t={};ORDER.forEach(function(k){t[k]=0});answers.forEach(function(a){if(a)t[a]++});
 return ORDER.slice().sort(function(a,b){return t[b]-t[a]||ORDER.indexOf(a)-ORDER.indexOf(b)});
}
function finish(){var r=score();location.hash='result='+r[0]+(t2(r)?'&also='+r[1]:'')}
function t2(r){return r.length>1&&answers.filter(function(a){return a===r[1]}).length>=3}
function parseHash(){
 var m=/^#result=([a-z-]+)(?:&also=([a-z-]+))?$/.exec(location.hash);
 if(!m||!STYLES[m[1]])return null;
 return {id:m[1],also:(m[2]&&STYLES[m[2]]&&m[2]!==m[1])?m[2]:null};
}
function copy(text,statusEl,okMsg){
 if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(function(){statusEl.textContent=okMsg},function(){statusEl.textContent='Copy this link: '+text})}
 else statusEl.textContent='Copy this link: '+text;
}
function share(url,title,text,statusEl,okMsg){
 if(navigator.share){navigator.share({title:title,text:text,url:url}).catch(function(){})}else copy(url,statusEl,okMsg);
}
function result(r){
 var s=STYLES[r.id];clear(stage);cta.hidden=false;if(intro)intro.hidden=true;
 setMeta(s.name+' | Couples Connection Style Quiz | Nearvo',s.tag+' '+s.desc.split('. ')[0]+'. Take the free couples connection style quiz.');
 var box=el('div',{'class':'enter'});
 box.appendChild(img(s.art,'scene','Paper illustration for '+s.name));
 var pad=el('div',{'class':'pad'});box.appendChild(pad);
 pad.appendChild(el('p',{'class':'kicker',text:'Your connection style'}));
 pad.appendChild(el('h2',{'class':'nameplate',text:s.name,'data-focus':''}));
 pad.appendChild(el('p',{'class':'essence',text:s.tag}));
 pad.appendChild(el('p',{text:s.desc}));
 pad.appendChild(el('div',{'class':'note'},[el('p',{text:s.worth})]));
 if(r.also){var o=STYLES[r.also];var p=el('p',{'class':'also'});p.appendChild(document.createTextNode('Also strong for you: '));p.appendChild(el('a',{href:'#result='+r.also,text:o.name}));p.appendChild(document.createTextNode('.'));pad.appendChild(p)}
 pad.appendChild(el('h3',{text:'Three things to try this week, together'}));
 var ol=el('ol',{'class':'try'});s.tries.forEach(function(t){ol.appendChild(el('li',{text:t}))});pad.appendChild(ol);
 pad.appendChild(el('h3',{text:'A question to ask your partner tonight'}));
 pad.appendChild(el('blockquote',{'class':'quote'},[el('p',{text:s.ask})]));
 var st=el('p',{'class':'status',role:'status','aria-live':'polite'});
 var shareBtn=el('button',{'class':'btn big',type:'button',text:'Share my result'});
 var withBtn=el('button',{'class':'btn alt',type:'button',text:'Take it with your partner'});
 var again=el('button',{'class':'linkbtn',type:'button',text:'Retake the quiz'});
 var myUrl=BASE+'result/'+r.id+'/';
 shareBtn.addEventListener('click',function(){share(myUrl,s.name,'I got '+s.name+' on the Nearvo connection style quiz.',st,'Link copied.')});
 withBtn.addEventListener('click',function(){share(BASE,'Connection style quiz for two','Take this short quiz too, then we can compare what we got.',st,'Quiz link copied. Send it to your partner, then compare results.')});
 again.addEventListener('click',function(){start(true)});
 pad.appendChild(el('div',{'class':'actions'},[shareBtn,withBtn,again]));pad.appendChild(st);
 var more=el('p',{'class':'fun'});more.appendChild(document.createTextNode('More to talk about: '));more.appendChild(el('a',{href:'/nearvo/questions/',text:'25 questions to ask your partner'}));more.appendChild(document.createTextNode('.'));pad.appendChild(more);
 pad.appendChild(el('p',{'class':'fun',text:'Most people are a blend, and styles can shift with seasons of life. Comparing results with your partner is the point: talk about where you match and where you differ.'}));
 stage.appendChild(box);
 var all=el('div',{'class':'enter'});
 all.appendChild(el('h3',{text:'All five connection styles'}));
 var ul=el('ul',{'class':'styles'});
 ORDER.forEach(function(k){var li=el('li');var a=el('a',{href:'#result='+k},[img(STYLES[k].art,'','' ),el('span',{},[el('b',{text:STYLES[k].name}),document.createTextNode(STYLES[k].tag)])]);a.firstChild.setAttribute('loading','lazy');li.appendChild(a);ul.appendChild(li)});
 all.appendChild(ul);stage.appendChild(all);
 focusHeading();
}
function route(){var r=parseHash();if(r)result(r);else start()}
renderCta();
window.addEventListener('hashchange',route);
route();
})();
