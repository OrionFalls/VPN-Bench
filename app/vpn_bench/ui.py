from fastapi.responses import HTMLResponse

ICON_DASHBOARD = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>'
ICON_PROVIDERS = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v18M3 8h18M5 8v8M19 8v8M8 16h8M8 12h8"/><circle cx="12" cy="8" r="2"/></svg>'
ICON_SERVERS = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="6" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><path d="M7 7h.01M7 17h.01"/></svg>'
ICON_TESTS = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>'
ICON_ANALYTICS = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19V9M9 19V5M14 19v-7M19 19V3M2 19h20"/></svg>'
ICON_LOGS = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>'
ICON_SETTINGS = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-1.8 1.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5v.1h-2.5v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1-1.8-1.8.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H6.6v-2.5h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1 1.8-1.8.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.5V4.6h2.5v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1 1.8 1.8-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.5 1h.1v2.5h-.1a1.7 1.7 0 0 0-1.5 1Z"/></svg>'

HTML = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#152034">
<meta name="description" content="VPN-Bench — тестирование и мониторинг VPN-серверов">
<link rel="icon" type="image/svg+xml" href="/static/Favicon.svg">
<link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
<link rel="mask-icon" href="/static/Favicon.svg" color="#3D84FF">
<title>VPN-Bench</title>
<link rel="stylesheet" href="/static/app_v2.css">
</head>
<body>
<div class="shell">
  <aside class="side">
    <div class="brand"><img src="/static/LOGO.svg" alt="VPN-Bench"></div>
    <nav class="nav" aria-label="Основная навигация">
      <button data-page="dashboard" class="active"><span class="nav-icon">{ICON_DASHBOARD}</span><span>Дашборд</span></button>
      <button data-page="providers"><span class="nav-icon">{ICON_PROVIDERS}</span><span>Провайдеры</span></button>
      <button data-page="servers"><span class="nav-icon">{ICON_SERVERS}</span><span>Серверы</span></button>
      <button data-page="tests"><span class="nav-icon">{ICON_TESTS}</span><span>Тесты</span></button>
      <button data-page="analytics"><span class="nav-icon">{ICON_ANALYTICS}</span><span>Графики</span></button>
      <button data-page="logs"><span class="nav-icon">{ICON_LOGS}</span><span>Логи</span></button>
      <button data-page="settings"><span class="nav-icon">{ICON_SETTINGS}</span><span>Настройки</span></button>
    </nav>
    <div class="bottom">v0.2.0</div>
  </aside>
  <main class="main"><div id="app"></div></main>
</div>
<script src="/static/app_v2.js" defer></script>
</body>
</html>"""

def page() -> HTMLResponse:
    return HTMLResponse(HTML)
