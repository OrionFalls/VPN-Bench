from fastapi.responses import HTMLResponse

ICON_DASHBOARD = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M19.842 8.29901L13.842 3.63201C12.759 2.78901 11.242 2.78901 10.158 3.63201L4.158 8.29901C3.427 8.86701 3 9.74101 3 10.667V18C3 19.657 4.343 21 6 21H18C19.657 21 21 19.657 21 18V10.667C21 9.74101 20.573 8.86701 19.842 8.29901Z" stroke="#3D84FF" stroke-width="1.5"/><path d="M14.121 11.379C15.293 12.551 15.293 14.45 14.121 15.622C12.949 16.794 11.05 16.794 9.87802 15.622C8.70602 14.45 8.70602 12.551 9.87802 11.379C11.05 10.207 12.95 10.207 14.121 11.379Z" stroke="#3D84FF" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ICON_PROVIDERS = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M13.75 20H20M4 20H10.25M12 18.25C12.966 18.25 13.75 19.033 13.75 20C13.75 20.966 12.967 21.75 12 21.75C11.034 21.75 10.25 20.967 10.25 20C10.25 19.034 11.034 18.25 12 18.25ZM12.002 3C9.18398 3 6.90098 5.283 6.90098 8.101C5.02298 8.101 3.50098 9.623 3.50098 11.501C3.50098 13.379 5.02298 14.901 6.90098 14.901H16.25C18.597 14.901 20.5 12.998 20.5 10.651C20.5 8.501 18.897 6.742 16.824 6.459C16.141 4.448 14.241 3 12.002 3Z" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 14.901V18.25" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ICON_SERVERS = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8.97998V5.49998M13.5 4H20M4 4H10.5M6.5 18.5V17.5M9.5 18.5V17.5M12.5 18H18M6.5 12.5V11.5M9.5 12.5V11.5M12.5 12H18M19.5 15H4.5C3.67157 15 3 14.3284 3 13.5V10.5C3 9.67157 3.67157 9 4.5 9H19.5C20.3284 9 21 9.67157 21 10.5V13.5C21 14.3284 20.3284 15 19.5 15ZM19.5 21H4.5C3.67157 21 3 20.3284 3 19.5V16.5C3 15.6716 3.67157 15 4.5 15H19.5C20.3284 15 21 15.6716 21 16.5V19.5C21 20.3284 20.3284 21 19.5 21ZM12 2.5C12.8284 2.5 13.5 3.17157 13.5 4C13.5 4.82843 12.8284 5.5 12 5.5C11.1716 5.5 10.5 4.82843 10.5 4C10.5 3.17157 11.1716 2.5 12 2.5Z" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ICON_TESTS = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M4.67004 17.209C5.25413 18.0291 5.97097 18.7459 6.79104 19.33M3.13501 10.5C2.955 11.4919 2.955 12.5081 3.13501 13.5M4.67004 6.79101C5.25383 5.9704 5.97071 5.25318 6.79104 4.66901M10.5 20.865C15.396 21.7227 20.0603 18.449 20.918 13.553C21.7757 8.657 18.502 3.9927 13.606 3.135C12.5785 2.955 11.5275 2.955 10.5 3.135M14.512 10.707L11.373 13.846L9.48596 11.965" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ICON_ANALYTICS = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12V20M14.7001 14.67V20M4 17V20M9.30005 13.6V20M15.9395 8.50854C16.6229 9.19195 16.6229 10.3 15.9395 10.9834C15.256 11.6668 14.148 11.6668 13.4646 10.9834C12.7812 10.3 12.7812 9.19195 13.4646 8.50854C14.148 7.82512 15.256 7.82512 15.9395 8.50854ZM21.3424 4.00554C22.0258 4.68896 22.0258 5.797 21.3424 6.48041C20.659 7.16383 19.551 7.16383 18.8675 6.48041C18.1841 5.797 18.1841 4.68895 18.8675 4.00554C19.551 3.32213 20.659 3.32213 21.3424 4.00554ZM5.13245 11.8774C5.81587 11.194 5.81587 10.0859 5.13245 9.40252C4.44904 8.7191 3.341 8.7191 2.65758 9.40252C1.97417 10.0859 1.97417 11.194 2.65758 11.8774C3.34099 12.5608 4.44904 12.5608 5.13245 11.8774ZM10.5364 4.90056C11.2198 5.58398 11.2198 6.69202 10.5364 7.37543C9.85297 8.05885 8.74492 8.05885 8.06151 7.37543C7.3781 6.69202 7.3781 5.58397 8.06151 4.90056C8.74493 4.21715 9.85297 4.21715 10.5364 4.90056ZM18.77 6.35999L16.04 8.62999M13.24 8.77998L10.75 7.10999M5.23999 9.53001L7.95999 7.26001" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ICON_LOGS = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 12H17M17 3H7C4.79086 3 3 4.79086 3 7V17C3 19.2091 4.79086 21 7 21H17C19.2091 21 21 19.2091 21 17V7C21 4.79086 19.2091 3 17 3ZM7 16H17M7 8H12" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ICON_SETTINGS = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 15.5C13.933 15.5 15.5 13.933 15.5 12C15.5 10.067 13.933 8.5 12 8.5C10.067 8.5 8.5 10.067 8.5 12C8.5 13.933 10.067 15.5 12 15.5Z" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M16.3703 20.799L17.5125 20.1396C17.7637 19.9945 17.9675 19.7797 18.0992 19.5211C18.2308 19.2625 18.2846 18.9713 18.2541 18.6828L18.0692 16.9346C18.045 16.7055 18.094 16.4747 18.2092 16.2752L18.8766 15.1192C18.9917 14.9198 19.1671 14.7619 19.3776 14.6684L20.9145 13.9853C21.1797 13.8675 21.405 13.6753 21.5631 13.432C21.7212 13.1887 21.8053 12.9048 21.8053 12.6146V11.2958C21.8053 11.0057 21.7212 10.7218 21.5631 10.4785C21.405 10.2352 21.1797 10.043 20.9145 9.92512L19.3777 9.24212C19.1672 9.14857 18.9918 8.99075 18.8766 8.7913L18.2171 7.64909C18.102 7.44961 18.053 7.21877 18.0772 6.98972L18.2541 5.31721C18.2847 5.02866 18.2308 4.73745 18.0992 4.47888C17.9675 4.22031 17.7637 4.00546 17.5125 3.86039L16.3703 3.20101C16.119 3.05593 15.8311 2.98685 15.5413 3.00213C15.2516 3.01741 14.9725 3.1164 14.7378 3.28711L13.4701 4.20944C13.2838 4.34494 13.0594 4.41794 12.8291 4.41793H11.1707C10.9404 4.41793 10.7159 4.34494 10.5297 4.20944L9.26201 3.28707C9.02738 3.11637 8.74828 3.01739 8.45853 3.00211C8.16878 2.98684 7.88082 3.05593 7.62954 3.20101L6.48739 3.86043C6.23611 4.0055 6.03231 4.22034 5.90067 4.4789C5.76902 4.73747 5.7152 5.02867 5.74571 5.31721L5.92262 6.98973C5.94684 7.21877 5.89786 7.44961 5.78269 7.64908L5.05369 8.91167C4.93854 9.11112 4.76314 9.26895 4.55269 9.3625L3.08538 10.0146C2.82023 10.1325 2.59495 10.3247 2.43684 10.568C2.27873 10.8113 2.19458 11.0952 2.19458 11.3853V12.7042C2.19458 12.9943 2.27873 13.2783 2.43684 13.5215C2.59495 13.7648 2.82022 13.9571 3.08537 14.0749L4.69179 14.7889C4.90225 14.8824 5.07765 15.0403 5.19279 15.2398L5.79065 16.2753C5.9058 16.4748 5.95479 16.7056 5.93056 16.9346L5.74566 18.6829C5.71514 18.9714 5.76897 19.2626 5.90061 19.5212C6.03225 19.7797 6.23606 19.9946 6.48734 20.1397L7.6295 20.7991C7.88078 20.9442 8.16874 21.0132 8.4585 20.998C8.74825 20.9827 9.02734 20.8837 9.26197 20.713L10.6527 19.7012C10.839 19.5656 11.0634 19.4927 11.2937 19.4927H12.7061C12.9365 19.4927 13.1609 19.5656 13.3471 19.7012L14.7379 20.713C14.9725 20.8837 15.2516 20.9826 15.5413 20.9979C15.8311 21.0132 16.119 20.9441 16.3703 20.799Z" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'

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
<link rel="stylesheet" href="/static/app.css">
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
      <button data-page="analytics"><span class="nav-icon">{ICON_ANALYTICS}</span><span>Сравнение</span></button>
      <button data-page="logs"><span class="nav-icon">{ICON_LOGS}</span><span>Логи</span></button>
      <button data-page="settings"><span class="nav-icon">{ICON_SETTINGS}</span><span>Настройки</span></button>
    </nav>
    <div class="bottom" id="app-version"></div>
  </aside>
  <main class="main"><div id="app"></div></main>
</div>
<script src="/static/app.js" defer></script>
</body>
</html>"""

def page() -> HTMLResponse:
    return HTMLResponse(HTML)
