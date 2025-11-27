import os
import sys
from django.core.wsgi import get_wsgi_application

# Adiciona o diretório raiz do projeto ao caminho de importação.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_tax_saas.settings')

application = get_wsgi_application()
