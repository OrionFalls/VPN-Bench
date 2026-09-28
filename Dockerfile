FROM ghcr.io/sagernet/sing-box:v1.14.2 AS singbox

FROM ghcr.io/xtls/xray-core:26.9.8 AS xray

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VPN_BENCH_SING_BOX=/usr/local/bin/sing-box \
    VPN_BENCH_XRAY=/usr/local/bin/xray

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=singbox /usr/local/bin/sing-box /usr/local/bin/sing-box
COPY --from=xray /usr/local/bin/xray /usr/local/bin/xray
COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8080

CMD ["python", "-m", "vpn_bench"]
