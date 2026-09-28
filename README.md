# ⚡ VPN-Bench

<div align="center">

**Real-world VPN benchmarking & long-term connection monitoring**

[![CI](https://github.com/OrionFalls/VPN-Bench/actions/workflows/ci.yml/badge.svg)](https://github.com/OrionFalls/VPN-Bench/actions/workflows/ci.yml) ![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?logo=python&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white) ![License](https://img.shields.io/badge/License-GPL--3.0-blue)

**🇷🇺 RU | [🇬🇧 EN](#english)**

</div>

Self-hosted автоматический бенчмарк VPN-серверов и система долгосрочного мониторинга качества соединений.

# 🇷🇺 Русская версия

## Что это

VPN-Bench предназначен для автоматического сравнения VPN-серверов не по простому ping до IP-адреса, а по реальному качеству соединения.

Идея проекта:

**подписка провайдера → импорт серверов → подключение через изолированное VPN-ядро → реальные сетевые проверки → сохранение результатов → история и аналитика.**

Главная цель — получить воспроизводимые измерения, по которым можно сравнивать десятки и сотни серверов и затем длительно наблюдать за ними.

## Текущий статус

- веб-панель с первоначальной настройкой администратора;
- авторизация и сессии;
- шифрование URL подписок при хранении;
- добавление VPN-провайдеров и автоматическое обновление подписок;
- нормализация серверов в единую модель;
- импорт Base64-подписок;
- импорт VLESS, VMess, Trojan, Shadowsocks, Hysteria2, TUIC, AnyTLS, SSH, SOCKS5 и NaiveProxy URI;
- импорт sing-box JSON;
- модель тестовых кампаний с живым прогрессом;
- режимы **Equal Time** и **Sequential**;
- регулярные выражения для фильтрации серверов;
- SQLite для результатов и журналов;
- реальные DNS/HTTP/TCP-пробы через VPN proxy;
- измерение latency, jitter и packet loss;
- изолированный запуск VPN-ядра;
- Docker-развёртывание;
- CI с Python-тестами и проверкой Docker-сборки;
- одно-командная установка на отдельную Debian/Ubuntu VM.

Проект находится в активной разработке: полноценные измерения скорости, whitelist-bypass, длительные stability-тесты и аналитика ещё расширяются.

## VPN-ядра

Архитектура специально не привязана к одному ядру.

> **Runtime по умолчанию: только LX + Extended. Xray не входит в базовый Docker image и подключается как optional compatibility backend.**

| Ядро | Назначение | Runtime |
|---|---|---|
| **sing-box-lx** | основной универсальный backend | ✅ |
| **sing-box-extended** | дополнительные протоколы и fallback | ✅ |
| **Xray** | резервная Xray-специфичная совместимость | optional |
| upstream **sing-box** | baseline/reference для разработки | ❌ |

LX становится основным runtime-ядром. Отдельный upstream sing-box в runtime не нужен: он остаётся baseline/reference только для разработки и проверки совместимости.

Extended оставляем как специализированный fallback для протоколов и функций, которые выходят за пределы обычной sing-box/LX-модели. Xray — последний compatibility fallback.

**Runtime-цепочка: LX → Extended → optional Xray.** Это уменьшает размер образа и количество почти одинаковых бинарников, не закрывая доступ к редким протоколам.

## Импорт подписок

Подписка превращается в нормализованный объект:

    Provider
       |
       v
    Subscription
       |
       v
    Parser
       |
       +--> VLESS
       +--> VMess
       +--> Trojan
       +--> Shadowsocks
       +--> Hysteria2
       +--> sing-box JSON
       |
       v
    Normalized Server
       +--> protocol
       +--> host
       +--> port
       +--> transport
       +--> security
       +--> metadata

В дальнейшем importer будет расширяться за счёт форматов расширенных ядер, включая TUIC, AnyTLS, WireGuard/AmneziaWG, NaiveProxy, MASQUE и другие варианты.

## Реальный тест соединения

VPN-Bench не оценивает качество сервера по одному ping.

Планируемые уровни проверки:

1. запуск VPN в изолированном окружении;
2. проверка установления соединения;
3. DNS;
4. TCP/TLS;
5. HTTP/HTTPS;
6. latency;
7. jitter;
8. packet loss;
9. download/upload;
10. whitelist-bypass;
11. длительная стабильность.

Первичный screening должен быть коротким, чтобы быстро проверять большое количество серверов. После screening только подходящие серверы переходят в длительный тест.

## Режимы тестирования

### Equal Time

Общее время кампании делится между выбранными серверами. Например: **20 серверов × 60 секунд = около 20 минут на кампанию.**

### Sequential

Сервер тестируется до завершения заданного набора проверок, после чего запускается следующий.

## Изоляция

> Тест VPN никогда не должен ломать сеть самого benchmark-хоста.

VPN-ядро не должно менять default route Proxmox VM, Docker host или основной OpenWrt router.

Планируемая архитектура:

    VPN-Bench Controller
            |
            v
       Isolated Worker
            |
       +----+----+
       |         |
    sing-box   Xray
       |         |
       +----+----+
            |
            v
        Test traffic

Только worker должен получать необходимые сетевые права. Контроллер, web UI и база данных не должны получать NET_ADMIN без необходимости.

## Whitelist-bypass

Whitelist-bypass будет отдельным типом теста, а не частью обычного ping/speed benchmark.

Будут разделяться обычная доступность Интернета, whitelist-sensitive домены, DNS, HTTP/HTTPS, стабильность и скорость через VPN.

## Скорость

Непрерывный speedtest для каждого сервера не нужен и будет искажать картину.

Планируется короткий throughput screening, фиксированные endpoint'ы, отдельные download/upload samples, длительный throughput только для отобранных серверов и повторение измерений в разное время суток.

В идеале benchmark будет использовать собственный контролируемый VPS endpoint. Если он недоступен — fallback на публичные endpoints.

## UI

1. **Dashboard** — состояние системы, провайдеры, серверы и текущая кампания.
2. **Providers** — подписки, обновление, срок действия и статистика.
3. **Servers** — список серверов и параметры подключения.
4. **Tests** — запуск кампаний, фильтры, длительность и live progress.
5. **Analytics** — графики, история и сравнение результатов.
6. **Logs** — технические события и диагностика.
7. **Settings** — конфигурация, безопасность, хранилище и обновления.

## Безопасность

URL подписок не возвращаются обычным API списка провайдеров и хранятся в базе в зашифрованном виде. Ключ шифрования хранится отдельно через VPN_BENCH_SECRET.

Для доступа из Интернета VPN-Bench следует размещать за HTTPS reverse proxy и ограничивать firewall.

## Установка одной командой

На отдельной Debian/Ubuntu VM:

    curl -fsSL https://raw.githubusercontent.com/OrionFalls/VPN-Bench/main/install.sh | sudo bash

Установщик устанавливает Docker, клонирует или обновляет репозиторий, создаёт конфигурацию, генерирует секрет, собирает image, запускает приложение, ждёт healthcheck и показывает адрес веб-панели.

## Планируемая архитектура

    Provider subscriptions
             |
             v
    Subscription importer
             |
             v
    Normalized server model
             |
             v
    Capability detection
             |
       +-----+-----+
       |     |     |
       v     v     v
   sing-box  lx  extended
       |     |     |
       +-----+-----+
             |
             v
           Xray
       (если требуется)
             |
             v
      Isolated benchmark
             |
      +------+------+------+------+
      |      |      |      |      |
     DNS    HTTP   TCP/TLS Speed Whitelist
             |
             v
        Measurements
             |
             v
       SQLite / PostgreSQL
             |
             v
          Web UI / API

## Разработка

    pip install -e .
    pytest -q

CI автоматически запускает тесты на Python 3.13 и проверяет сборку Docker image.

## Репозиторий

GitHub: https://github.com/OrionFalls/VPN-Bench

---

<a id="english"></a>

# 🇬🇧 English version

## What is VPN-Bench?

VPN-Bench is a self-hosted automated VPN server benchmark and long-term connection-quality monitoring system.

The project compares VPN servers using real network behaviour instead of relying on a simple ping to the VPN endpoint.

Intended pipeline:

**provider subscription → server import → isolated VPN core → real network probes → stored measurements → history and analytics.**

## Current status

- web panel with first-run administrator setup;
- authentication and sessions;
- encrypted subscription URLs at rest;
- provider management and automatic subscription synchronization;
- normalized server model;
- Base64 subscription decoding;
- VLESS, VMess, Trojan, Shadowsocks and Hysteria2 import;
- sing-box JSON import;
- live test campaign state;
- **Equal Time** and **Sequential** scheduling;
- regular-expression server filtering;
- SQLite storage;
- real DNS/HTTP/TCP probes through a VPN proxy;
- latency, jitter and packet-loss measurements;
- isolated VPN-core execution;
- Docker deployment;
- CI with Python tests and Docker image builds;
- one-command Debian/Ubuntu VM installation.

Throughput benchmarking, whitelist-bypass testing, long-term stability testing and analytics are still being expanded.

## VPN cores

| Core | Purpose | Runtime |
|---|---|---|
| **sing-box-lx** | primary general-purpose backend | ✅ |
| **sing-box-extended** | extended protocol fallback | ✅ |
| **Xray** | Xray-specific compatibility fallback | optional |
| upstream **sing-box** | development/reference baseline | ❌ |

LX is the primary runtime core. The upstream sing-box binary is not shipped in production; it remains a development/reference baseline.

Extended is kept as a specialized fallback for additional protocols and features. Xray remains the final compatibility fallback.

**Runtime strategy: LX → Extended → optional Xray.**

## Real connection testing

VPN-Bench is not intended to evaluate servers using a single ping.

Planned checks:

1. isolated VPN startup;
2. connection establishment;
3. DNS;
4. TCP/TLS;
5. HTTP/HTTPS;
6. latency;
7. jitter;
8. packet loss;
9. download/upload;
10. whitelist-bypass;
11. long-term stability.

Initial screening should be short enough to process a large server pool efficiently. Only selected servers should proceed to long stability tests.

## Isolation

> A VPN test must never break the benchmark host's own network.

The VPN core must not modify the default route of the Proxmox VM, Docker host or primary OpenWrt router.

Only isolated workers should receive the network capabilities required by the VPN core. The controller, web UI and database should not receive NET_ADMIN unnecessarily.

## One-command installation

On a dedicated Debian/Ubuntu VM:

    curl -fsSL https://raw.githubusercontent.com/OrionFalls/VPN-Bench/main/install.sh | sudo bash

The installer installs Docker when needed, clones or updates the repository, creates configuration, generates the encryption secret, builds the image, starts the application, waits for health and prints the web-panel address.

## Planned architecture

    Provider subscriptions
             |
             v
    Subscription importer
             |
             v
    Normalized server model
             |
             v
    Capability detection
             |
       +-----+-----+
       |     |     |
       v     v     v
   sing-box  lx  extended
       |     |     |
       +-----+-----+
             |
             v
           Xray
             |
             v
      Isolated benchmark
             |
      +------+------+------+------+
      |      |      |      |      |
     DNS    HTTP   TCP/TLS Speed Whitelist
             |
             v
        Measurements
             |
             v
       SQLite / PostgreSQL
             |
             v
          Web UI / API

## Development

    pip install -e .
    pytest -q

CI runs the Python 3.13 test suite and verifies the Docker image build.

## Repository

urlGitHub — OrionFalls/VPN-Benchhttps://github.com/OrionFalls/VPN-Bench

---

VPN-Bench is intended to become a reproducible VPN-node laboratory: fixed targets, consistent methodology, isolated execution, raw measurements and long-term history instead of subjective speed tests.