FROM python:3.11-slim

WORKDIR /app

# Увеличиваем таймауты (без зеркала)
ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_RETRIES=10

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install fastapi uvicorn[standard]
RUN pip install --no-cache-dir --timeout 100 --retries 10 -r requirements.txt

COPY . .
RUN mkdir -p /app/data

RUN python -c "import uvicorn; print('uvicorn installed successfully')"

EXPOSE 8000

# Хостинг (Render) передаёт порт в переменной PORT; локально её нет, и берётся 8000.
# --proxy-headers и --forwarded-allow-ips берут настоящий адрес посетителя из X-Forwarded-For,
# иначе ограничения частоты (вход, заявки, ИИ-поиск) считались бы по адресу прокси хостинга
# и действовали бы на всех посетителей разом. Бэкенд должен быть доступен только через прокси хостинга.
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
