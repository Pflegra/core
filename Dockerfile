ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3 py3-pip py3-wheel gcc musl-dev libffi-dev curl tar

RUN pip3 install --no-cache-dir --break-system-packages \
    fastapi \
    "uvicorn[standard]" \
    jinja2 \
    python-multipart \
    reportlab \
    odfpy \
    openpyxl \
    xlrd \
    bcrypt \
    itsdangerous

WORKDIR /app
COPY app/ /app/
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh
RUN mkdir -p /share/pflegra/Archiv
# v2.3.2 ingress fix
RUN echo "2.3.2" > /app/version.txt

CMD ["/app/run.sh"]
