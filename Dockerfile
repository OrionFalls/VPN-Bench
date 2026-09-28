FROM debian:bookworm-slim AS cores

ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl tar \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "$TARGETARCH" in \
      amd64) LX_ARCH="amd64"; EXT_ARCH="amd64" ;; \
      arm64) LX_ARCH="arm64"; EXT_ARCH="arm64" ;; \
      *) echo "Unsupported TARGETARCH: $TARGETARCH"; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/Leadaxe/sing-box-lx/releases/download/v1.14.2-lx.5/sing-box-1.14.2-lx.5-linux-$LX_ARCH.tar.gz" -o /tmp/lx.tar.gz; \
    tar -xzf /tmp/lx.tar.gz -C /tmp; \
    find /tmp -type f -name sing-box -exec cp {} /usr/local/bin/sing-box-lx \;; \
    curl -fsSL "https://github.com/shtorm-7/sing-box-extended/releases/download/v1.14.1-extended-2.7.2/SFL-1.14.1-extended-2.7.2-$EXT_ARCH.deb" -o /tmp/extended.deb; \
    mkdir -p /tmp/extended; \
    dpkg-deb -x /tmp/extended.deb /tmp/extended; \
    cp /tmp/extended/usr/bin/sing-box /usr/local/bin/sing-box-extended; \
    chmod +x /usr/local/bin/sing-box-lx /usr/local/bin/sing-box-extended

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VPN_BENCH_SING_BOX_LX=/usr/local/bin/sing-box-lx \
    VPN_BENCH_SING_BOX_EXTENDED=/usr/local/bin/sing-box-extended \

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates iproute2 iptables procps \
    && rm -rf /var/lib/apt/lists/*

COPY --from=cores /usr/local/bin/sing-box-lx /usr/local/bin/sing-box-lx
COPY --from=cores /usr/local/bin/sing-box-extended /usr/local/bin/sing-box-extended
COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8080

CMD ["python", "-m", "vpn_bench"]
