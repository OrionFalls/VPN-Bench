# ⚡ VPN-Bench

<div align="center">

<img src="assets/logo.svg" alt="VPN-Bench" width="190">

### Реальный бенчмарк VPN-серверов

**Импортируй подписки → быстро отсекай плохие узлы → тестируй лучшие → накапливай историю.**

[![CI](https://github.com/OrionFalls/VPN-Bench/actions/workflows/ci.yml/badge.svg)](https://github.com/OrionFalls/VPN-Bench/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue)](LICENSE)

🇷🇺 **Русский** · [🇬🇧 English](README.en.md)

</div>

> 🧪 **Статус:** active development. Архитектура и базовый runtime уже работают; методика измерений и аналитика продолжают развиваться.

---

## 🎯 Зачем это нужно?

Обычный speedtest отвечает на вопрос **«как быстро сейчас?»**.

VPN-Bench должен отвечать на более полезный вопрос:

> **«Как этот VPN-узел ведёт себя в реальной работе и как он ведёт себя через день, неделю и месяц?»**

Система не ограничивается ping до IP-адреса. Трафик тестируется через **реально поднятое VPN-соединение в изолированном network namespace**.

![VPN-Bench architecture](https://raw.githubusercontent.com/OrionFalls/VPN-Bench/main/assets/readme/architecture.svg)

---

## ✨ Что уже есть

| | Возможность |
|---|---|
| 🔐 | Авторизация и первоначальная настройка администратора |
| 🔗 | Добавление VPN-провайдеров по URL подписки |
| 🔄 | Синхронизация и обновление подписок |
| 📦 | Нормализация серверов в единую модель |
| 🧩 | VLESS · VMess · Trojan · Shadowsocks · Hysteria2 · TUIC · AnyTLS · SSH · SOCKS5 · NaiveProxy |
| 🗂️ | Base64-подписки и sing-box JSON |
| 🧠 | Capability detection для доступных runtime-ядер |
| 🧪 | Быстрый screening перед длительным тестом |
| 📡 | DNS · TCP/TLS · HTTP/HTTPS |
| 📊 | Latency · jitter · packet loss |
| 🚀 | Throughput samples |
| 🛡️ | Отдельная проверка whitelist-sensitive targets |
| 📈 | История измерений и аналитика |
| 🐳 | Docker deployment |
| 🧱 | Изолированный privileged worker |
| ❤️ | Healthchecks и CI |

### VPN runtime

**LX → Extended → WireGuard → optional Xray**

- **sing-box-lx** — основной runtime;
- **sing-box-extended** — fallback для расширенных возможностей;
- **WireGuard** — отдельный стандартный adapter;
- **Xray** — optional compatibility backend.

---

## 🧪 Как проходит тест

![Benchmark flow](https://raw.githubusercontent.com/OrionFalls/VPN-Bench/main/assets/readme/benchmark-flow.svg)

### 1. 📥 Импорт

VPN-Bench получает подписку и превращает её в нормализованный список серверов.

### 2. ⚡ Screening

Короткие проходы быстро отсеивают узлы, которые не устанавливают соединение, нестабильны или не проходят базовые проверки.

### 3. 🔬 Полный тест

Только выбранные серверы переходят в более длительное измерение.

### 4. 📊 История

Каждое измерение сохраняется. Со временем можно видеть не только разовый результат, но и стабильность узла.

---

## 🛡️ Изоляция — ключевой принцип

VPN-тест **не должен ломать сеть самого VPN-Bench**.

Controller работает без `NET_ADMIN`.

Worker получает необходимые сетевые возможности и для каждого задания создаёт отдельный Linux network namespace:

```text
Controller
    │
    ▼
Worker
    │
    ├── Job #1 → netns → VPN → probes
    ├── Job #2 → netns → VPN → probes
    └── Job #3 → netns → VPN → probes
```

VPN-core и TUN-интерфейс остаются внутри namespace. Основной маршрут хоста при этом не используется для VPN-туннеля.

---

## 🎯 Whitelist-bypass

Это отдельная проверка, а не «ещё один ping».

Логика:

```text
Target
  │
  ├── без VPN → доступен?
  │       └── да → not_applicable
  │
  └── без VPN → недоступен
          │
          └── через VPN → доступен?
                  ├── да → bypass confirmed
                  └── нет → failed
```

Так обычная доступность сайта не смешивается с результатом проверки обхода.

---

## ⏱️ Режимы тестирования

### ⚖️ Equal Time

Общее время кампании распределяется между выбранными серверами.

**Пример:** 20 серверов × 60 секунд ≈ 20 минут.

### ▶️ Sequential

Серверы проходят тест последовательно.

---

## 🖥️ Web UI

| Раздел | Назначение |
|---|---|
| 🏠 **Dashboard** | состояние системы и текущая кампания |
| 🔗 **Providers** | подписки и синхронизация |
| 🖥️ **Servers** | импортированные узлы и capabilities |
| 🧪 **Tests** | screening и полные тесты |
| 📊 **Analytics** | накопленные результаты |
| 📜 **Logs** | диагностика |
| ⚙️ **Settings** | системные настройки |

Интерфейс рассчитан на **desktop + tablet + mobile**.

---

## 🚀 Быстрый старт

Рекомендуется отдельная Debian/Ubuntu VM.

```bash
curl -fsSL https://raw.githubusercontent.com/OrionFalls/VPN-Bench/main/install.sh | sudo bash
```

Установщик:

1. устанавливает Docker при необходимости;
2. клонирует/обновляет репозиторий;
3. создаёт конфигурацию;
4. генерирует секрет;
5. собирает контейнеры;
6. запускает Controller + Worker;
7. выполняет healthcheck;
8. показывает адрес Web UI.

> 💡 Для production-развёртывания лучше использовать отдельную VM/LXC и не размещать VPN-Bench непосредственно на основном OpenWrt.

---

## 🧱 Архитектура

```text
                  ┌─────────────────────┐
                  │      Web UI         │
                  │      FastAPI        │
                  └──────────┬──────────┘
                             │
                  ┌──────────▼──────────┐
                  │     Controller      │
                  │     SQLite / API    │
                  └──────────┬──────────┘
                             │
                  Docker internal network
                             │
                  ┌──────────▼──────────┐
                  │       Worker        │
                  │ NET_ADMIN + TUN     │
                  └──────────┬──────────┘
                             │
                    isolated netns
                             │
              ┌──────────────▼──────────────┐
              │        VPN runtime         │
              │ LX / Extended / WG / Xray  │
              └──────────────┬──────────────┘
                             │
                    real test traffic
                             │
              ┌──────────────▼──────────────┐
              │ DNS · HTTP · TCP · Speed    │
              │ Latency · Loss · Bypass     │
              └─────────────────────────────┘
```

---

## 🔒 Безопасность

- URL подписок хранятся в зашифрованном виде.
- Ключ шифрования задаётся через `VPN_BENCH_SECRET`.
- Controller не получает `NET_ADMIN`.
- VPN-сеансы запускаются в отдельных network namespaces.
- Для доступа извне рекомендуется HTTPS reverse proxy + firewall.

---

## 🛠️ Разработка

```bash
git clone https://github.com/OrionFalls/VPN-Bench.git
cd VPN-Bench

pip install -e .
pytest -q
```

Docker:

```bash
docker compose up -d --build
```

CI проверяет Python-тесты, браузерный JavaScript и Docker image.

---

## 🗺️ Roadmap

- [x] Controller / Worker architecture
- [x] Isolated VPN runtime
- [x] Provider subscriptions
- [x] Server normalization
- [x] Basic network probes
- [x] Screening campaigns
- [x] Mobile-responsive UI
- [ ] 📈 Полноценная аналитика и графики
- [ ] 🚀 Controlled throughput benchmark
- [ ] 🛡️ Расширенный whitelist-bypass benchmark
- [ ] 🕐 Long-term stability campaigns
- [ ] 🗄️ PostgreSQL backend
- [ ] 📤 Экспорт результатов
- [ ] 🔔 Уведомления о деградации серверов

---

## 🤝 Идея проекта

VPN-Bench создаётся как **лаборатория для воспроизводимого тестирования VPN**, а не как очередной «speedtest на один раз».

Фиксированные targets → одинаковая методика → изолированное выполнение → сырые измерения → история.

**Меньше субъективности. Больше данных.**

---

<div align="center">

**⚡ VPN-Bench**

[GitHub](https://github.com/OrionFalls/VPN-Bench) · GPL-3.0

</div>
