web: gunicorn ecommerce_tax_saas.wsgi --log-file -
worker: celery -A ecommerce_tax_saas worker -l info
beat: celery -A ecommerce_tax_saas beat -l info
