#!/bin/bash

# Activate Virtual Env (if exists)
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Starting E-commerce Tax SaaS Services..."

# 1. Apply Migrations
echo "Applying Database Migrations..."
python manage.py makemigrations finance_core
python manage.py migrate

# 2. Start Celery Worker (Background)
echo "Starting Celery Worker..."
celery -A ecommerce_tax_saas worker -l info --detach --pidfile=worker.pid --logfile=worker.log

# 3. Start Celery Beat (Background)
echo "Starting Celery Beat..."
celery -A ecommerce_tax_saas beat -l info --detach --pidfile=beat.pid --logfile=beat.log

# 4. Start Django Server
echo "Starting Django Server..."
python manage.py runserver 0.0.0.0:8000
