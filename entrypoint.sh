#!/bin/sh

# Exit immediately on error
set -e

# 1. Apply database migrations (only run upgrade, not migrate)
echo "Running DB migrations..."
flask db upgrade

# 2. Start Gunicorn
echo "Starting Gunicorn..."
# exec allows gunicorn to replace the current shell process and receive system signals
# gthread multi-threaded mode: suitable for long-running I/O (e.g., SSE streaming), prevents a single request from monopolizing the process and causing timeout
# --preload: load the application (including ML model) in the Master process early, workers fork and share memory, avoiding each worker loading its own copy of the model
exec gunicorn -w 2 -b 0.0.0.0:5000 --worker-class gthread --threads 4 --timeout 120 --preload --access-logfile - wsgi:app
