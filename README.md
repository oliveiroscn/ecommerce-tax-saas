# SaaS de Análise de Lucratividade Real e Gestão Fiscal para E-commerce

## 1. Visão Geral
Este sistema é uma plataforma SaaS (Software as a Service) projetada para fornecer uma análise precisa da **Margem Líquida Real** de vendas em marketplaces (Mercado Livre, Shopee). 

Diferente de planilhas ou ERPs genéricos, esta solução integra profundamente os custos de produto (CMV), comissões variáveis, custos logísticos complexos (Envio Próprio vs. Coletas) e, crucialmente, a **Engenharia Tributária Brasileira**. O sistema suporta regimes de Lucro Real e Simples Nacional, com destaque para a aplicação automática de Benefícios Fiscais de Carga Efetiva (ex: TTS de Minas Gerais), garantindo que o lucro reportado seja o lucro real do bolso do vendedor.

## 2. Stack Tecnológica

*   **Linguagem:** Python 3.10+
*   **Framework Backend:** Django 4.x & Django Rest Framework (DRF)
*   **Banco de Dados:** PostgreSQL
*   **Frontend:** Next.js / React (Dashboard de Analytics)
*   **Filas & Agendamento:** Celery & Redis (Broker)
*   **Integrações:** Mercado Livre API, Shopee API V2 (HMAC-SHA256)

## 3. Arquitetura Fiscal e de Dados

### Multi-Tenancy
O sistema implementa uma arquitetura multi-tenant lógica. Todos os dados críticos (Transações, Custos, Configurações Fiscais) são isolados pelo modelo `Organization`. Cada requisição e processamento é escopado pelo CNPJ do cliente.

### Motor Fiscal (Tax Engine)
O coração do sistema é o cálculo de impostos no momento da venda.
*   **Regime Padrão:** Cálculo de Débito e Crédito de ICMS/PIS/COFINS.
*   **Benefícios Fiscais (TTS/Corredor):** O modelo `TaxProfile` permite configurar uma `effective_tax_rate` (ex: 1.3% ou 4% dependendo do estado de destino). O sistema calcula automaticamente o imposto a pagar baseado nessa alíquota efetiva, substituindo o cálculo padrão de débito de ICMS, o que é essencial para e-commerces situados em estados com incentivos fiscais.

### Logística Inteligente (Smart Logistics)
Para evitar a "dupla cobrança" de frete comum em integrações, o sistema utiliza uma lógica de **Exclusão Condicional**:
1.  O sistema verifica a tabela `LogisticsCostTable` para o método de envio da transação (ex: "Envio Próprio").
2.  Se um custo fixo interno for encontrado, a flag `is_fixed_cost_applied` é ativada.
3.  **Resultado:** O custo de frete reportado pela API do marketplace (`shipping_cost_platform`) é zerado no cálculo da margem, e apenas o custo fixo interno é considerado.

## 4. Instalação e Configuração

### Pré-requisitos
*   Python 3.10+
*   Redis (para o Celery)
*   PostgreSQL (ou SQLite para dev)

### Passo a Passo

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/seu-repo/ecommerce_tax_saas.git
    cd ecommerce_tax_saas
    ```

2.  **Crie e ative o ambiente virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # venv\Scripts\activate  # Windows
    ```

3.  **Instale as dependências:**
    ```bash
    pip install django djangorestframework celery redis requests psycopg2-binary
    ```

4.  **Configure as Variáveis de Ambiente (.env):**
    Crie um arquivo `.env` na raiz com:
    ```env
    DJANGO_SECRET_KEY=sua_chave_secreta_segura
    DEBUG=True
    DATABASE_URL=postgres://user:pass@localhost:5432/ecommerce_db
    CELERY_BROKER_URL=redis://localhost:6379/0
    # Credenciais de Integração (Opcional, podem ser geridas via Admin)
    ML_CLIENT_ID=seu_app_id
    ML_CLIENT_SECRET=seu_secret
    SHOPEE_PARTNER_KEY=sua_partner_key
    ```

5.  **Inicialize o Banco de Dados:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    python manage.py createsuperuser # Para acessar o Admin
    ```

6.  **Execute os Serviços:**
    *   **API Server:** `python manage.py runserver`
    *   **Celery Worker:** `celery -A ecommerce_tax_saas worker -l info`
    *   **Celery Beat:** `celery -A ecommerce_tax_saas beat -l info`

## 5. Monitoramento e Manutenção

O sistema possui automação robusta via Celery para garantir a continuidade da operação:

### Tarefas Agendadas (Cron Jobs)
*   `renew_all_platform_tokens` (A cada 1 hora): Verifica e renova tokens de acesso do Mercado Livre e Shopee antes da expiração.
*   `fetch_all_new_orders` (A cada 30 minutos): Coleta novos pedidos incrementalmente de todas as contas conectadas.

### Sistema de Alertas (Confiabilidade)
O modelo `IntegrationErrorLog` registra falhas de comunicação com APIs externas.
*   **Alertas Críticos:** Se uma renovação de token falhar (o que pararia a operação), o sistema dispara automaticamente um e-mail para o administrador via `send_alert_email`, permitindo uma intervenção rápida antes que a coleta de vendas seja afetada.
*   **Dashboard de Saúde:** O Django Admin exibe o status de saúde (`Healthy`, `Critical`) de cada organização baseando-se nos logs de erro recentes.
