from fastapi.responses import HTMLResponse

HTML = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#f5f7fb">
<title>VPN-Bench</title>
<link rel="stylesheet" href="/static/app.css?v=6">
</head>
<body>
<div class="shell">
  <aside class="side">
    <div class="brand"><span class="brand-mark">◉</span><span class="brand-name">VPN-Bench</span></div>
    <nav class="nav" aria-label="Основная навигация">
      <button data-page="dashboard" class="active"><span class="nav-icon">⌂</span><span>Дашборд</span></button>
      <button data-page="providers"><span class="nav-icon">◉</span><span>Провайдеры</span></button>
      <button data-page="servers"><span class="nav-icon">◌</span><span>Серверы</span></button>
      <button data-page="tests"><span class="nav-icon">▶</span><span>Тесты</span></button>
      <button data-page="analytics"><span class="nav-icon">▥</span><span>Графики</span></button>\n      <button data-page="comparison"><span class="nav-icon">◫</span><span>Сравнение</span></button>
      <button data-page="logs"><span class="nav-icon">≡</span><span>Логи</span></button>
      <button data-page="settings"><span class="nav-icon">⚙</span><span>Настройки</span></button>
    </nav>
    <div class="bottom">v0.2.0</div>
  </aside>
  <main class="main">
    <div id="app"></div>
  </main>
</div>
<script src="/static/app.js?v=6" defer></script>
</body>
</html>"""

def page() -> HTMLResponse:
    return HTMLResponse(HTML)
