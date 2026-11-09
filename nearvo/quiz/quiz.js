(function(){
'use strict';
var BASE='https://bakerventuresstudio.com/nearvo/quiz/';
var STYLES={
'steady-noticer':{name:'The Steady Noticer',tag:'You feel closest when someone has paid attention.',
 desc:'You tend to feel loved through the small, specific things: a remembered detail, a text that shows they were thinking of you, an unspoken “I can tell you’re tired.” You probably notice a lot about your partner too, often more than you say out loud.',
 worth:'Worth knowing: if you wait to be noticed, your partner may not realise what you are hoping for. Saying it once, kindly, can help.',
 tries:['Each day this week, tell your partner one small thing you noticed about them. Keep it specific.','Pick one detail from a past conversation and bring it back with something that nods to it.','Take turns finishing the sentence “A small thing you do that I love is…”.'],
 ask:'What is something small I did recently that you noticed and liked?'},
'open-talker':{name:'The Open Talker',tag:'You feel closest when things are said out loud.',
 desc:'Words are how you connect. Saying how the day went, hearing “I appreciate you”, and talking things through to the end all leave you feeling near to your partner. Silence can feel like distance, even when nothing is wrong.',
 worth:'Worth knowing: a partner who connects in other ways may need a little time before they find their words. Pauses are not always distance.',
 tries:['Set aside ten phone-free minutes after dinner and take turns telling each other about your day without interrupting.','Write your partner a short note, a few honest sentences, and leave it where they will find it.','Say one thing you appreciate about them every evening, out loud.'],
 ask:'Is there something you have wanted to tell me lately but have not found the moment for?'},
'side-by-side-doer':{name:'The Side-by-Side Doer',tag:'You feel closest when you are doing something together.',
 desc:'For you, closeness shows up in action: cooking together, tackling a project, a walk, or a partner who quietly takes something off your plate. Being useful to each other, or simply busy side by side, feels like love.',
 worth:'Worth knowing: help is not the only way your partner may be trying to show care. Look for what sits behind the gesture.',
 tries:['Choose one small project this week, like a recipe, a shelf or a playlist, and do it together from start to finish.','Take over one of your partner’s least favourite chores this week without being asked.','Plan one outing and split the planning: one picks where, the other picks what to bring.'],
 ask:'What is one thing I could take off your plate this week that would make a real difference?'},
'quiet-recharger':{name:'The Quiet Recharger',tag:'You feel closest when there is calm and room to breathe.',
 desc:'You value ease: unhurried time, comfortable silence, and a partner who understands that needing space is not rejection. You often come back warmer after some quiet, and you feel safe when you are not pushed.',
 worth:'Worth knowing: your partner may read your space as distance. A short “I need an hour, then I would love to be with you” goes a long way.',
 tries:['Agree on a simple phrase for “I need a little space, and I will come find you in an hour”, then use it once this week.','Spend twenty minutes in the same room, each doing your own quiet thing, with no screens between you.','Plan a slow, unscheduled morning together with nothing on the list.'],
 ask:'What kind of quiet time helps you feel close to me rather than far from me?'},
'warm-sparker':{name:'The Warm Sparker',tag:'You feel closest through warmth, play and touch.',
 desc:'Affection is your language: hugs, hand-holding, laughing at something silly, a playful nudge in the kitchen. Lightness and physical closeness help you feel connected and help you reset after a rough patch.',
 worth:'Worth knowing: not everyone feels safe to be playful when they are stressed. Match your partner’s mood, then lift it gently.',
 tries:['Start or end each day this week with a proper ten-second hug.','Invent one tiny silly ritual together, like a handshake, a nickname or a kitchen dance.','Hold hands on a walk, and swap who sets the pace.'],
 ask:'What kind of touch or playfulness feels best to you when we are both relaxed?'}
};
var ORDER=['steady-noticer','open-talker','side-by-side-doer','quiet-recharger','warm-sparker'];
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
var stage=$('stage'),cta=document.querySelector('[data-cta]');
var answers=[],idx=0;
var defaultTitle=document.title;
var metaDesc=document.querySelector('meta[name="description"]');
var defaultDesc=metaDesc?metaDesc.getAttribute('content'):'';
function el(tag,attrs,kids){var e=document.createElement(tag);if(attrs)for(var k in attrs){if(k==='text')e.textContent=attrs[k];else e.setAttribute(k,attrs[k])}(kids||[]).forEach(function(c){e.appendChild(c)});return e}
function clear(n){while(n.firstChild)n.removeChild(n.firstChild)}
function setMeta(title,desc){document.title=title;if(metaDesc)metaDesc.setAttribute('content',desc);var a=document.querySelector('meta[property="og:title"]'),b=document.querySelector('meta[property="og:description"]');if(a)a.setAttribute('content',title);if(b)b.setAttribute('content',desc)}
function focusHeading(){var h=stage.querySelector('[data-focus]');if(h){h.setAttribute('tabindex','-1');h.focus({preventScroll:false})}}
function renderCta(){
 // CTA flip: set data-cta="on" and data-store-url on the <section data-cta> element in index.html. Nothing else.
 var on=cta.getAttribute('data-cta')==='on',url=cta.getAttribute('data-store-url')||'';
 var off=cta.querySelector('[data-cta-off]'),onBox=cta.querySelector('[data-cta-on]');
 if(on&&/^https:\/\/apps\.apple\.com\//.test(url)){off.hidden=true;onBox.hidden=false;onBox.querySelector('a').setAttribute('href',url)}else{off.hidden=false;onBox.hidden=true}
}
function start(){
 answers=[];idx=0;location.hash='';setMeta(defaultTitle,defaultDesc);clear(stage);
 var c=el('div',{'class':'card'},[
  el('h2',{text:'Twelve quick questions. About two minutes.','data-focus':''}),
  el('p',{text:'Pick the answer that sounds most like you. There are no right answers, and your answers never leave this page.'}),
  el('div',{'class':'row'},[el('button',{'class':'btn',type:'button',id:'go',text:'Start the quiz'})])]);
 stage.appendChild(c);$('go').addEventListener('click',function(){ask(0)});cta.hidden=false;
}
function ask(i){
 idx=i;clear(stage);cta.hidden=true;
 var q=Q[i],n=Q.length;
 var form=el('form',{'class':'card',novalidate:''});
 form.appendChild(el('p',{'class':'count',text:'Question '+(i+1)+' of '+n}));
 var pr=el('progress',{'class':'prog',max:String(n),value:String(i+1),'aria-label':'Quiz progress'});form.appendChild(pr);
 var fs=el('fieldset');var lg=el('legend',{text:q[0],'data-focus':''});fs.appendChild(lg);
 q[1].forEach(function(o,k){
  var id='q'+i+'o'+k;
  var inp=el('input',{type:'radio',name:'q'+i,id:id,value:o[1]});
  if(answers[i]===o[1])inp.checked=true;
  var w=el('div',{'class':'opt'},[inp,el('label',{'for':id,text:o[0]})]);
  inp.addEventListener('change',function(){answers[i]=o[1];next.disabled=false});
  fs.appendChild(w)});
 form.appendChild(fs);
 var row=el('div',{'class':'row'});
 var back=el('button',{'class':'btn alt',type:'button',text:i===0?'Cancel':'Back'});
 var next=el('button',{'class':'btn',type:'submit',text:i===n-1?'See my result':'Next'});
 next.disabled=!answers[i];
 back.addEventListener('click',function(){i===0?start():ask(i-1)});
 form.addEventListener('submit',function(e){e.preventDefault();if(!answers[i])return;i===n-1?finish():ask(i+1)});
 row.appendChild(back);row.appendChild(next);form.appendChild(row);stage.appendChild(form);focusHeading();
}
function score(){
 var t={};ORDER.forEach(function(k){t[k]=0});answers.forEach(function(a){if(a)t[a]++});
 var ranked=ORDER.slice().sort(function(a,b){return t[b]-t[a]||ORDER.indexOf(a)-ORDER.indexOf(b)});
 return ranked;
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
 var s=STYLES[r.id];clear(stage);cta.hidden=false;
 setMeta(s.name+' – Couples Connection Style Quiz | Nearvo',s.tag+' '+s.desc.split('. ')[0]+'. Take the free couples connection style quiz.');
 var box=el('div');
 box.appendChild(el('p',{'class':'tag',text:'Your connection style'}));
 box.appendChild(el('h2',{text:s.name,'data-focus':''}));
 box.appendChild(el('p',{'class':'lede',text:s.tag}));
 box.appendChild(el('p',{text:s.desc}));
 box.appendChild(el('p',{text:s.worth}));
 if(r.also){var o=STYLES[r.also];var p=el('p');p.appendChild(document.createTextNode('Also strong for you: '));p.appendChild(el('a',{href:'#result='+r.also,text:o.name}));p.appendChild(document.createTextNode('.'));box.appendChild(p)}
 box.appendChild(el('h3',{text:'Three things to try this week, together'}));
 var ol=el('ol',{'class':'try'});s.tries.forEach(function(t){ol.appendChild(el('li',{text:t}))});box.appendChild(ol);
 box.appendChild(el('h3',{text:'A question to ask your partner tonight'}));
 box.appendChild(el('p',{'class':'tonight',text:s.ask}));
 var st=el('p',{'class':'status',role:'status','aria-live':'polite'});
 var shareBtn=el('button',{'class':'btn',type:'button',text:'Share my result'});
 var withBtn=el('button',{'class':'btn alt',type:'button',text:'Take it with your partner'});
 var again=el('button',{'class':'btn alt',type:'button',text:'Retake the quiz'});
 var myUrl=BASE+'#result='+r.id;
 shareBtn.addEventListener('click',function(){share(myUrl,s.name,'I got '+s.name+' on the Nearvo connection style quiz.',st,'Link copied.')});
 withBtn.addEventListener('click',function(){share(BASE,'Connection style quiz for two','Take this short quiz too, then we can compare what we got.',st,'Quiz link copied. Send it to your partner, then compare results.')});
 again.addEventListener('click',start);
 box.appendChild(el('div',{'class':'row'},[shareBtn,withBtn,again]));box.appendChild(st);
 box.appendChild(el('h3',{text:'All five connection styles'}));
 var ul=el('ul',{'class':'styles'});
 ORDER.forEach(function(k){var li=el('li');li.appendChild(el('a',{href:'#result='+k,text:STYLES[k].name}));li.appendChild(document.createTextNode(' – '+STYLES[k].tag));ul.appendChild(li)});
 box.appendChild(ul);
 box.appendChild(el('p',{'class':'fun',text:'Most people are a blend, and styles can shift with seasons of life. Comparing results with your partner is the point: talk about where you match and where you differ.'}));
 stage.appendChild(box);focusHeading();
}
function route(){var r=parseHash();if(r)result(r);else start()}
renderCta();
window.addEventListener('hashchange',function(){var r=parseHash();if(r)result(r);else start()});
route();
})();
