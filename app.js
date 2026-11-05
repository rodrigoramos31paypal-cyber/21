(() => {
'use strict';
const c=window.FOCO_CONTENT;const KEY='foco_21_v3';let state={screen:'inicio',day:1,track:'geral',checks:{},name:'',loggedIn:false,paid:false,email:'',userId:null,profileDone:false};
try{const v=localStorage.getItem(KEY);if(v){state={...state,...JSON.parse(v)}}}catch(e){}
if(state.accountOwner){window.FocoAccounts.transition(state,null,null);}
const $=id=>document.getElementById(id),save=()=>{try{if(state.accountOwner){sessionStorage.setItem('foco_account_pending',JSON.stringify(state));localStorage.removeItem(KEY)}else{sessionStorage.removeItem('foco_account_pending');localStorage.setItem(KEY,JSON.stringify(state))}}catch(e){}};
const encode=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
function flash(message){$('toast').textContent=message;$('toast').classList.remove('hidden');clearTimeout(flash.timer);flash.timer=setTimeout(()=>$('toast').classList.add('hidden'),3500)}
// API helpers
async function api(path, method='GET', body) {
  const opts = {method, headers:{'Content-Type':'application/json'}};
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  const data = await r.json();
  if(!r.ok)throw Error(data.error||'Serviço indisponível.');
  return data;
}
async function loadProgress() {
  if (!state.userId) return;
  const data = await api(`/api/progress?user_id=${state.userId}`);
  if (data.checks) {
    state.checks = {};
    for (const [d, c] of Object.entries(data.checks)) state.checks[d] = c;
    save();
  }
}
async function saveProgress(day) {
  if (!state.userId) return;
  await api('/api/progress', 'POST', {user_id: state.userId, day, checks: state.checks[day], track: state.track});
}
function renderAlimentacao(){window.FocoV4.renderFood()}

// Admin
async function loadAdmin(){
  try{
    const stats = await api('/api/admin/stats');
    $('adminTotal').textContent = stats.total_users || 0;
    $('adminProgress').textContent = stats.users_with_progress || 0;
    const data = await api('/api/admin/users');
    const list = data.users || [];
    $('adminUsers').innerHTML = list.length
      ? list.map(u => `<div style="padding:8px 0;border-bottom:1px solid var(--edge)"><b>${encode(u.name||u.email)}</b> · ${encode(u.email)}<br><span class="tiny">${u.track||'—'} · ${u.created_at?u.created_at.slice(0,10):''}</span></div>`).join('')
      : 'Nenhum utilizador ainda.';
  }catch(e){
    $('adminUsers').textContent = 'Erro ao carregar (servidor ativo?).';
  }
}
function showAdmin(){
  document.getElementById('adminNav').style.display = 'flex';
  screen('admin');
  loadAdmin();
}

function screen(name){
  state.screen=name;save();document.querySelectorAll('.scene').forEach(el=>el.classList.toggle('active',el.id==='screen-'+name));document.querySelectorAll('[data-screen]').forEach(el=>{el.classList.toggle('active',el.dataset.screen===name);el.setAttribute('aria-current',el.dataset.screen===name?'page':'false')});if(name==='hoje')renderToday();if(name==='plano')renderPlan();if(name==='alimentacao')renderAlimentacao();if(name==='admin')loadAdmin();window.scrollTo({top:0,behavior:'smooth'})
}
const record=d=>state.checks[d]||[false,false,false];const allDone=d=>record(d).every(Boolean);const daysDone=()=>Array.from({length:21},(_,i)=>i+1).filter(allDone).length;
function getExercises(d){const type=c.days[d-1].type;return c.exercises[state.track][type]||c.common[type]||[]}
function renderToday(){const d=state.day,datum={...c.days[d-1],focus:window.FocoV4.textForDay(d)||c.days[d-1].focus},week=Math.ceil(d/7),prog=record(d).filter(Boolean).length;const workout=getExercises(d),kind=datum.type;
$('myName').textContent=state.name?`, ${state.name}`:'';
$('todayDay').textContent=String(d).padStart(2,'0');$('todayWeek').textContent='SEMANA '+week;$('todayTitle').textContent=datum.name;$('todayFocus').textContent=datum.focus;$('todayMini').textContent=`${d} de 21 · ${daysDone()} feitos`;
$('guideTitle').textContent = 'Hoje: ' + datum.name;
$('guideText').textContent = datum.focus + ' Marca as 3 tarefas quando terminares.';
const msgs = ['Foco no que controlas hoje.','Consistência vale mais do que perfeição.','Um dia de cada vez.','Já estás a construir o hábito.'];
$('jpMessage').textContent = '“' + msgs[d % msgs.length] + '” — João Pedro';
if(d===21){ $('guideText').textContent = 'Avaliação final. Fizeste ' + daysDone() + ' dias completos. Marca as tarefas e vê o resumo.'; }
$('prevDay').disabled=d===1;$('nextDay').disabled=d===21;
$('todayProgress').style.setProperty('--p',Math.round(prog/3*100));$('todayProgressNum').textContent=prog+'/3';$('todayStats').textContent=`${daysDone()} dias completos de 21`;
$('workoutTitle').textContent=datum.name;$('workoutSubtitle').textContent=(kind==='A'||kind==='B'||kind==='C')?c.trainingTracks[state.track]+' · 30–45 min':kind==='recovery'?'Recuperação leve':kind==='check'?'Reflexão e evolução':'Bloco comum · Movimento';
$('exerciseList').innerHTML=workout.map((x,i)=>`<div class="exercise"><div class="number">${i+1}</div><div><b>${encode(x[0])}</b><small>${kind==='check'?'Objetivo de acompanhamento':'Execução em vídeo a adicionar'}</small></div><em>${encode(x[1])}</em></div>`).join('');
$('dayImage').src=`assets/DIA_${String(d).padStart(2,'0')}.png`;$('dayImage').alt=`Cartão do dia ${d}: ${datum.name}`;
const videourl=window.FocoV4.videoForDay(d)||c.videoUrls[d]||'';const videoBtn=$('videoAction');videoBtn.textContent=videourl?'▶ Ver vídeo de hoje':'Em breve';videoBtn.disabled=false;videoBtn.onclick=()=>{if(videourl){window.open(videourl,'_blank','noopener,noreferrer')}else flash('Este vídeo será ligado depois das gravações.')};
const taskNames=kind==='check'?['Fiz o check-in e a reflexão','Organizei as refeições','Defini o próximo objetivo']:['Completei o movimento de hoje','Preparei / organizei a alimentação','Cumpri o objetivo de foco'];
$('tasks').innerHTML=taskNames.map((label,i)=>`<label class="task"><input type="checkbox" data-task="${i}" ${record(d)[i]?'checked':''}/><span>${encode(label)}</span></label>`).join('');
$('tasks').querySelectorAll('input[data-task]').forEach(input=>input.addEventListener('change',async ()=>{const a=[...record(d)];a[+input.dataset.task]=input.checked;state.checks[d]=a;save();try{await window.FocoV4.sync()}catch(e){}renderToday();flash(a.every(Boolean)?'Dia fechado. Continuas.':'Marcado.'); if(a.every(Boolean)){ document.body.classList.add('day-complete'); setTimeout(()=>document.body.classList.remove('day-complete'),1200); } }));
$('trackSelect').value=state.track;
const checkDays = [7,14,21];
const banner = document.getElementById('checkinBanner');
if(banner) banner.classList.toggle('hidden', !checkDays.includes(d));
if(d===21 && !state.offerShown){ setTimeout(()=>{ $('offerModal').classList.remove('hidden'); state.offerShown=true; save(); }, 800); }
}
function renderPlan(){const done=daysDone();$('planComplete').textContent=`${done}/21 dias concluídos`;$('planPercent').textContent=Math.round(done/21*100)+'%';$('planTrack').value=state.track;
$('weeks').innerHTML=Array.from({length:3},(_,wi)=>{let d0=wi*7+1;return `<div class="week"><div class="row"><h3>Semana ${wi+1}</h3><span class="tiny">Dias ${d0}–${d0+6}</span></div><div class="days">${Array.from({length:7},(_,j)=>{let d=d0+j;return `<button class="daychip ${d===state.day?'selected':''} ${allDone(d)?'completed':''}" data-goday="${d}" title="Dia ${d} · ${encode(c.days[d-1].name)}" aria-label="Abrir dia ${d}">${d}</button>`}).join('')}</div><p class="weekfoot">${['Aprender a começar','Repetir com qualidade','Consolidar a rotina'][wi]}</p></div>`}).join('');
$('weeks').querySelectorAll('[data-goday]').forEach(btn=>btn.onclick=()=>{state.day=+btn.dataset.goday;save();screen('hoje')});
}
function setTrack(v){state.track=v;save();window.FocoV4.sync().catch(()=>{});renderToday();renderPlan();flash('Percurso atualizado.')}
function openModal(){document.getElementById('modal').classList.remove('hidden')}
function closeModal(){document.getElementById('modal').classList.add('hidden')}
function openLogin(){$('loginModal').classList.remove('hidden')}
function closeLogin(){$('loginModal').classList.add('hidden')}
function openOnboard(){window.FocoV4.openProfile()}
function closeOnboard(){$('onboardModal').classList.add('hidden')}
function wire(){document.querySelectorAll('[data-screen]').forEach(btn=>btn.onclick=()=>screen(btn.dataset.screen));
$('startDemo').onclick=()=>screen('hoje');
$('openDemo2').onclick=()=>screen('hoje');
$('modal').onclick=e=>{if(e.target.id==='modal')closeModal()};
$('prevDay').onclick=()=>{state.day=Math.max(1,state.day-1);save();renderToday()};$('nextDay').onclick=()=>{state.day=Math.min(21,state.day+1);save();renderToday()};
$('trackSelect').onchange=e=>setTrack(e.target.value);$('planTrack').onchange=e=>setTrack(e.target.value);
$('nameInput').value=state.name;$('nameInput').addEventListener('input',e=>{state.name=e.target.value.trim().slice(0,28);if(state.profileV4&&state.name)state.profileV4.name=state.name;save();window.FocoV4.sync().catch(()=>{});$('myName').textContent=state.name?`, ${state.name}`:''});
$('restart').onclick=()=>{if(confirm('Reiniciar o teu progresso?')){state.checks={};state.day=1;save();renderPlan();flash('Progresso reiniciado.')}};
$('demoCheck').onclick=()=>{state.checks[1]=[true,true,true];state.day=1;save();renderToday();flash('Exemplo: Dia 1 marcado como concluído.')};
$('priceButton').onclick=openModal;$('modalClose').onclick=closeModal;$('modalOk').onclick=()=>{closeModal();flash('Pagamento ainda não ativo.');};
window.FocoV4.init({state,save,screen,flash,encode,renderToday,renderPlan});
// Pay
$('subBtn') && ($('subBtn').onclick=()=>{$('accountButton').click();$('offerModal').classList.add('hidden');});
  const adminRefresh=$('adminRefresh');if(adminRefresh)adminRefresh.onclick=loadAdmin;

}

// Theme
function applyTheme(t){
  document.documentElement.setAttribute('data-theme', t);
  try{localStorage.setItem('foco_theme', t)}catch(e){}
  const meta = document.querySelector('meta[name="theme-color"]');
  if(meta) meta.content = t === 'dark' ? '#0f1614' : '#101816';
  const btn = document.getElementById('themeToggle');
  if(btn) btn.textContent = t === 'dark' ? '☀️' : '🌙';
}
function initTheme(){
  let saved='light';try{saved=localStorage.getItem('foco_theme')||'light'}catch(e){}
  applyTheme(saved);
  const btn = document.getElementById('themeToggle');
  if(btn) btn.onclick = () => applyTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
}

window.addEventListener('DOMContentLoaded',async()=>{
  wire();
  initTheme();
  await window.FocoV4.ready;
  screen(state.profileDone ? 'hoje' : 'inicio');
  if(!state.profileV4) openOnboard();
});
})();
