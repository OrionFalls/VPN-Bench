from fastapi.responses import HTMLResponse

HTML = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>VPN-Bench</title>
<style>
:root{font-family:Inter,system-ui,sans-serif;color:#172033;background:#f5f7fb}*{box-sizing:border-box}body{margin:0}
.shell{display:flex;min-height:100vh}.side{width:225px;background:#172033;color:#dce4f2;padding:22px 14px;position:fixed;inset:0 auto 0 0}
.brand{font-weight:800;font-size:18px;padding:0 12px 28px}.brand b{color:#4b8cff}.nav button{display:block;width:100%;border:0;background:transparent;color:#b8c3d7;text-align:left;padding:11px 12px;border-radius:9px;margin:3px 0;cursor:pointer;font-size:14px}.nav button.active,.nav button:hover{background:#263653;color:white}.bottom{position:absolute;bottom:20px;left:14px;color:#8290a8;font-size:12px}
.main{margin-left:225px;width:calc(100% - 225px);padding:30px;max-width:1500px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}.top h1{margin:0 0 5px;font-size:28px}.muted{color:#758198;font-size:13px}
.card{background:white;border:1px solid #e4e8f0;border-radius:14px;padding:18px;box-shadow:0 4px 18px rgba(22,32,51,.04)}.grid{display:grid;gap:16px}.stats{grid-template-columns:repeat(4,1fr)}
.stat strong{display:block;font-size:28px;margin-top:8px}.row{display:grid;grid-template-columns:1.5fr 1fr;gap:16px;margin-top:16px}
.progress{height:10px;background:#e9edf5;border-radius:10px;overflow:hidden}.bar{height:100%;background:#3478f6;border-radius:10px}
.btn{border:0;background:#246df3;color:white;padding:10px 16px;border-radius:9px;font-weight:650;cursor:pointer}.btn.secondary{background:#eef3fb;color:#315078}.btn.danger{background:#e5484d}
.input,select{width:100%;border:1px solid #d4dbe7;border-radius:9px;padding:10px 12px;background:white;font:inherit}.table{width:100%;border-collapse:collapse;font-size:13px}.table th,.table td{text-align:left;padding:11px 8px;border-bottom:1px solid #edf0f5}.pill{display:inline-block;padding:4px 8px;border-radius:99px;background:#edf7ef;color:#238447;font-size:11px}.empty{padding:35px;text-align:center;color:#8490a4}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:14px}.mode{border:2px solid #e2e7ef;border-radius:13px;padding:16px;cursor:pointer}.mode.selected{border-color:#3478f6;background:#f6f9ff}
.checktree{max-height:420px;overflow:auto;border:1px solid #e2e7ef;border-radius:10px;padding:10px}.providerline{font-weight:700;padding:9px 5px}.serverline{padding:6px 5px 6px 22px}.filter{display:flex;gap:8px;margin:7px 0}.filter input{flex:1}
@media(max-width:900px){.side{width:68px}.brand{font-size:0}.brand b{font-size:18px}.nav button{font-size:0;text-align:center}.main{margin-left:68px;width:calc(100% - 68px);padding:18px}.stats,.cards,.row{grid-template-columns:1fr}}
</style></head>
<div class="shell"><aside class="side"><div class="brand">◉ <b>VPN-Bench</b></div><nav class="nav">
<button data-page="dashboard" class="active">⌂ &nbsp; Дашборд</button><button data-page="providers">◉ &nbsp; Провайдеры</button><button data-page="servers">◌ &nbsp; Серверы</button><button data-page="tests">▶ &nbsp; Тесты</button><button data-page="analytics">▥ &nbsp; Аналитика</button><button data-page="logs">≡ &nbsp; Логи</button><button data-page="settings">⚙ &nbsp; Настройки</button>
</nav><div class="bottom">v0.2.0</div></aside><main class="main"><div id="app"></div></main></div>
<script src="/static/app.js" defer></script>
</body></html>"""

def page() -> HTMLResponse:
    return HTMLResponse(HTML)
