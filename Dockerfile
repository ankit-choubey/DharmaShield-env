FROM python:3.11-slim

# Non-root user — HF Spaces requirement
RUN useradd -m -u 1000 user
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --chown=user requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY --chown=user . /app

USER user

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/health', timeout=3)"

# Critical: 0.0.0.0 mandatory — not localhost
CMD ["uvicorn", "dharma_shield.server:app", "--host", "0.0.0.0", "--port", "7860"]