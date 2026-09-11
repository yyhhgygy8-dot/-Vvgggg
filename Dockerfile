FROM python:3.11-slim-bookworm
ENV DEBIAN_FRONTEND=noninteractive XRAY_BIN=/usr/local/bin/xray
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip ca-certificates procps && rm -rf /var/lib/apt/lists/*
# نصب خودکار Xray در زمان build؛ نسخه را با XRAY_VERSION قابل کنترل کنید.
ARG XRAY_VERSION=1.8.24
RUN curl -fsSL "https://github.com/XTLS/Xray-core/releases/download/v${XRAY_VERSION}/Xray-linux-64.zip" -o /tmp/xray.zip && unzip /tmp/xray.zip -d /tmp/xray && install -m 0755 /tmp/xray/xray /usr/local/bin/xray && rm -rf /tmp/xray* || true
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/
RUN mkdir -p /data
ENV PORT=5000 XRAY_PORT=443 VLESS_PATH=/vless
EXPOSE 5000 443
CMD ["gunicorn","--bind","0.0.0.0:5000","--workers","1","--threads","4","--timeout","120","wsgi:app"]
