# Flask application image: automatically run db upgrade on startup, then start Gunicorn
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (including entrypoint.sh)
COPY . .

# Entrypoint script must be given execute permissions after COPY . . , otherwise it will be overwritten
RUN chmod +x entrypoint.sh

# Specify Flask application via environment variable (can also be overridden at runtime)
ENV FLASK_APP=app:create_app

EXPOSE 5000

# Use script as entry: first upgrade then start Gunicorn
ENTRYPOINT ["./entrypoint.sh"]
