ARG BUILD_FROM=python:3.12-alpine
FROM ${BUILD_FROM}
RUN apk add --no-cache python3 py3-pip py3-wheel gcc musl-dev libffi-dev curl tar \
    tesseract-ocr tesseract-ocr-data-deu
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
    itsdangerous \
    pymupdf \
    pytesseract \
    pillow
WORKDIR /app
COPY app/ /app/
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh
RUN mkdir -p /share/pflegra/Archiv
RUN echo "1.6.2" > /app/version.txt
CMD ["/app/run.sh"]
