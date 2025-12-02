FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

# Port d'écoute de l'API
EXPOSE 6969

CMD ["python", "bot.py"]