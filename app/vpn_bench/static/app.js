var state={page:"dashboard",servers:[],providers:[],selected:{},mode:"equal_time",duration:600,filters:[""],serverFilters:{provider:"",country:"",protocol:"",status:"",search:""},screening:null,screeningFirst:30,screeningSecond:30,screeningRepeats:2,screeningMax:"",serverDetail:null,analyticsMetric:"speed",analyticsPeriod:"24h",analyticsSelected:[],screeningEnabled:false};
var app=document.getElementById("app");

function esc(v){return String(v==null?"":v).replace(/[&<>"]/g,function(m){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[m]})}
function num(v,d){return v==null||Number.isNaN(Number(v))?"—":Number(v).toFixed(d==null?0:d)}
function fmt(s){s=Math.max(0,Math.round(s||0));var h=Math.floor(s/3600);s%=3600;var m=Math.floor(s/60),x=s%60;return (h?String(h).padStart(2,"0")+":":"")+String(m).padStart(2,"0")+":"+String(x).padStart(2,"0")}
function api(p,o){return fetch(p,Object.assign({headers:{"Content-Type":"application/json"}},o||{})).then(async function(r){if(!r.ok){var e={};try{e=await r.json()}catch(_){ }throw new Error(e.detail||"Ошибка запроса")}return r.json()})}
function icon(name){
  var paths={
    dashboard:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    providers:'<path d="M12 3v18M3 8h18M5 8v8M19 8v8M8 16h8M8 12h8"/><circle cx="12" cy="8" r="2"/>',
    servers:'<rect x="3" y="4" width="18" height="6" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><path d="M7 7h.01M7 17h.01"/>',
    tests:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    analytics:'<path d="M4 19V9M9 19V5M14 19v-7M19 19V3"/><path d="M2 19h20"/>',
    logs:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-1.8 1.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5v.1h-2.5v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1-1.8-1.8.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H6.6v-2.5h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1 1.8-1.8.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.5V4.6h2.5v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1 1.8 1.8-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.5 1h.1v2.5h-.1a1.7 1.7 0 0 0-1.5 1Z"/>',
    search:'<circle cx="11" cy="11" r="6.5"/><path d="m16 16 5 5"/>',
    refresh:'<path d="M20 11a8 8 0 0 0-14.9-4L3 10"/><path d="M3 5v5h5"/><path d="M4 13a8 8 0 0 0 14.9 4L21 14"/><path d="M21 19v-5h-5"/>',
    plus:'<path d="M12 5v14M5 12h14"/>',
    arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',
    back:'<path d="m15 18-6-6 6-6"/><path d="M9 12h10"/>',
    filter:'<path d="M4 6h16M7 12h10M10 18h4"/>',
    check:'<path d="m5 12 4 4L19 6"/>',
    warning:'<path d="m12 4 9 16H3L12 4Z"/><path d="M12 9v5M12 17h.01"/>',
    info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    eye:'<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="2.5"/>',
    lock:'<rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>'
  };
  return '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">'+(paths[name]||paths.info)+'</svg>';
}
function badge(text,type){return '<span class="badge '+(type||"")+'"><i></i>'+esc(text)+'</span>'}
function countryInfo(value){var s=String(value||"");var emoji=s.match(/^\s*([\u{1F1E6}-\u{1F1FF}]{2})/u);if(emoji){var f=emoji[1],a=[...f].map(function(ch){return ch.codePointAt(0)-127397});return {flag:f,code:String.fromCharCode(a[0])+String.fromCharCode(a[1])}}var n=s.toLowerCase();var map={"germany":"DE","de":"DE","france":"FR","fr":"FR","finland":"FI","fi":"FI","netherlands":"NL","nl":"NL","poland":"PL","pl":"PL","estonia":"EE","ee":"EE","united kingdom":"GB","uk":"GB","united states":"US","us":"US","japan":"JP","singapore":"SG","russia":"RU","ru":"RU"};for(var k in map)if(n===k||n.indexOf(k)>=0)return {flag:map[k].replace(/./g,function(x){return String.fromCodePoint(x.charCodeAt(0)+127397)}),code:map[k]};return {flag:"",code:""}}
function flag(name){return countryInfo(name).flag}
function displayServerName(name){return String(name||"").replace(/^\s*[\u{1F1E6}-\u{1F1FF}]{2}\s*/u,"").replace(/^\s*🌐\s*/,"")||String(name||"—")}
function providerName(id){var p=state.providers.find(function(x){return x.id===id});return p?(p.display_name||p.name):"—"}
function statusDot(ok){return '<span class="status-dot '+(ok===false?"bad":ok===true?"good":"neutral")+'"></span>'}
function head(t,s,action){return '<div class="page-head"><div><h1>'+t+'</h1><p>'+s+'</p></div>'+(action||"")+'</div>'}
function card(title,sub,body,cls){return '<section class="card '+(cls||"")+'"><div class="card-head"><div><h3>'+title+'</h3>'+(sub?'<p>'+sub+'</p>':"")+'</div></div>'+body+'</section>'}

async function boot(){
  try{
    var s=await api("/api/v1/setup/status");
    if(!s.configured){setupPage();return}
    try{await api("/api/v1/auth/me")}catch(_){loginPage();return}
    try{await refresh()}catch(e){state.bootError=e.message}
    await render()
  }catch(e){app.innerHTML='<div class="auth-wrap"><div class="auth-card card"><img src="/static/LOGO.svg" class="auth-logo"><h1>Ошибка запуска</h1><p>'+esc(e.message||e)+'</p><button class="btn" onclick="location.reload()">Повторить</button></div></div>'}
}
function setupPage(){app.innerHTML='<div class="auth-wrap"><div class="auth-card card"><img src="/static/LOGO.svg" class="auth-logo"><div class="auth-icon">'+icon("lock")+'</div><h1>Добро пожаловать</h1><p>Создайте пароль администратора VPN-Bench. Минимум 12 символов.</p><input id="p1" class="input" type="password" placeholder="Пароль"><input id="p2" class="input" type="password" placeholder="Повторите пароль"><button class="btn wide" onclick="setup()">Создать администратора</button></div></div>'}
async function setup(){var a=document.getElementById("p1").value,b=document.getElementById("p2").value;if(a!==b)return alert("Пароли не совпадают");try{await api("/api/v1/setup",{method:"POST",body:JSON.stringify({password:a})});await refresh();render()}catch(e){showToast(e.message,"error")}}
function loginPage(){app.innerHTML='<div class="auth-wrap"><div class="auth-card card"><img src="/static/LOGO.svg" class="auth-logo"><div class="auth-icon">'+icon("lock")+'</div><h1>Вход в VPN-Bench</h1><p>Введите пароль администратора.</p><input id="lp" class="input" type="password" placeholder="Пароль" onkeydown="if(event.key===\'Enter\')login()"><button class="btn wide" onclick="login()">Войти</button></div></div>'}
async function login(){try{await api("/api/v1/auth/login",{method:"POST",body:JSON.stringify({password:document.getElementById("lp").value})});await refresh();render()}catch(e){alert("Неверный пароль")}}
async function refresh(){state.providers=await api("/api/v1/providers");state.servers=await api("/api/v1/servers")}

function nav(){
  var n=document.querySelector(".nav");
  if(n&&!n.dataset.bound){
    n.addEventListener("click",function(e){var b=e.target.closest("button[data-page]");if(!b)return;state.page=b.dataset.page;state.serverDetail=null;render()});
    n.dataset.bound="1";
  }
  document.querySelectorAll(".nav button").forEach(function(b){b.classList.toggle("active",b.dataset.page===state.page)})
}
async function render(){
  nav();
  try{
    if(state.page==="dashboard")await dashboard();
    else if(state.page==="providers")providers();
    else if(state.page==="servers")servers();
    else if(state.page==="tests")tests();
    else if(state.page==="analytics")await analytics();
    else if(state.page==="logs")await logs();
    else settings();
  }catch(e){app.innerHTML=head("Ошибка","Не удалось загрузить раздел")+'<section class="card error-card"><div class="empty-icon">'+icon("warning")+'</div><h3>Не удалось загрузить раздел</h3><p>'+esc(e.message||e)+'</p><button class="btn" onclick="render()">Повторить</button></section>'}
}

function dashboardChart(data,w,h){
  if(!data||!data.length)return '<div class="chart-empty"><span>'+icon("analytics")+'</span><b>Недостаточно данных для графика</b><small>После первых измерений здесь появится динамика скорости.</small></div>';
  var vals=[];data.forEach(function(x){if(x.download_mbps!=null)vals.push(Number(x.download_mbps));if(x.upload_mbps!=null)vals.push(Number(x.upload_mbps))});
  if(!vals.length)return '<div class="chart-empty"><span>'+icon("analytics")+'</span><b>Нет данных о скорости</b><small>Запустите тестирование серверов.</small></div>';
  var max=Math.max.apply(null,vals)||1, pts1=[],pts2=[];
  data.forEach(function(x,i){var xx=30+(i*Math.max(1,(w-55)/Math.max(1,data.length-1)));pts1.push(xx+","+(h-32-(Number(x.download_mbps||0)/max)*(h-65)));pts2.push(xx+","+(h-32-(Number(x.upload_mbps||0)/max)*(h-65)))});
  return '<svg class="chart" viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none"><line x1="30" y1="28" x2="'+(w-15)+'" y2="28" class="gridline"/><line x1="30" y1="'+(h/2)+'" x2="'+(w-15)+'" y2="'+(h/2)+'" class="gridline"/><line x1="30" y1="'+(h-32)+'" x2="'+(w-15)+'" y2="'+(h-32)+'" class="gridline"/><polyline points="'+pts1.join(" ")+'" class="line-blue"/><polyline points="'+pts2.join(" ")+'" class="line-green"/></svg>'
}
function donut(opt,warn,fail){
  var total=opt+warn+fail;if(!total)return '<div class="donut-empty">Нет накопленных измерений</div>';
  var p=Math.round(opt/total*100);
  return '<div class="donut-wrap"><div class="donut" style="--p:'+p+'%"><div><b>'+p+'%</b><span>доступны</span></div></div><div class="legend"><span><i class="lg good"></i>Отличны <b>'+opt+'</b></span><span><i class="lg warn"></i>Внимание <b>'+warn+'</b></span><span><i class="lg bad"></i>Проблемы <b>'+fail+'</b></span></div></div>'
}
async function dashboard(){
  var d=await api("/api/v1/dashboard"),t=d.test||{},top=d.top_servers||[];
  var rows=top.map(function(r,i){return '<tr><td>'+String(i+1).padStart(2,"0")+'</td><td>'+esc(r.provider)+'</td><td><span class="server-name">'+(flag(r.name)?flag(r.name)+" ":"")+esc(displayServerName(r.name))+'</span></td><td>'+num(r.latency_ms,0)+' ms</td><td><b>'+num(r.download_mbps,0)+'</b> Мбит/с</td><td>'+num(r.availability,1)+'%</td></tr>'}).join("");
  var html=head("Дашборд","Краткая статистика по всем провайдерам и серверам",'<span class="updated"><span class="pulse"></span>Обновлено: сейчас</span>');
  html+='<div class="stats">';
  html+='<div class="kpi"><span class="kpi-icon blue">'+icon("providers")+'</span><div><b>'+d.providers+'</b><span>Провайдеров</span><small>Подключено</small></div></div>';
  html+='<div class="kpi"><span class="kpi-icon violet">'+icon("servers")+'</span><div><b>'+d.servers+'</b><span>Серверов</span><small>Всего</small></div></div>';
  html+='<div class="kpi"><span class="kpi-icon cyan">'+icon("tests")+'</span><div><b>'+d.testing_now+'</b><span>Тестируется</span><small>Сейчас</small></div></div>';
  html+='<div class="kpi"><span class="kpi-icon green">'+icon("check")+'</span><div><b>'+d.optimal+'</b><span>Оптимальных</span><small>По накопленным данным</small></div></div></div>';
  html+='<div class="dashboard-grid">';
  html+='<section class="card chart-card"><div class="card-head"><div><h3>Средняя скорость по времени</h3><p>Загрузка и отдача за последние 24 часа</p></div><div class="chart-legend"><span><i class="legend-dot blue-dot"></i>Загрузка</span><span><i class="legend-dot green-dot"></i>Отдача</span></div></div>'+dashboardChart(d.speed_trend,720,230)+'</section>';
  html+='<section class="card availability"><div class="card-head"><div><h3>Доступность серверов</h3><p>По накопленным измерениям</p></div></div>'+donut(d.optimal,d.warning,d.failed)+'</section></div>';
  html+='<section class="card table-card"><div class="card-head"><div><h3>Топ серверы</h3><p>По доступности, задержке и скорости</p></div><button class="btn secondary" onclick="state.page=\'servers\';render()">Все серверы <span>'+icon("arrow")+'</span></button></div><div class="table-scroll"><table class="table"><thead><tr><th>#</th><th>Провайдер</th><th>Сервер</th><th>Задержка</th><th>Скорость ↓</th><th>Доступность</th></tr></thead><tbody>'+(rows||'<tr><td colspan="6" class="empty">Измерений пока нет</td></tr>')+'</tbody></table></div></section>';
  if(t.status==="running")html+='<section class="card live-card"><div class="card-head"><div><h3>Тестирование сейчас</h3><p>'+esc(t.current_server_name||"Подготовка")+'</p></div><b>'+t.completed_servers+" / "+t.total_servers+'</b></div>'+summary(t)+'</section>';
  app.innerHTML=html;
  if(t.status==="running")setTimeout(dashboard,1000);
}
function summary(t){
  if(!t||t.status==="idle")return '<div class="empty-state"><div class="empty-icon">'+icon("check")+'</div><b>Тестирование не запущено</b><span>Выберите серверы и запустите тест в разделе «Тесты».</span></div>';
  return '<div class="test-progress-head"><div><b>'+esc(t.current_server_name||"Завершение")+'</b><span>'+esc(t.message||"")+'</span></div><strong>'+t.progress+'%</strong></div><div class="progress"><div class="bar" style="width:'+t.progress+'%"></div></div><div class="test-meta"><span>Обработано <b>'+t.completed_servers+' / '+t.total_servers+'</b></span><span>Прошло <b>'+fmt(t.elapsed_seconds)+'</b></span><span>Осталось <b>'+(t.remaining_seconds==null?"рассчитывается":fmt(t.remaining_seconds))+'</b></span></div>'
}

function metadataSummary(p){var m=p.metadata||{},parts=[];if(m["profile-title"])parts.push(m["profile-title"]);if(m.server_count!=null)parts.push(m.server_count+" серверов");if(m.expire_at)parts.push("до "+new Date(m.expire_at).toLocaleDateString("ru-RU"));else if(m.expire)parts.push("до "+new Date(Number(m.expire)*1000).toLocaleDateString("ru-RU"));if(m.total!=null){var used=Number(m.used||0),total=Number(m.total||0);parts.push((used/1073741824).toFixed(1)+" / "+(total/1073741824).toFixed(1)+" GB");}if(m["profile-update-interval"])parts.push("обновление "+m["profile-update-interval"]);if(Array.isArray(m.protocols)&&m.protocols.length)parts.push(m.protocols.join(", "));if(Array.isArray(m.countries)&&m.countries.length)parts.push(m.countries.join(", "));return parts.join(" · ")}\nfunction providerRows(){
  return state.providers.map(function(p){
    var n=state.servers.filter(function(s){return s.provider_id===p.id}).length;
    var meta=metadataSummary(p);
    return '<tr><td><span class="status-dot '+(p.enabled?"good":"bad")+'"></span></td><td><div class="entity"><b>'+esc(p.display_name||p.name||"—")+'</b><small>'+esc(p.name||"Автоопределение")+'</small>'+(meta?'<small>'+esc(meta)+'</small>':"")+'</div></td><td><span class="masked-url">'+esc(p.subscription_url_masked||"••••")+'</span></td><td>'+n+'</td><td>'+badge(p.enabled?"Активен":"Выключен",p.enabled?"good":"bad")+'</td><td>'+esc(p.last_updated_at||"—")+'</td><td><div class="row-actions"><button class="icon-btn" onclick="editProvider(&quot;'+p.id+'&quot;)" title="Редактировать">✎</button><button class="icon-btn" onclick="syncProvider(&quot;'+p.id+'&quot;)" title="Обновить">'+icon("refresh")+'</button></div></td></tr>';
  }).join("");
}
function providers(){
  app.innerHTML=head("Провайдеры","Подключенные подписки, серверы и состояние обновления",'<button class="btn" onclick="providerForm()">'+icon("plus")+'Добавить провайдера</button>')+
  '<section class="card table-card"><div class="section-note"><span class="info-badge">'+icon("info")+'</span><div><b>Подписки хранятся защищённо</b><p>URL показывается в маскированном виде и раскрывается только по явному действию.</p></div></div><div class="table-scroll"><table class="table provider-table"><thead><tr><th></th><th>Провайдер</th><th>URL подписки</th><th>Серверов</th><th>Статус</th><th>Обновлено</th><th></th></tr></thead><tbody>'+(providerRows()||'<tr><td colspan="7" class="empty">Провайдеров пока нет</td></tr>')+'</tbody></table></div></section>'
}
function providerForm(id){
  var p=id?state.providers.find(function(x){return x.id===id}):null;
  var name=p?esc(p.display_name||""):"";
  app.innerHTML=head(p?"Редактировать провайдера":"Добавить провайдера","Настройка подписки и параметров обновления")+
  '<section class="card form-card"><div class="form-grid"><label>Название <span class="optional">необязательно</span><input id="pn" class="input" value="'+name+'" placeholder="Оставьте пустым — определится автоматически"></label><div class="field-help">Если поле пустое, VPN-Bench попробует получить название из метаданных подписки.</div><label>URL подписки <span>*</span><div class="input-with-action"><input id="pu" class="input" type="password" value="" placeholder="'+(p?(p.subscription_url_masked||"••••"): "https://example.com/sub")+'"><button class="icon-btn" onclick="revealProviderUrl(&quot;'+(p?p.id:"")+'&quot;)" title="Показать текущий URL">'+icon("eye")+'</button></div></label><label>Описание<input id="pd" class="input" placeholder="Необязательно"></label></div><div class="settings-inline"><label><input id="pa" type="checkbox" checked> Автоматическое обновление</label><label><input id="pv" type="checkbox" checked> Проверять доступность при обновлении</label></div><div class="form-actions"><button class="btn secondary" onclick="state.page=\'providers\';render()">Отмена</button><button class="btn" onclick="saveProvider(&quot;'+(p?p.id:"")+'&quot;)">Сохранить</button></div></section>'
}
async function revealProviderUrl(id){if(!id)return;try{var r=await api("/api/v1/providers/"+id+"/subscription-url"),el=document.getElementById("pu");if(el){el.type="text";el.value=r.subscription_url}}catch(e){alert(e.message)}}
async function saveProvider(id){
  var name=document.getElementById("pn").value.trim(),url=document.getElementById("pu").value.trim();
  try{
    if(!url&&id){var revealed=await api("/api/v1/providers/"+id+"/subscription-url");url=revealed.subscription_url}
    if(!url){showToast("Укажите URL подписки","error");return}
    var body={name:"",display_name:name||null,subscription_url:url,enabled:true};
    var p=await api(id?"/api/v1/providers/"+id:"/api/v1/providers",{method:id?"PUT":"POST",body:JSON.stringify(body)});
    var synced=await api("/api/v1/providers/"+p.id+"/sync",{method:"POST"});await refresh();state.page="providers";render();showToast("Подписка обновлена · "+(synced.servers||0)+" серверов","success")
  }catch(e){showToast(e.message,"error")}
}
function editProvider(id){providerForm(id)}
async function syncProvider(id){try{var r=await api("/api/v1/providers/"+id+"/sync",{method:"POST"});await refresh();render();showToast("Импортировано серверов: "+r.servers,"success")}catch(e){showToast(e.message,"error")}}

function countryOf(s){var m=s.metadata||{};return m.country_code||m.country||m.country_name||countryInfo(s.name).code||""}
function matchesRegexFilters(s){
  var expressions=state.filters.map(function(x){return String(x||"").trim()}).filter(Boolean);if(!expressions.length)return true;
  var hay=[s.name,s.provider,s.protocol,s.transport,s.security,countryOf(s)].join(" ");
  return expressions.every(function(expr){try{return !new RegExp(expr,"i").test(hay)}catch(_){return hay.toLowerCase().indexOf(expr.toLowerCase())<0}})
}
function filteredServers(){
  var f=state.serverFilters;
  return state.servers.filter(function(s){
    var name=String(s.name||"").toLowerCase(),provider=String(s.provider||""),protocol=String(s.protocol||""),country=countryOf(s),active=!!s.active;
    return matchesRegexFilters(s)&&(!f.provider||String(s.provider_id||"")===f.provider||provider===f.provider)&&(!f.country||country===f.country)&&(!f.protocol||protocol===f.protocol)&&(!f.status||(f.status==="online"&&active)||(f.status==="offline"&&!active))&&(!f.search||name.indexOf(f.search.toLowerCase())>=0)
  })
}
function filterOptions(list,value){return list.filter(Boolean).filter(function(x,i,a){return a.indexOf(x)===i}).sort().map(function(x){return '<option value="'+esc(x)+'" '+(x===value?"selected":"")+'>'+esc(x)+'</option>'}).join("")}
function updateServerFilter(key,value){state.serverFilters[key]=value;render()}
var SERVER_COLUMNS_KEY="vpn-bench.server-columns.v1";
var defaultServerColumns=["provider","server","country","protocol","latency","speed","availability","status"];
function serverColumnOrder(){try{var x=JSON.parse(localStorage.getItem(SERVER_COLUMNS_KEY)||"[]");return defaultServerColumns.filter(function(k){return x.indexOf(k)>=0}).concat(defaultServerColumns.filter(function(k){return x.indexOf(k)<0}))}catch(_){return defaultServerColumns.slice()}}
function serverCell(s,col){var country=countryOf(s)||"",f=flag(s.name),name=displayServerName(s.name),latest=s.latest_result||{};if(col==="provider")return '<td data-col="provider">'+esc(s.provider||"—")+'</td>';if(col==="server")return '<td data-col="server"><span class="server-name">'+(f?f+" ":"")+esc(name)+'</span></td>';if(col==="country")return '<td data-col="country">'+(f?f+" ":"")+esc(country||"—")+'</td>';if(col==="protocol")return '<td data-col="protocol" title="'+esc((s.protocol||"—")+" · "+(s.transport||"—")+" · "+(s.security||"—"))+'"><b>'+esc(s.protocol||"—")+'</b><small class="protocol-sub">'+esc((s.transport||"—")+" / "+(s.security||"—"))+'</small></td>';if(col==="latency")return '<td data-col="latency">'+num(latest.latency_ms,0)+' ms</td>';if(col==="speed")return '<td data-col="speed"><b>'+num(latest.download_mbps,0)+'</b> Мбит/с</td>';if(col==="availability")return '<td data-col="availability">'+num(latest.availability,1)+'%</td>';return '<td data-col="status">'+badge(s.active?"Онлайн":"Неактивен",s.active?"good":"bad")+'</td>'}
function serverRows(){var cols=serverColumnOrder();return filteredServers().map(function(s){return '<tr class="clickable" onclick="openServer(&quot;'+s.id+'&quot;)">'+cols.map(function(col){return serverCell(s,col)}).join("")+'</tr>'}).join("")}
function serverHeaders(){var labels={provider:"Провайдер",server:"Сервер",country:"Страна",protocol:"Протокол",latency:"Задержка",speed:"Скорость",availability:"Доступность",status:"Статус"};return serverColumnOrder().map(function(col){return '<th data-col="'+col+'" draggable="true">'+labels[col]+'<span class="drag-handle">⋮⋮</span></th>'}).join("")}
function bindColumnDnD(){var table=document.querySelector(".server-table");if(!table)return;var dragged=null;table.querySelectorAll("th[draggable]").forEach(function(th){th.addEventListener("dragstart",function(){dragged=th.dataset.col;th.classList.add("dragging")});th.addEventListener("dragend",function(){th.classList.remove("dragging")});th.addEventListener("dragover",function(e){e.preventDefault()});th.addEventListener("drop",function(e){e.preventDefault();var target=th.dataset.col;if(!dragged||dragged===target)return;var cols=serverColumnOrder(),from=cols.indexOf(dragged),to=cols.indexOf(target);cols.splice(from,1);cols.splice(to,0,dragged);localStorage.setItem(SERVER_COLUMNS_KEY,JSON.stringify(cols));servers()})})}
function servers(){var ps=state.servers.map(function(s){return s.provider||""}),countries=state.servers.map(countryOf),protocols=state.servers.map(function(s){return s.protocol||""}),f=state.serverFilters,rows=filteredServers();app.innerHTML=head("Серверы","Все серверы от подключенных провайдеров")+'<div class="filter-toolbar"><div class="filter-item"><span>Провайдер</span><select class="input" onchange="updateServerFilter(&quot;provider&quot;,this.value)"><option value="">Все провайдеры</option>'+filterOptions(ps,f.provider)+'</select></div><div class="filter-item"><span>Страна</span><select class="input" onchange="updateServerFilter(&quot;country&quot;,this.value)"><option value="">Все страны</option>'+filterOptions(countries,f.country)+'</select></div><div class="filter-item"><span>Протокол</span><select class="input" onchange="updateServerFilter(&quot;protocol&quot;,this.value)"><option value="">Все протоколы</option>'+filterOptions(protocols,f.protocol)+'</select></div><div class="filter-item"><span>Статус</span><select class="input" onchange="updateServerFilter(&quot;status&quot;,this.value)"><option value="">Все статусы</option><option value="online" '+(f.status==="online"?"selected":"")+'>Онлайн</option><option value="offline" '+(f.status==="offline"?"selected":"")+'>Неактивен</option></select></div><div class="filter-item search-filter"><span>Поиск</span><div class="input-with-action"><input class="input" value="'+esc(f.search)+'" oninput="state.serverFilters.search=this.value;filterServerTable()" placeholder="Название сервера">'+icon("search")+'</div></div></div><div class="filter-row"><div class="regex-box"><span>'+icon("filter")+'</span><div><b>Исключающие regex-фильтры</b><small>Например, <code>LTE</code> исключит серверы с LTE в названии.</small></div>'+filterHtml()+'</div></div><section class="card table-card"><div class="table-card-top"><div><b>'+rows.length+'</b><span> серверов отображается</span></div><span class="muted">Перетаскивайте заголовки, чтобы менять порядок столбцов</span></div><div class="table-scroll"><table class="table server-table"><thead><tr>'+serverHeaders()+'</tr></thead><tbody>'+(serverRows()||'<tr><td colspan="'+serverColumnOrder().length+'" class="empty">По фильтрам ничего не найдено</td></tr>')+'</tbody></table></div></section>';bindColumnDnD()}
function filterServerTable(){var table=document.querySelector(".server-table");if(!table)return;var rows=filteredServers(),body=table.querySelector("tbody");body.innerHTML=rows.map(function(s){return '<tr class="clickable" onclick="openServer(&quot;'+s.id+'&quot;)">'+serverColumnOrder().map(function(col){return serverCell(s,col)}).join("")+'</tr>'}).join("")||'<tr><td colspan="'+serverColumnOrder().length+'" class="empty">По фильтрам ничего не найдено</td></tr>'}
function filterHtml(){return '<div class="filter-list">'+state.filters.map(function(v,i){return '<div class="filter"><input class="input" value="'+esc(v)+'" placeholder="Например: LTE" title="Regex-фильтр: найденные серверы будут исключены" oninput="state.filters['+i+']=this.value" onchange="state.filters['+i+']=this.value;render()"><button class="icon-btn" onclick="removeFilter('+i+')" title="Удалить фильтр">×</button></div>'}).join("")+'<button class="btn tiny secondary" onclick="addFilter()">+ Добавить фильтр</button></div>}
function addFilter(){state.filters.push("");render()}
function removeFilter(i){if(state.filters.length===1){state.filters[0]="";render();return}state.filters.splice(i,1);render()}
function toggle(id,on){if(on)state.selected[id]=true;else delete state.selected[id];render()}
function selectAllFiltered(on){filteredServers().forEach(function(s){if(on)state.selected[s.id]=true;else delete state.selected[s.id]});render()}
async function openServer(id){state.serverDetail=await api("/api/v1/servers/"+id);serverDetail()}
function metric(label,value,unit,kind,tip){return '<div class="metric" title="'+esc(tip||label)+'"><span class="metric-icon '+(kind||"blue")+'">'+icon("analytics")+'</span><div><small>'+esc(label)+'</small><b>'+value+(unit?" <em>"+unit+"</em>":"")+'</b></div></div>'}
function resultStatus(v){return v===true?'<span class="ok">Доступен</span>':v===false?'<span class="err">Недоступен</span>':'—'}
function serverDetail(){
  var s=state.serverDetail;if(!s)return;var rs=s.results||[],latest=rs[0]||{},name=esc(displayServerName(s.name));
  var speedData=rs.slice().reverse().map(function(r){return {download_mbps:r.download_mbps,upload_mbps:r.upload_mbps}});
  var lossData=rs.slice().reverse().map(function(r){return {download_mbps:r.latency_ms,upload_mbps:r.packet_loss_percent}});
  var tips={latency:"Среднее время отклика сервера.",download:"Скорость загрузки.",upload:"Скорость отдачи.",loss:"Доля потерянных пакетов.",jitter:"Разброс задержки между измерениями.",dns:"Результат DNS-проверки.",http:"Результат HTTP-проверки."};
  app.innerHTML='<div class="detail-top"><button class="back-btn" onclick="state.page=\'servers\';render()">'+icon("back")+'Серверы</button><div class="detail-title"><span class="detail-flag">'+flag(s.name)+'</span><div><h1>'+name+'</h1><p>'+esc(s.provider)+' · '+esc(s.protocol||"—")+' · '+esc(s.transport||"—")+' · '+esc(s.security||"—")+'</p></div></div><div class="head-actions"><button class="btn" onclick="state.selected={};state.selected[\''+s.id+'\']=true;state.page=\'tests\';render()">Запустить тест</button></div></div>'+
  '<div class="tabs"><button class="active">Обзор</button><button>Графики</button><button>История тестов</button><button>Технические данные</button><button>Логи</button></div>'+
  '<div class="detail-grid"><section class="card metrics-card"><div class="card-head"><div><h3>Текущие показатели</h3><p>Последнее измерение</p></div>'+badge(s.active?"Онлайн":"Неактивен",s.active?"good":"bad")+'</div>'+
  metric("Задержка",num(latest.latency_ms,0),"ms","blue",tips.latency)+metric("Скорость загрузки",num(latest.download_mbps,0),"Мбит/с","cyan",tips.download)+metric("Скорость отдачи",num(latest.upload_mbps,0),"Мбит/с","green",tips.upload)+metric("Потери пакетов",num(latest.packet_loss_percent,1),"%","red",tips.loss)+metric("Стабильность",latest.success==null?"—":latest.success?"Стабильно":"Ошибка","",latest.success?"green":"red","Устойчивость результата тестирования.")+metric("Jitter",num(latest.jitter_ms,0),"ms","violet",tips.jitter)+metric("DNS",resultStatus(latest.dns_ok),"","blue",tips.dns)+metric("HTTP",resultStatus(latest.http_ok),"","cyan",tips.http)+
  '<div class="service-list"><span>'+statusDot((latest.details||{}).youtube_ok)+'YouTube <b>'+resultStatus((latest.details||{}).youtube_ok)+'</b></span><span>'+statusDot((latest.details||{}).telegram_ok)+'Telegram <b>'+resultStatus((latest.details||{}).telegram_ok)+'</b></span><span>'+statusDot((latest.details||{}).github_ok)+'GitHub <b>'+resultStatus((latest.details||{}).github_ok)+'</b></span></div></section>'+
  '<div><section class="card chart-card"><div class="card-head"><div><h3>Скорость</h3><p>Последние измерения</p></div><div class="chart-legend"><span><i class="legend-dot blue-dot"></i>Загрузка</span><span><i class="legend-dot green-dot"></i>Отдача</span></div></div>'+dashboardChart(speedData,700,230)+'</section><section class="card chart-card" style="margin-top:14px"><div class="card-head"><div><h3>Задержка и потери пакетов</h3><p>Последние измерения</p></div></div>'+dashboardChart(lossData,700,190)+'</section></div></div>'
}

function setAnalyticsMetric(metric){state.analyticsMetric=metric;render()}
async function analytics(){
  var metric=state.analyticsMetric,period=state.analyticsPeriod,labels={speed:"Скорость",latency:"Задержка",loss:"Потери пакетов",availability:"Доступность",sites:"Сайты"};
  var rows=await api("/api/v1/analytics")||[];
  var selected=state.analyticsSelected.filter(function(id){return rows.some(function(r){return r.id===id})}).slice(0,5);state.analyticsSelected=selected;
  function value(r){if(metric==="speed")return {a:r.download_mbps,b:r.upload_mbps,unit:"Мбит/с",second:"Upload"};if(metric==="latency")return {a:r.latency_ms,b:r.jitter_ms,unit:"ms",second:"Jitter"};if(metric==="loss")return {a:r.packet_loss_percent,b:null,unit:"%",second:""};if(metric==="availability")return {a:r.availability,b:null,unit:"%",second:""};return {a:r.samples,b:null,unit:"проверок",second:""}}
  var options=rows.map(function(r){return '<option value="'+esc(r.id)+'" '+(selected.indexOf(r.id)>=0?"selected":"")+'>'+esc(r.provider)+" · "+esc(r.name)+'</option>'}).join("");
  var data=selected.length?selected.map(function(id){return rows.find(function(r){return r.id===id})}).filter(Boolean):rows.slice(0,8);
  var max=1;data.forEach(function(r){var v=value(r).a;if(v!=null)max=Math.max(max,Number(v)||0)});
  var bars=data.map(function(r){var v=value(r),pct=v.a==null?0:Math.max(4,Math.round(Number(v.a)/max*100));return '<div class="metric-bar"><div><span>'+esc(r.name)+'</span><b>'+num(v.a,metric==="loss"||metric==="availability"?1:0)+(v.unit?" "+v.unit:"")+'</b></div><div class="bar-track"><i style="width:'+pct+'%"></i></div></div>'}).join("");
  var cards=selected.map(function(id){var r=rows.find(function(x){return x.id===id})||{},v=value(r);return '<div class="compare-metric"><b>'+esc(r.name||"—")+'</b><div class="compare-value"><span>'+labels[metric]+'</span><strong>'+num(v.a,1)+(v.unit?" "+v.unit:"")+'</strong></div>'+(v.b!=null?'<div class="compare-value"><span>'+esc(v.second)+'</span><strong>'+num(v.b,1)+' ms</strong></div>':"")+'</div>'}).join("");
  var table=selected.map(function(id){var r=rows.find(function(x){return x.id===id})||{};return '<tr><td>'+esc(r.provider)+'</td><td>'+esc(r.name)+'</td><td>'+num(r.download_mbps,0)+'</td><td>'+num(r.upload_mbps,0)+'</td><td>'+num(r.latency_ms,1)+'</td><td>'+num(r.jitter_ms,1)+'</td><td>'+num(r.packet_loss_percent,2)+'</td><td>'+num(r.availability,1)+'%</td></tr>'}).join("");
  var tabs=Object.keys(labels).map(function(k){return '<button class="'+(metric===k?"active":"")+'" onclick="setAnalyticsMetric(&quot;'+k+'&quot;)">'+labels[k]+'</button>'}).join("");
  app.innerHTML=head("Графики / Сравнение","История показателей и сопоставление серверов")+
  '<section class="card analytics-card"><div class="analytics-toolbar"><label>Метрика<select class="input" onchange="setAnalyticsMetric(this.value)">'+Object.keys(labels).map(function(k){return '<option value="'+k+'" '+(metric===k?"selected":"")+'>'+labels[k]+'</option>'}).join("")+'</select></label><label>Период<select class="input" onchange="state.analyticsPeriod=this.value;render()"><option value="24h" '+(period==="24h"?"selected":"")+' >24 часа</option><option value="7d" '+(period==="7d"?"selected":"")+' >7 дней</option><option value="30d" '+(period==="30d"?"selected":"")+' >30 дней</option></select></label><label>Серверы <select class="input" multiple size="1" onchange="state.analyticsSelected=Array.from(this.selectedOptions).map(function(o){return o.value}).slice(0,5);render()">'+options+'</select></label></div><div class="analytics-tabs">'+tabs+'</div>'+
  '<div class="chart-placeholder"><div class="placeholder-grid"></div><div class="metric-bars">'+(bars||'<div class="empty">Недостаточно данных для графика</div>')+'</div></div>'+
  '<div class="compare-grid">'+(cards||'<div class="empty-chip">Выберите до 5 серверов для сравнения</div>')+'</div>'+
  '<div class="table-scroll"><table class="table analytics-table"><thead><tr><th>Провайдер</th><th>Сервер</th><th>Download</th><th>Upload</th><th>Ping</th><th>Jitter</th><th>Loss</th><th>Доступность</th></tr></thead><tbody>'+(table||'<tr><td colspan="8" class="empty">Выберите серверы</td></tr>')+'</tbody></table></div></section>'
}

function setMode(mode){state.mode=mode;render()}
function toggleProvider(providerId,on){var p=state.providers.find(function(x){return x.id===providerId});if(!p)return;state.servers.filter(function(s){return s.provider_id===p.id||s.provider===p.name}).forEach(function(s){toggle(s.id,on)});render()}
function clearSelection(){state.selected={};render()}

function tests(){
  var count=Object.keys(state.selected).length,screen=state.screening;
  var groups=state.providers.map(function(p){
    var ss=state.servers.filter(function(s){return (s.provider_id===p.id||s.provider===p.name)&&matchesRegexFilters(s)});if(!ss.length)return "";
    var selectedCount=ss.filter(function(s){return state.selected[s.id]}).length,all=selectedCount===ss.length;
    var ch='<div class="providerline"><label class="provider-check"><input type="checkbox" '+(all?"checked":"")+' onchange="toggleProvider(&quot;'+p.id+'&quot;,this.checked)"><b>'+esc(p.display_name||p.name)+'</b><span>'+selectedCount+'/'+ss.length+'</span></label></div>';
    ss.forEach(function(s){var f=flag(s.name),nm=displayServerName(s.name);ch+='<label class="serverline"><input type="checkbox" '+(state.selected[s.id]?"checked":"")+' onchange="toggle(&quot;'+s.id+'&quot;,this.checked)"><span class="serverline-name">'+(f?f+" ":"")+esc(nm)+'</span><span class="server-tags"><b>'+esc(s.protocol||"—")+'</b><small>'+esc((s.transport||"—")+" / "+(s.security||"—"))+'</small></span></label>'});
    return ch;
  }).join("");
  var running=screen&&["running","stopping"].indexOf(screen.status)>=0;
  app.innerHTML=head("Тесты","Выберите серверы и запустите полную проверку")+
  '<div class="test-summary"><div><b>'+count+'</b><span>серверов выбрано</span></div><button class="btn secondary" onclick="clearSelection()">Сбросить выбор</button></div>'+
  '<div class="test-grid"><section class="card selection-card"><div class="card-head"><div><h3>Серверы</h3><p>Выбор по провайдеру или отдельно</p></div></div>'+filterHtml()+'<div class="checktree">'+(groups||'<div class="empty">Добавьте провайдеров</div>')+'</div></section>'+
  '<section class="card campaign-card"><div class="card-head"><div><h3>Кампания тестирования</h3><p>Скрининг и полный тест собраны в одном рабочем блоке.</p></div>'+badge(running?"Скрининг выполняется":"Готово",running?"warn":"neutral")+'</div>'+
  '<div class="campaign-section"><div class="section-title"><b>Скрининг</b><span>Необязательно</span></div><label class="screening-toggle"><input id="screeningEnabled" type="checkbox" '+(state.screeningEnabled?"checked":"")+' onchange="state.screeningEnabled=this.checked"><span>Перед полным тестом отсеять нестабильные серверы</span></label><details class="screening-advanced"><summary>Расширенные параметры</summary><div class="form-grid compact"><label>1-й проход<input id="s1" class="input" type="number" min="1" value="'+state.screeningFirst+'"><small>секунд на сервер</small></label><label>Повтор<input id="s2" class="input" type="number" min="1" value="'+state.screeningSecond+'"><small>секунд на сервер</small></label><label>Повторов<input id="sr" class="input" type="number" min="1" value="'+state.screeningRepeats+'"><small>максимум 3</small></label><label>Лимит<input id="sm" class="input" type="number" min="1" placeholder="без лимита" value="'+esc(state.screeningMax)+'"><small>серверов в shortlist</small></label></div></details><div id="screening-status">Загрузка…</div></div>'+
  '<div class="campaign-section"><div class="section-title"><b>Продолжительность</b><span>Общее время кампании</span></div><div class="duration-row"><input id="dur" class="input" type="number" min="1" value="'+Math.max(1,Math.round(state.duration/60))+'"><select id="unit" class="input"><option value="60">минут</option><option value="3600">часов</option><option value="86400">дней</option><option value="604800">недель</option><option value="2592000">месяцев</option></select></div><div class="mode-grid"><div class="mode '+(state.mode==="equal_time"?"selected":"")+'" onclick="setMode('equal_time')"><span class="mode-radio"></span><div><b>Равное время</b><p>Общее время делится между выбранными серверами.</p><strong>'+(count?fmt(state.duration/count):"—")+'</strong><small>на сервер</small></div></div><div class="mode '+(state.mode==="sequential"?"selected":"")+'" onclick="setMode('sequential')"><span class="mode-radio"></span><div><b>Последовательно</b><p>Каждый сервер получает полный интервал по очереди.</p><strong>'+fmt(state.duration)+'</strong><small>на сервер</small></div></div></div></div>'+
  '<div class="campaign-section"><div class="section-title"><b>Текущий тест</b><span>'+count+' серверов</span></div><div id="test-status">Загрузка…</div><button class="btn wide campaign-start" onclick="startTest()" '+(running?"disabled":"")+'>'+icon("tests")+(running?"Выполняется…":"Запустить тест")+'</button></div></section></div>';
  document.getElementById("dur").onchange=function(){state.duration=Number(this.value)*Number(document.getElementById("unit").value);render()};
  document.getElementById("unit").onchange=function(){state.duration=Number(document.getElementById("dur").value)*Number(this.value);render()};
  loadStatus();loadScreening();
}
async function startTest(){var ids=Object.keys(state.selected);if(!ids.length){showToast("Выберите хотя бы один сервер","error");return}if(state.screeningEnabled){state.screeningAutoStart=true;await startScreening();return}try{await api("/api/v1/tests",{method:"POST",body:JSON.stringify({server_ids:ids,duration_seconds:state.duration,scheduling_mode:state.mode})});showToast("Тест запущен","success");loadStatus()}catch(e){showToast(e.message,"error")}}
async function loadStatus(){try{var t=await api("/api/v1/tests/latest"),el=document.getElementById("test-status");if(!el)return;el.innerHTML=summary(t)+(t.status==="running"||t.status==="stopping"?'<button class="btn danger tiny" onclick="stopTest(&quot;'+t.run_id+'&quot;)">Остановить тест</button>':"");if(t.status==="running"||t.status==="stopping")setTimeout(loadStatus,1000)}catch(_){ }}
async function stopTest(id){try{await api("/api/v1/tests/"+id+"/stop",{method:"POST"});showToast("Остановка теста запрошена","success");loadStatus()}catch(e){showToast(e.message,"error")}}
async function startScreening(){var ids=Object.keys(state.selected);if(!ids.length){showToast("Выберите серверы для скрининга","error");return}state.screeningFirst=Number(document.getElementById("s1").value)||30;state.screeningSecond=Number(document.getElementById("s2").value)||30;state.screeningRepeats=Number(document.getElementById("sr").value)||2;state.screeningMax=document.getElementById("sm").value;try{var r=await api("/api/v1/screening",{method:"POST",body:JSON.stringify({server_ids:ids,first_pass_seconds:state.screeningFirst,second_pass_seconds:state.screeningSecond,repeat_passes:state.screeningRepeats,max_shortlist:state.screeningMax?Number(state.screeningMax):null})});state.screening=r;loadScreening()}catch(e){showToast(e.message,"error")}}
async function loadScreening(){var el=document.getElementById("screening-status");if(!el)return;try{var r=await api("/api/v1/screening/latest");state.screening=r;if(!r||!r.status){el.innerHTML='<span class="muted">Скрининг ещё не запускался.</span>';return}var running=["running","stopping"].indexOf(r.status)>=0;var text=r.status==="running"?"Выполняется":r.status==="completed"?"Завершён":r.status==="stopping"?"Останавливается":"Остановлен";var action=running?'<button class="btn danger tiny" onclick="stopScreening(&quot;'+r.run_id+'&quot;)">Остановить</button>':r.status==="completed"?'<button class="btn tiny" onclick="startFullFromScreening(&quot;'+r.run_id+'&quot;)">Запустить полный тест shortlist</button>':"";var current=r.current_server_name?(" · "+r.current_server_name):"";var progress=r.progress!=null?(" · "+num(r.progress,0)+"%"):"";var shortlistNames=(r.shortlist||[]).map(function(id){var s=state.servers.find(function(x){return x.id===id});return s?displayServerName(s.name):id}).slice(0,5);el.innerHTML='<div class="screening-result">'+badge(text,running?"warn":r.status==="completed"?"good":"bad")+' <span>'+esc(r.message||"")+esc(current)+esc(progress)+'</span>'+(r.total_servers!=null?'<small>'+r.total_servers+' серверов · обработано: '+(r.completed_servers||0)+' · shortlist: '+(r.shortlist_count!=null?r.shortlist_count:(r.shortlisted_servers||0))+(shortlistNames.length?' · '+esc(shortlistNames.join(", ")): "")+'</small>':"")+action+'</div>';if(running)setTimeout(loadScreening,1000);if(r.status==="completed"&&state.screeningAutoStart){state.screeningAutoStart=false;startFullFromScreening(r.run_id)}}catch(e){el.innerHTML='<span class="muted">'+esc(e.message||"Скрининг недоступен.")+'</span>'}}
async function stopScreening(id){try{await api("/api/v1/screening/"+id+"/stop",{method:"POST"});loadScreening()}catch(e){showToast(e.message,"error")}}
async function startFullFromScreening(id){try{await api("/api/v1/screening/"+id+"/start-test",{method:"POST",body:JSON.stringify({duration_seconds:state.duration,scheduling_mode:state.mode})});showToast("Полный тест shortlist запущен","success");loadStatus()}catch(e){showToast(e.message,"error")}}

async function logs(level){level=level||"all";try{var rows=await api("/api/v1/logs?level="+encodeURIComponent(level)+"&limit=100")||[];var body=rows.map(function(r){return '<div class="log-row"><time>'+esc(r.created_at)+'</time><b class="log-'+String(r.level).toLowerCase()+'">'+esc(r.level)+'</b><span>'+esc(r.message)+'</span></div>'}).join("");app.innerHTML=head("Логи","Системные события, тесты и ошибки",'<div class="head-actions"><select class="input small" onchange="logs(this.value)"><option value="all" '+(level==="all"?"selected":"")+' >Все уровни</option><option value="INFO" '+(level==="INFO"?"selected":"")+'>INFO</option><option value="WARN" '+(level==="WARN"?"selected":"")+'>WARN</option><option value="ERROR" '+(level==="ERROR"?"selected":"")+'>ERROR</option></select></div>')+'<section class="card log-card"><div class="log-toolbar"><span>'+rows.length+' событий</span><span class="muted">Последние 100 записей</span></div>'+(body||'<div class="empty">Системных событий пока нет</div>')+'</section>'}catch(e){app.innerHTML=head("Логи","Системные события, тесты и ошибки")+'<section class="card"><p>'+esc(e.message)+'</p></section>'}}
function settings(){
  app.innerHTML=head("Настройки","Основные параметры VPN-Bench")+
  '<div class="settings-layout"><aside class="settings-nav"><button class="active">Основные</button><button>Безопасность</button><button>Система</button></aside><div class="settings-content">'+
  '<section class="card form-card"><div class="card-head"><div><h3>Основные</h3><p>Параметры фоновой работы и хранения результатов</p></div></div>'+
  '<div class="setting-row"><span><b>Параллельные тесты</b><small>Количество одновременно запускаемых проверок</small></span><input class="input short" value="1"></div>'+
  '<div class="setting-row"><span><b>Автообновление подписок</b><small>Автоматически обновлять данные провайдеров</small></span><input type="checkbox" checked></div>'+
  '<div class="setting-row"><span><b>Сохранять историю</b><small>Хранить результаты измерений</small></span><input type="checkbox" checked></div>'+
  '<div class="setting-row"><span><b>Срок хранения</b><small>Удаление старых измерений</small></span><select class="input short"><option>30 дней</option><option>90 дней</option><option>180 дней</option><option>365 дней</option></select></div>'+
  '<div class="setting-row"><span><b>Использовать IPv6</b><small>Разрешить IPv6 для проверок</small></span><input type="checkbox"></div>'+
  '<div class="form-actions"><button class="btn">Сохранить настройки</button></div></section>'+
  '<section class="card form-card"><div class="card-head"><div><h3>Безопасность</h3><p>Доступ к панели и защита учетной записи администратора</p></div></div><div class="security-row"><span class="info-badge">'+icon("lock")+'</span><div><b>Пароль администратора</b><small>Пароль хранится в виде защищённого хэша.</small></div><button class="btn secondary" onclick="changePassword()">Изменить пароль</button></div></section>'+
  '<section class="card form-card"><div class="card-head"><div><h3>Система</h3><p>Версия, обновления и состояние сервиса</p></div></div><div class="system-version"><img src="/static/Favicon.svg"><div><b>VPN-Bench</b><small>Текущая версия 0.2.0</small></div><span class="badge neutral">Установлена</span></div><div class="form-actions"><button class="btn secondary" onclick="checkUpdates()">Проверить обновления</button><button class="btn secondary" onclick="restartService()">Перезапустить сервис</button></div></section></div></div>'
}
async function changePassword(){var a=prompt("Текущий пароль"),b=prompt("Новый пароль (минимум 12 символов)");if(!a||!b)return;try{await api("/api/v1/auth/change-password",{method:"POST",body:JSON.stringify({current_password:a,new_password:b})});alert("Пароль изменён")}catch(e){alert(e.message)}}
async function checkUpdates(){try{var r=await api("/api/v1/system/update-check");showToast(r.message||"Проверка завершена","success")}catch(e){showToast(e.message||"Проверка обновлений недоступна","error")}}
async function restartService(){if(!confirm("Перезапустить VPN-Bench?"))return;try{await api("/api/v1/system/restart",{method:"POST"});showToast("Сервис перезапускается…","success")}catch(e){showToast(e.message||"Не удалось перезапустить сервис","error")}}
function startApp(){nav();boot()}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",startApp,{once:true});else startApp();
