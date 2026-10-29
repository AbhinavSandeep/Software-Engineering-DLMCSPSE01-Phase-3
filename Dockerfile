FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=wsgi.py

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x docker-entrypoint.sh && useradd --create-home appuser
USER appuser

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
# Cloud platforms such as Render pass the port in $PORT; locally 8000 is used.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 2 wsgi:app"]
