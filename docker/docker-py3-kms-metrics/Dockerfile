# This is a full version of Dockerfile with SQLite support and Prometheus metrics endpoint
FROM alpine:3.24.1

ARG BUILD_COMMIT=unknown
ARG BUILD_REFERENCE=unknown

ENV IP=::
ENV DUALSTACK=1
ENV PORT=1688
ENV EPID=""
ENV LCID=1033
ENV CLIENT_COUNT=26
ENV ACTIVATION_INTERVAL=120
ENV RENEWAL_INTERVAL=10080
ENV HWID=RANDOM
ENV LOGLEVEL=INFO
ENV LOGFILE=STDOUT
ENV LOGSIZE=""
ENV TZ=America/Chicago
ENV WEBUI=1
ENV WEBUI_PORT=8080
ENV METRICS=0
ENV METRICS_PORT=9090

# fix for apk 403 errors during build time
RUN sed -i 's/https/http/g' /etc/apk/repositories

# Adding dependency packages
RUN apk add --no-cache --update bash python3 py3-pip ca-certificates shadow tzdata

# Installing requirements (base + prometheus-client for metrics)
COPY docker/docker-py3-kms/requirements.txt /home/py-kms/requirements-base.txt
COPY docker/docker-py3-kms-metrics/requirements.txt /home/py-kms/requirements-metrics.txt
RUN cat /home/py-kms/requirements-base.txt > /home/py-kms/requirements.txt && \
    echo "" >> /home/py-kms/requirements.txt && \
    cat /home/py-kms/requirements-metrics.txt >> /home/py-kms/requirements.txt && \
    pip3 install --break-system-packages --no-cache-dir -r /home/py-kms/requirements.txt

RUN mkdir -p /db/ /home/py-kms/db && \
    adduser -S py-kms -G users -s /bin/bash && \
    chown py-kms:users /home/py-kms && \
    # Fix undefined timezone, in case the user did not mount the /etc/localtime
    ln -sf /usr/share/zoneinfo/UTC /etc/localtime

COPY py-kms /home/py-kms/
COPY docker/entrypoint.py /usr/bin/entrypoint.py
COPY docker/healthcheck.py /usr/bin/healthcheck.py
COPY docker/start.py /usr/bin/start.py
RUN chmod 555 /usr/bin/entrypoint.py /usr/bin/healthcheck.py /usr/bin/start.py

# Additional permission hardening: keep application files read-only, but preserve
# a dedicated writable database directory for WebUI/SQLite at runtime.
RUN find /home/py-kms -type f -print -exec chmod 444 {} ';' && \
    find /home/py-kms -type d -print -exec chmod 555 {} ';' && \
    chown root: -R /home/py-kms && \
    chown py-kms: /home/py-kms && \
    chmod 1777 /home/py-kms/db

# Web-interface specifics
COPY LICENSE /LICENSE
RUN echo "$BUILD_COMMIT" > /VERSION && echo "$BUILD_REFERENCE" >> /VERSION

WORKDIR /home/py-kms

# KMS port (default 1688), WebUI port (default 8080), Metrics port (default 9090)
# Use docker run -p to expose these ports as needed
EXPOSE ${PORT}/tcp
EXPOSE 8080/tcp
EXPOSE 9090/tcp

HEALTHCHECK --interval=5m --timeout=10s --start-period=10s --retries=3 CMD /usr/bin/python3 /usr/bin/healthcheck.py

ENTRYPOINT [ "/usr/bin/python3", "-u", "/usr/bin/entrypoint.py" ]
