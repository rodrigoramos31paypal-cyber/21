(function(){
'use strict';
const $=id=>document.getElementById(id),F=window.FocoFood,R=window.FOCO_RECIPES;
const allergyNames={leite:'Leite / lactose',gluten:'Glúten',ovos:'Ovos',amendoim:'Amendoim','frutos-casca':'Frutos de casca rija',soja:'Soja',sesamo:'Sésamo',aipo:'Aipo',peixe:'Peixe',crustaceos:'Crustáceos',moluscos:'Moluscos',mostarda:'Mostarda',tremoco:'Tremoço',sulfitos:'Sulfitos'};
const goals={perder:'Perder gordura',manter:'Manutenção',ganhar:'Ganhar massa muscular'};
let ctx,profile,tab='today',week=0,step=1,session=null,online=false,dirty=false,syncTimer,returnFocus,syncChain=Promise.resolve();
const E=s=>ctx.encode(s),byId=id=>R.find(r=>r.id===id);
const safeLink=url=>{try{const u=new URL(url,location.href);return ['https:','http:'].includes(u.protocol)?E(u.href):''}catch(e){return ''}};
async function request(path,method='GET',body){
 const response=await fetch('/api/'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
 if(!response.headers.get('content-type')?.includes('application/json'))throw Error('O serviço de contas não está disponível neste alojamento. O perfil continua guardado neste navegador.');
 const data=await response.json();if(!response.ok)throw Error(data.error||'Não foi possível guardar.');return data;
}
function note(){const el=$('syncStatus');if(el)el.textContent=session?(dirty?'Guardado aqui · sincronização pendente':'Guardado na tua conta'):'Guardado neste navegador';}
function persist(){dirty=Boolean(session);ctx.state.syncPending=dirty;ctx.save();note();clearTimeout(syncTimer);if(session)syncTimer=setTimeout(()=>sync().catch(()=>{}),400);}
function payload(){const s=ctx.state;return {profile:s.profileV4,plan:s.foodPlan,mealChecks:s.mealChecks||{},shoppingChecks:s.shoppingChecks||{},checks:s.checks,day:s.day,track:s.track,name:s.name};}
function sync(){
 if(!session||!ctx.state.profileV4)return Promise.resolve();
 const user=session.id;
 syncChain=syncChain.catch(()=>{}).then(async()=>{
 if(session?.id!==user)return;
 const snapshot=JSON.stringify(payload());dirty=true;ctx.state.syncPending=true;ctx.save();note();
 try{await request('state','PUT',JSON.parse(snapshot));dirty=JSON.stringify(payload())!==snapshot;ctx.state.syncPending=dirty;ctx.save();note();}
 catch(e){dirty=true;ctx.state.syncPending=true;ctx.save();note();throw e;}
 });return syncChain;
}
function open(id){returnFocus=document.activeElement;$(id).classList.remove('hidden');document.body.classList.add('dialog-open');setTimeout(()=>$(id).querySelector('button,input,select')?.focus(),0);}
function close(id){$(id).classList.add('hidden');if(!document.querySelector('.modalback:not(.hidden)'))document.body.classList.remove('dialog-open');returnFocus?.focus();}
function setStep(n){step=n;document.querySelectorAll('[data-profile-step]').forEach(el=>{el.hidden=Number(el.dataset.profileStep)!==n;el.disabled=el.hidden});$('profileStepLabel').textContent=`PASSO ${n} DE 3`;$('profileTitle').textContent=['O teu ponto de partida','O treino na tua rotina','O que gostas de comer'][n-1];$('profileBack').hidden=n===1;$('profileNext').hidden=n===3;$('profileSave').hidden=n!==3;document.querySelectorAll('.step-bars i').forEach((el,i)=>el.classList.toggle('filled',i<n));$('profileError').textContent='';}
function openProfile(){
 const p=ctx.state.profileV4||{name:ctx.state.name||'',goal:ctx.state.goal||'manter',place:ctx.state.track==='casa'?'casa':'ginasio',diet:'todos',meals:Object.keys(F.meals),allergies:ctx.state.restrictions||[]};
 const map={Name:'name',Age:'age',Height:'height',Weight:'weight',Goal:'goal',Place:'place',Experience:'experience',Availability:'availability',Diet:'diet',Other:'otherRestrictions'};
 for(const [suffix,key] of Object.entries(map))$('profile'+suffix).value=p[key]??({experience:'iniciante',availability:3}[key]||'');
 $('allergyChoices').innerHTML=Object.entries(allergyNames).map(([id,label])=>`<label class="choice"><input type="checkbox" name="allergies" value="${id}" ${(p.allergies||[]).includes(id)?'checked':''}>${label}</label>`).join('');
 $('mealChoices').innerHTML=Object.entries(F.meals).map(([id,label])=>`<label class="choice"><input type="checkbox" name="meals" value="${id}" ${(p.meals||[]).includes(id)?'checked':''}>${label}</label>`).join('');
 $('profileStorageNotice').textContent=session?'O perfil será guardado na tua conta.':'Sem sessão, o perfil fica apenas neste navegador. Entra na tua conta para sincronizar.';
 setStep(1);open('onboardModal');
}
function validStep(){const inputs=document.querySelector(`[data-profile-step="${step}"]`).querySelectorAll('input,select');for(const input of inputs)if(!input.reportValidity())return false;return true;}
function saveProfile(e){
 e.preventDefault();if(!validStep())return;
 const data=new FormData($('profileForm')); // Campos dos passos anteriores são lidos diretamente (fieldset desativado para validação).
 const val=s=>$('profile'+s).value.trim(),num=s=>val(s)===''?null:Number(val(s));
 const p={name:val('Name'),age:num('Age'),height:num('Height'),weight:num('Weight'),goal:val('Goal'),place:val('Place'),experience:val('Experience'),availability:Number(val('Availability')),diet:val('Diet'),otherRestrictions:val('Other'),allergies:data.getAll('allergies'),meals:data.getAll('meals')};
 if(!p.meals.length){$('profileError').textContent='Escolhe pelo menos uma refeição.';return;}
 const changed=JSON.stringify([profile?.diet,profile?.allergies,profile?.meals,profile?.goal,profile?.otherRestrictions])!==JSON.stringify([p.diet,p.allergies,p.meals,p.goal,p.otherRestrictions]);
 if(changed&&ctx.state.foodPlan&&!confirm('Atualizar as preferências reorganiza as refeições dos 21 dias e limpa as marcações alimentares. O progresso de treino mantém-se. Continuar?'))return;
 profile=p;const s=ctx.state;s.profileV4=p;s.name=p.name;s.goal=p.goal;s.profileDone=true;s.calories=null;
 if(p.place==='casa')s.track='casa';else if(s.track==='casa')s.track='geral';
 if(changed||!s.foodPlan){s.foodPlan=F.createPlan(R,p);s.mealChecks={};s.shoppingChecks={};}
 persist();close('onboardModal');ctx.screen('alimentacao');ctx.flash(session?'Perfil guardado. A sincronizar a conta.':'Perfil guardado neste navegador.');
}
function ensurePlan(){if(!ctx.state.foodPlan||ctx.state.foodPlan.length!==21){ctx.state.foodPlan=F.createPlan(R,profile);persist();}}
function empty(){return `<div class="empty-state"><h3>Vamos preparar as tuas refeições</h3><p>Escolhe as tuas preferências para organizar os 21 dias.</p><button class="btn lime" data-edit-profile>Preencher o meu perfil</button></div>`;}
function photo(r){return `<img src="${E(r.image)}" alt="${E(r.name)} — imagem do e-book" loading="lazy" width="640" height="420">`;}
function recipeCard(r,day,meal){
 if(!r)return `<article class="card meal-card unavailable"><div class="pad"><span class="eyebrow">${F.meals[meal]}</span><h3>Sem sugestão compatível</h3><p>A seleção atual ainda não tem uma receita para estas preferências. Não substituímos ingredientes automaticamente.</p><button class="btn light" data-edit-profile>Rever preferências</button></div></article>`;
 const checked=Boolean(ctx.state.mealChecks?.[`${day}:${meal}:${r.id}`]);
 return `<article class="card meal-card">${photo(r)}<div class="pad"><div class="row"><span class="eyebrow">${F.meals[meal]}</span><span class="tiny">Vol. ${r.volume}</span></div><h3>${E(r.name)}</h3><p>${E(r.description)}</p><div class="macro-line">≈ ${r.nutrition.kcal} kcal · ${r.nutrition.protein} g proteína <small>${E(r.nutrition.portion)} · indicativo</small></div><div class="meal-actions"><button class="btn" data-recipe="${r.id}">Ver receita</button>${r.video?`<a class="btn light" href="${safeLink(r.video)}" target="_blank" rel="noopener">Ver vídeo</a>`:'<button class="btn light" disabled title="Ainda não foi ligado um vídeo a esta receita">Vídeo por adicionar</button>'}<button class="text-button" data-swap="${day}:${meal}">Trocar receita ↔</button></div><label class="task"><input type="checkbox" data-meal-check="${day}:${meal}:${r.id}" ${checked?'checked':''}>Cumpri esta refeição</label></div></article>`;
}
function weekButtons(){return `<div class="week-selector" aria-label="Semana alimentar">${[0,1,2].map(w=>`<button class="btn ${w===week?'':'light'}" data-week="${w}" aria-pressed="${w===week}">Semana ${w+1}<small>Dias ${w*7+1}–${w*7+7}</small></button>`).join('')}</div>`;}
function renderFood(){
 profile=ctx.state.profileV4;$('foodGoal').textContent=profile?goals[profile.goal]:'';$('foodRestrictions').textContent=profile?[profile.diet==='todos'?'Sem preferência alimentar':profile.diet,...profile.allergies.map(a=>allergyNames[a]||a),profile.otherRestrictions].filter(Boolean).join(' · '):'';note();
 document.querySelectorAll('[data-food-tab]').forEach(b=>{const selected=b.dataset.foodTab===tab;b.setAttribute('aria-selected',selected);b.tabIndex=selected?0:-1;});
 if(!profile){$('foodBody').innerHTML=empty();bindFood();return;}
 ensurePlan();const s=ctx.state;
 const warning=profile.otherRestrictions?'<div class="notice">Tens outras restrições por rever. As sugestões automáticas ficam suspensas até serem verificadas. Podes consultar as receitas e os ingredientes na biblioteca.</div>':'';
 if(tab==='today'){
 const day=Math.max(1,Math.min(21,s.day));
 $('foodBody').innerHTML=warning+`<div class="row food-day"><div><span class="eyebrow">SEMANA ${Math.ceil(day/7)}</span><h3>Dia ${day} de 21</h3></div><div class="gap12"><button class="round" data-food-day="${day-1}" ${day===1?'disabled':''} aria-label="Dia alimentar anterior">‹</button><button class="round" data-food-day="${day+1}" ${day===21?'disabled':''} aria-label="Dia alimentar seguinte">›</button></div></div><div class="meal-grid">${profile.meals.map(m=>recipeCard(byId(s.foodPlan[day-1][m]),day,m)).join('')}</div>`;
 }else if(tab==='week'){
 $('foodBody').innerHTML=warning+weekButtons()+`<p class="tiny">Segunda-feira a domingo representam os sete dias de cada semana do desafio.</p><div class="week-grid">${Array.from({length:7},(_,i)=>{const day=week*7+i+1;return `<article class="card week-day"><div class="row"><h3>${['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo'][i]}</h3><span class="tiny">Dia ${day}</span></div>${profile.meals.map(m=>{const r=byId(s.foodPlan[day-1][m]);return `<div class="week-meal"><span>${F.meals[m]}</span>${r?`<button class="recipe-link" data-recipe="${r.id}">${E(r.name)}</button>`:'<p>Sem sugestão compatível</p>'}<button class="text-button" data-swap="${day}:${m}">Trocar</button></div>`;}).join('')}<button class="btn light full" data-repeat-day="${day}" ${day===21?'disabled':''}>Repetir no dia seguinte</button></article>`;}).join('')}</div><div class="row repeat-week"><p>Gostaste desta semana?</p><button class="btn light" data-repeat-week>Repetir noutra semana</button></div><div id="repeatWeekOptions"></div>`;
 }else if(tab==='library'){
 $('foodBody').innerHTML=`<div class="library-intro"><h3>Da cozinha do João Pedro</h3><p>Uma seleção de 10 receitas dos Volumes 1 e 2. Simples de repetir, fácil de manter.</p></div><div class="library-filters"><label>Refeição<select id="libraryMeal"><option value="">Todas</option>${Object.entries(F.meals).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><label>Preferência<select id="libraryDiet"><option value="todos">Todas</option><option value="vegetariano">Vegetariana</option><option value="vegan">Vegan</option></select></label><label class="choice"><input type="checkbox" id="libraryCompatible">Aplicar as minhas restrições</label></div><div class="meal-grid" id="libraryResults"></div>`;
 renderLibrary();$('libraryMeal').onchange=renderLibrary;$('libraryDiet').onchange=renderLibrary;$('libraryCompatible').onchange=renderLibrary;
 }else renderShopping();
 bindFood();
}
function renderLibrary(){const meal=$('libraryMeal').value,diet=$('libraryDiet').value,apply=$('libraryCompatible').checked;
 const p=apply?{...profile,diet:diet==='todos'?profile.diet:diet}:{diet,allergies:[]};
 const list=R.filter(r=>F.compatible(r,p,meal));
 $('libraryResults').innerHTML=list.length?list.map(r=>`<article class="card library-card">${photo(r)}<div class="pad"><span class="eyebrow">VOL. ${r.volume} · ${F.meals[r.meals[0]]}</span><h3>${E(r.name)}</h3><p>${E(r.description)}</p><button class="btn light full" data-recipe="${r.id}">Ver receita →</button></div></article>`).join(''):'<div class="empty-state">Não há receitas nesta seleção que cumpram todos os filtros.</div>';bindRecipes();
}
function renderShopping(){const items=F.shopping(R,ctx.state.foodPlan,week),s=ctx.state;
 $('foodBody').innerHTML=weekButtons()+`<div class="row food-day"><div><h3>O que precisas esta semana</h3><p class="tiny">Soma das doses das receitas escolhidas. Confirma o que já tens em casa.</p></div><button class="btn light" id="downloadShopping">Descarregar lista</button></div><div class="card pad shopping-list">${items.map((i,index)=>{const key=JSON.stringify([week,i.name,i.qty,i.maximum,i.count]);return `<label class="shopping-item"><input type="checkbox" data-shopping="${E(key)}" ${s.shoppingChecks?.[key]?'checked':''}><span><b>${E(i.name)}</b><small>${E(i.note||'')}</small></span><em>${E(F.quantity(i))}</em></label>`;}).join('')||'<p>Escolhe refeições compatíveis para gerar a lista.</p>'}</div><p class="tiny">Quantidades em cru ou cozinhado conforme o original. Ingredientes sem quantidade no e-book ficam assinalados; não são estimados.</p><a class="text-button" href="assets/checklist_compras.pdf" target="_blank" rel="noopener">Abrir também a checklist original em PDF →</a>`;
 $('downloadShopping').onclick=()=>{const text=`21 Dias de Foco — Semana ${week+1}\n\n`+items.map(i=>`${i.name}: ${F.quantity(i)}${i.note?' ('+i.note+')':''}`).join('\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));a.download=`compras-semana-${week+1}.txt`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
}
function showRecipe(id){const r=byId(id);if(!r)return;$('recipeDetail').innerHTML=`${photo(r)}<div class="eyebrow">JOÃO PEDRO MENDES · VOL. ${r.volume} · PÁGINA ${r.page}</div><h2 id="recipeTitle">${E(r.name)}</h2><p>${E(r.description)}</p><div class="recipe-macros"><b>≈ ${r.nutrition.kcal} kcal</b><span>${r.nutrition.protein} g proteína</span><span>${r.nutrition.carbs} g hidratos</span><span>${r.nutrition.fat} g gordura</span></div><p class="tiny">${E(r.nutrition.portion)} · Valores indicativos do e-book, sem validação independente.</p><p class="notice">Atenção a: ${r.allergens.length?r.allergens.map(a=>allergyNames[a]||a).join(', '):'rótulos, misturas de temperos e contaminação cruzada'}. As marcas e os ingredientes opcionais podem alterar os alergénios.</p><h3>Ingredientes</h3><ul>${r.ingredients.map(i=>`<li>${E(i.name)} — ${E(i.qty===null?'q.b.':F.quantity({...i,count:1}))}${i.note?' · '+E(i.note):''}</li>`).join('')}</ul><h3>Preparação</h3><ol>${r.steps.map(s=>`<li>${E(s)}</li>`).join('')}</ol>${r.video?`<a class="btn" href="${safeLink(r.video)}" target="_blank" rel="noopener">Ver vídeo</a>`:'<p class="tiny">O vídeo desta receita ainda não está disponível.</p>'}`;open('recipeDialog');}
function bindRecipes(){document.querySelectorAll('[data-recipe]').forEach(b=>b.onclick=()=>showRecipe(b.dataset.recipe));}
function swap(day,meal){const options=F.candidates(R,profile,meal);$('swapChoices').innerHTML=`<p>Dia ${day} · ${F.meals[meal]}. A troca atualiza também as compras.</p>`+(options.length?options.map(r=>`<button class="swap-option" data-pick="${r.id}">${photo(r)}<span><b>${E(r.name)}</b><small>Vol. ${r.volume} · ${E(r.nutrition.portion)}</small></span>${ctx.state.foodPlan[day-1][meal]===r.id?'✓':'→'}</button>`).join(''):'<p class="notice">Não há trocas compatíveis nesta seleção. Não alteramos os ingredientes das receitas automaticamente.</p>');open('swapDialog');$('swapChoices').querySelectorAll('[data-pick]').forEach(b=>b.onclick=()=>{const old=ctx.state.foodPlan[day-1][meal];ctx.state.foodPlan[day-1][meal]=b.dataset.pick;delete ctx.state.mealChecks?.[`${day}:${meal}:${old}`];persist();close('swapDialog');renderFood();});}
function clearDayChecks(day){for(const key of Object.keys(ctx.state.mealChecks||{}))if(key.startsWith(day+':'))delete ctx.state.mealChecks[key];}
function bindFood(){
 bindRecipes();document.querySelectorAll('[data-edit-profile]').forEach(b=>b.onclick=openProfile);
 document.querySelectorAll('[data-food-day]').forEach(b=>b.onclick=()=>{ctx.state.day=Number(b.dataset.foodDay);persist();renderFood();});
 document.querySelectorAll('[data-week]').forEach(b=>b.onclick=()=>{week=Number(b.dataset.week);renderFood();});
 document.querySelectorAll('[data-swap]').forEach(b=>b.onclick=()=>{const [d,m]=b.dataset.swap.split(':');swap(Number(d),m);});
 document.querySelectorAll('[data-meal-check]').forEach(b=>b.onchange=()=>{ctx.state.mealChecks??={};ctx.state.mealChecks[b.dataset.mealCheck]=b.checked;persist();});
 document.querySelectorAll('[data-shopping]').forEach(b=>b.onchange=()=>{ctx.state.shoppingChecks??={};ctx.state.shoppingChecks[b.dataset.shopping]=b.checked;persist();});
 document.querySelectorAll('[data-repeat-day]').forEach(b=>b.onclick=()=>{const d=Number(b.dataset.repeatDay);if(d>=21)return;if(!confirm(`Repetir as refeições do dia ${d} no dia ${d+1}? As escolhas anteriores desse dia serão substituídas.`))return;ctx.state.foodPlan[d]={...ctx.state.foodPlan[d-1]};clearDayChecks(d+1);persist();renderFood();ctx.flash('Refeições repetidas no dia seguinte.');});
 if($('repeatWeekOptions'))$('repeatWeekOptions').onclick=e=>{const b=e.target.closest('[data-copy-week]');if(!b)return;const target=Number(b.dataset.copyWeek);if(!confirm(`Substituir as refeições da semana ${target+1} pelas da semana ${week+1}?`))return;for(let i=0;i<7;i++){ctx.state.foodPlan[target*7+i]={...ctx.state.foodPlan[week*7+i]};clearDayChecks(target*7+i+1);}persist();renderFood();ctx.flash('Semana repetida.');};
 if($('repeatWeekOptions'))document.querySelector('[data-repeat-week]').onclick=()=>{$('repeatWeekOptions').innerHTML=[0,1,2].filter(w=>w!==week).map(w=>`<button class="btn light" data-copy-week="${w}">Repetir na semana ${w+1}</button>`).join(' ');};
}
function accountContent(){
 if(session){$('accountContent').innerHTML=`<p>Sessão iniciada: <b>${E(session.email)}</b></p><p class="tiny">O perfil, as refeições e o progresso ficam associados à tua conta.</p><button class="btn full" id="syncNow">Sincronizar agora</button><button class="btn light full" id="logoutAccount">Terminar sessão</button><p id="accountError" role="status"></p>`;$('syncNow').onclick=()=>sync().then(()=>$('accountError').textContent='Conta sincronizada.').catch(e=>$('accountError').textContent=e.message);$('logoutAccount').onclick=async()=>{try{await sync();await request('logout','POST',{});session=null;ctx.state.profileV4=null;ctx.state.foodPlan=null;ctx.state.mealChecks={};ctx.state.shoppingChecks={};ctx.state.checks={};ctx.state.name='';ctx.state.day=1;ctx.state.profileDone=false;ctx.state.userId=null;ctx.state.loggedIn=false;ctx.save();profile=null;note();close('accountDialog');ctx.screen('inicio');}catch(e){$('accountError').textContent=e.message;}};return;}
 $('accountContent').innerHTML=`<p>Guarda o teu perfil e continua noutro dispositivo.</p>${!online?'<p class="notice">As contas requerem o servidor da aplicação. Nesta pré-visualização estática podes continuar com os dados guardados neste navegador.</p>':''}<form id="accountForm"><label for="accountEmail">Email</label><input id="accountEmail" type="email" autocomplete="email" required maxlength="254"><label for="accountPassword">Palavra-passe</label><input id="accountPassword" type="password" minlength="1" maxlength="128" autocomplete="current-password" required><div class="row profile-actions"><button class="btn" type="submit">Entrar</button><button class="btn light" id="registerAccount" type="button">Criar conta</button></div><p id="accountError" class="form-error" role="alert"></p></form>`;
 async function auth(mode){const form=$('accountForm');if(!form.reportValidity())return;const buttons=form.querySelectorAll('button');buttons.forEach(b=>b.disabled=true);try{
 const data=await request(mode,'POST',{email:$('accountEmail').value.trim(),password:$('accountPassword').value,name:ctx.state.name||''});session=data.user;online=true;ctx.state.accountOwner=session.id;
 const saved=await request('state');
 if(saved.state){Object.assign(ctx.state,{...saved.state,userId:null,loggedIn:true});profile=ctx.state.profileV4;ctx.state.profileDone=Boolean(profile);ctx.save();}
 else{await sync();}note();close('accountDialog');ctx.screen(profile?'alimentacao':'inicio');if(!profile)openProfile();ctx.flash('Sessão iniciada.');
 }catch(e){$('accountError').textContent=e.message;}finally{buttons.forEach(b=>b.disabled=false);}}
 $('accountForm').onsubmit=e=>{e.preventDefault();auth('login');};$('registerAccount').onclick=()=>auth('register');
}
async function restoreSession(){try{const data=await request('session');online=true;session=data.user||null;if(session){if(ctx.state.accountOwner===session.id&&ctx.state.syncPending&&ctx.state.profileV4){await sync();}else{const saved=await request('state');if(saved.state){Object.assign(ctx.state,saved.state);ctx.state.profileDone=Boolean(ctx.state.profileV4);profile=ctx.state.profileV4;ctx.save();}else if(ctx.state.profileV4){await sync();}}ctx.state.accountOwner=session.id;ctx.save();}note();}catch(e){online=false;note();}}
function init(context){ctx=context;ctx.state.mealChecks??={};ctx.state.shoppingChecks??={};profile=ctx.state.profileV4;
 // Não enviar identificadores fictícios do login V3 para o servidor.
 ctx.state.userId=null;ctx.state.loggedIn=false;
 $('editProfile').onclick=openProfile;$('foodProfile').onclick=openProfile;$('closeProfile').onclick=()=>close('onboardModal');
 $('profileBack').onclick=()=>setStep(Math.max(1,step-1));$('profileNext').onclick=()=>{if(validStep())setStep(Math.min(3,step+1));};$('profileForm').onsubmit=saveProfile;
 document.querySelectorAll('[data-close-dialog]').forEach(b=>b.onclick=()=>close(b.dataset.closeDialog));
 document.querySelectorAll('[data-food-tab]').forEach(b=>{b.onclick=()=>{tab=b.dataset.foodTab;renderFood();};b.onkeydown=e=>{if(!['ArrowRight','ArrowLeft'].includes(e.key))return;e.preventDefault();const buttons=[...document.querySelectorAll('[data-food-tab]')];const index=buttons.indexOf(b);const next=buttons[(index+(e.key==='ArrowRight'?1:3))%4];next.click();next.focus();};});
 $('accountButton').onclick=()=>{accountContent();open('accountDialog');};
 document.addEventListener('keydown',e=>{const dialog=[...document.querySelectorAll('.modalback:not(.hidden)')].at(-1);if(!dialog)return;if(e.key==='Escape'){close(dialog.id);return;}if(e.key==='Tab'){const list=[...dialog.querySelectorAll('button,input,select,a[href],textarea')].filter(el=>!el.disabled&&el.getClientRects().length);if(!list.length)return;const first=list[0],last=list.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}});
 window.FocoV4.ready=restoreSession();
}
window.FocoV4={init,renderFood,openProfile,sync};
})();
