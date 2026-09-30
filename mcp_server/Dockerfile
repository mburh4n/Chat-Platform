FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py local_dictionary.json ./

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8001

CMD ["python", "main.py"]
