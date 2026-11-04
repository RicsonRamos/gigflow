"""
config.py - Configurações Gerais do GigFlow
Autor: Ricson Ramos
Foco: Mercado Nacional & Internacional, Home Office Aberto (Sem Requisitos Especialistas),
Automação de Propostas, Telegram e Notion
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
DB_PATH = DATA_DIR / "freelance_jobs.db"

# Garante criação dos diretórios locais
DATA_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)

# Função auxiliar para carregar .env sem dependência de terceiros (Custo Zero)
def load_env_file():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))

load_env_file()

# ==========================================
# 1. PERFIL PROFISSIONAL & ESPECIALIDADES TÉCNICAS (RICSON RAMOS)
# ==========================================
PROFILE = {
    "name": "Ricson Ramos",
    "headline": "Especialista em Ciência de Dados, OSINT, Cibersegurança e Automação com Python",
    "headline_en": "Data Science, OSINT, Cybersecurity & Python Automation Specialist",
    "portfolio_url": "https://ricsonramos.github.io/",
    "github_url": "https://github.com/RicsonRamos",
    "email": "ricsonramos@outlook.com",
    
    # Pitch Profissional Central
    "pitch": (
        "Tecnólogo em Ciência de Dados com mais de 10 anos de experiência em inteligência operacional, "
        "tomada de decisão sob risco e operações críticas. Especialista no desenvolvimento de pipelines de dados, "
        "modelagem preditiva (Machine Learning/XGBoost), inteligência de fontes abertas (OSINT), "
        "segurança da informação e engenharia de automação avançada com Python."
    ),
    "pitch_en": (
        "Data Science Technologist with 10+ years of mission-critical operations, risk intelligence, and quantitative analysis. "
        "Specialist in production data pipelines, predictive machine learning (XGBoost), Open Source Intelligence (OSINT), "
        "information security, and high-performance Python process automation."
    ),
    
    # Portfólio de Projetos Reais no GitHub
    "featured_projects": {
        "churn_radar": {
            "title": "Streaming Churn Radar",
            "url": "https://github.com/RicsonRamos/streaming_service_analysis_churn",
            "desc": "Pipeline MLOps completo com XGBoost Native, SHAP para explicabilidade e simulador de ROI de negócio em Streamlit.",
            "desc_en": "End-to-end MLOps pipeline with native XGBoost, SHAP explainability, and Streamlit ROI business simulator.",
            "tags": ["machine learning", "xgboost", "streamlit", "mlops", "churn", "previsão", "data science"]
        },
        "olist_platform": {
            "title": "Olist Data Platform",
            "url": "https://github.com/RicsonRamos/olist-data-platform",
            "desc": "Engenharia analítica moderna com dbt Core, PostgreSQL, Docker e testes automatizados de integridade.",
            "desc_en": "Modern analytics engineering with dbt Core, PostgreSQL, Docker containerization, and automated data tests.",
            "tags": ["dbt", "sql", "postgresql", "docker", "elt", "etl", "analytics engineering", "data pipeline"]
        },
        "macropulse": {
            "title": "MacroPulse Intelligence",
            "url": "https://github.com/RicsonRamos/macropulse",
            "desc": "Terminal de indicadores macroeconômicos e cálculo assíncrono de score de risco com FastAPI de alto rendimento.",
            "desc_en": "Macroeconomic terminal and real-time risk score calculations built with high-throughput asynchronous FastAPI.",
            "tags": ["fastapi", "api", "automação", "risco", "dados econômicos", "python", "backend"]
        },
        "osint_intel": {
            "title": "OSINT & Intelligence Automation",
            "url": "https://github.com/RicsonRamos",
            "desc": "Pipelines de coleta automatizada em fontes públicas, enriquecimento de entidades, OSINT e monitoramento investigativo com mitigação de riscos.",
            "desc_en": "Automated open-source intelligence gathering, entity resolution, investigative OSINT pipelines, and risk mitigation.",
            "tags": ["osint", "cybersecurity", "cibersegurança", "reconhecimento", "threat intelligence", "investigação"]
        }
    }
}

# ==========================================
# 2. CONFIGURAÇÕES TELEGRAM
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ==========================================
# 3. CONFIGURAÇÕES NOTION (CRM DE FREELAS)
# ==========================================
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

# ==========================================
# 4. CONFIGURAÇÕES DE IA (GEMINI FREE TIER OU TEMPLATE DINÂMICO)
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ==========================================
# 5. PILARES DE ESPECIALIDADE & PALAVRAS-CHAVE REFINADAS
# ==========================================

# Pilar 1: Ciência de Dados & Machine Learning
DATA_SCIENCE_KEYWORDS = [
    "data science", "ciência de dados", "ciencia de dados", "cientista de dados",
    "data scientist", "analista de dados", "analise de dados", "análise de dados",
    "data analyst", "data analysis", "analytics", "dados",
    "machine learning", "aprendizado de máquina", "aprendizado de maquina",
    "xgboost", "modelo preditivo", "predição", "predicao", "previsão", "previsao",
    "deep learning", "nlp", "llm", "langchain", "inteligência artificial", 
    "inteligencia artificial", "artificial intelligence", "ia", "ai agent",
    "streamlit", "dashboard", "power bi", "powerbi", "bi", "business intelligence",
    "dbt", "etl", "elt", "pipeline de dados", "data pipeline",
    "engenharia de dados", "engenheiro de dados", "data engineering", "data engineer",
    "sql", "postgresql", "big data", "pandas", "numpy", "scikit-learn"
]

# Pilar 2: OSINT & Cibersegurança
OSINT_CYBERSECURITY_KEYWORDS = [
    "osint", "open source intelligence", "cybersecurity", "cibersegurança", "ciberseguranca",
    "segurança da informação", "seguranca da informacao", "segurança", "seguranca",
    "infosec", "threat intelligence", "threat hunting", "investigação digital",
    "investigacao digital", "forense", "forensic", "pentest", "penetration testing",
    "vulnerabilidade", "vulnerability", "ethical hacking", "hacker ético", "malware",
    "soc", "siem", "reconhecimento", "coleta de inteligência", "appsec", "devsecops",
    "segurança defensiva", "segurança ofensiva", "auditoria de segurança",
    "cyber security", "threat", "vulnerabilidades", "análise de risco", "risk intelligence"
]

# Pilar 3: Automação & Web Scraping
AUTOMATION_KEYWORDS = [
    "automação", "automacao", "automation", "rpa", "web scraping", "scraper", "scraping",
    "crawler", "crawling", "raspagem", "bot", "bots", "selenium", "playwright", "patchright",
    "beautifulsoup", "puppeteer", "extração de dados", "extracao de dados", "coleta automatizada",
    "rotina automática", "rotina automatica", "script de automação", "automação de processos",
    "bot telegram", "bot whatsapp", "robô", "robo", "integrar api", "integração de sistemas"
]

# Pilar 4: Programação & Engenharia de Software
PROGRAMMING_KEYWORDS = [
    "python", "programação", "programacao", "programador", "programadora",
    "desenvolvedor python", "python developer", "desenvolvedor", "desenvolvedora",
    "backend", "back-end", "fastapi", "django", "flask", "api rest", "rest api",
    "endpoint", "microsserviço", "microservice", "docker", "docker-compose", "linux",
    "bash", "shell script", "software engineer", "engenharia de software", "script python",
    "scripts python", "desenvolvimento de software"
]

# União estrita dos 4 pilares de especialidade de Ricson
TARGET_KEYWORDS = (
    DATA_SCIENCE_KEYWORDS +
    OSINT_CYBERSECURITY_KEYWORDS +
    AUTOMATION_KEYWORDS +
    PROGRAMMING_KEYWORDS
)

# ==========================================
# 5.1 NÍVEL ATUAL DESEJADO (ESTÁGIOS, TRAINEE, JÚNIOR, NÍVEL INICIAL, FREELANCE, PJ)
# ==========================================
LEVEL_BOOST_KEYWORDS = [
    "estágio", "estagio", "estagiário", "estagiária", "estagiario", "estagiaria",
    "trainee", "júnior", "junior", "jr", "jr.", "iniciante", "entry level",
    "nível 1", "nivel 1", "nível i", "nivel i", "assistente",
    "freelance", "freelancer", "pj", "prestador", "prestação de serviços"
]

# ==========================================
# 5.2 EXCLUSÃO ESTRITA DE SENIORIDADE E GESTÃO (DESCARTE IMEDIATO)
# ==========================================
EXCLUDE_SENIORITY_KEYWORDS = [
    "sênior", "senior", "sr", "sr.", "sr/", "sr -", "tech lead", "lead", "staff",
    "principal", "head of", "head", "head de", "diretor", "diretora", "diretoria",
    "gerente", "gerência", "gerencia", "coordenador", "coordenadora", "coordenação",
    "coordenacao", "architect", "arquiteto", "especialista sênior", "especialista senior",
    "team lead", "engineering manager", "lead engineer", "iii", "nível iii", "nivel iii"
]

# ==========================================
# 5.3 EXCLUSÃO ESTRITA DE TRABALHO PRESENCIAL OU HÍBRIDO (APENAS 100% REMOTO / HOME OFFICE)
# ==========================================
EXCLUDE_PRESENTIAL_KEYWORDS = [
    "presencial", "apenas presencial", "trabalho presencial", "comparecer ao local",
    "comparecer na empresa", "comparecer presencialmente", "100% presencial",
    "modelo presencial", "formato presencial", "regime presencial",
    "híbrido", "hibrido", "hybrid", "modelo híbrido", "modelo hibrido",
    "trabalho híbrido", "vaga híbrida", "vaga hibrida", "on-site", "onsite",
    "residir em", "morar em", "residir na região", "residir na regiao",
    "visitas presenciais", "visita presencial", "atuação presencial", "atuacao presencial",
    "escritório presencial", "escritorio presencial", "disponibilidade para viagens",
    "disponibilidade para viagem", "alocado no cliente", "alocação no cliente",
    "dias presenciais", "dias no escritório", "dias no escritorio"
]

# ==========================================
# 5.4 EXCLUSÃO DE RUÍDOS NÃO TÉCNICOS / COMERCIAIS
# ==========================================
EXCLUDE_OTHER_KEYWORDS = [
    # Trabalhos físicos ou operacionais manuais
    "motorista", "cnh", "carteira d", "entregador", "faxina", "diarista", "garçom",
    
    # Vendas ativas, telemarketing e captação comercial
    "vendedor", "vendedora", "venda externa", "vendedor externo", "vendas ativas",
    "vendas online", "fechar vendas", "comercial ativo", "call center", "telemarketing",
    "cold call", "cold calling", "prospecção fria", "prospeccao fria", "venda de cursos",
    
    # Tráfego pago e afiliados
    "gestor de tráfego", "gestora de tráfego", "trafego pago", "facebook ads", "google ads",
    "bm facebook", "tiktok ads", "afiliado", "dropshipping", "cassino", "aposta",
    
    # Design gráfico e edição de mídia social
    "designer gráfico", "design gráfico", "edição de reels", "capcut", "social media",
    "post instagram", "canva", "edição de vídeo tiktok"
]

# União de todas as palavras de exclusão
EXCLUDE_KEYWORDS = (
    EXCLUDE_SENIORITY_KEYWORDS +
    EXCLUDE_PRESENTIAL_KEYWORDS +
    EXCLUDE_OTHER_KEYWORDS
)

# ==========================================
# 6. CONFIGURAÇÃO DE PRECIFICAÇÃO (MICROTAREFAS, PROJETOS E DÓLAR)
# ==========================================
PRICING_CONFIG = {
    "min_budget_brl": 50.00,        # Aceita microtarefas a partir de R$ 50
    "default_hourly_rate_brl": 45.00, # Valor hora para tarefas simples
    "tech_hourly_rate_brl": 85.00,    # Valor hora para projetos avançados
    "platform_fees": {
        "99freelas": 0.10,
        "workana": 0.15,
        "freelancer": 0.10,
        "linkedin": 0.0,
        "remoteok": 0.0,
        "weworkremotely": 0.0,
        "remotive": 0.0,
    }
}

PRICING_CONFIG_USD = {
    "min_budget_usd": 30.00,         # Aceita microtarefas em dólar a partir de $30
    "default_hourly_rate_usd": 20.00, # Valor hora tarefas simples em USD
    "tech_hourly_rate_usd": 45.00,    # Valor hora técnico em USD
    "platform_fees": {
        "workana": 0.15,
        "freelancer": 0.10,
        "linkedin": 0.0,
        "remoteok": 0.0,
        "weworkremotely": 0.0,
        "remotive": 0.0,
    }
}

# ==========================================
# 7. PARÂMETROS DE EXECUÇÃO, AUTO-SUBMIT E ANTI-BAN
# ==========================================
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "15"))
MAX_PROPOSALS_PER_JOB = 150          # Mais permissivo para permitir tarefas simples
SIMULATE_DRY_RUN = os.getenv("SIMULATE_DRY_RUN", "false").lower() == "true"

# Envio automático de propostas (Auto-bid)
AUTO_SUBMIT_PROPOSALS = os.getenv("AUTO_SUBMIT_PROPOSALS", "true").lower() == "true"
AUTO_SUBMIT_MIN_SCORE = int(os.getenv("AUTO_SUBMIT_MIN_SCORE", "65")) # Mais flexível
MAX_DAILY_PROPOSALS = int(os.getenv("MAX_DAILY_PROPOSALS", "15"))

# Expansão Internacional (Padrão: False - Foco estrito no Mercado Brasileiro)
ENABLE_INTERNATIONAL = os.getenv("ENABLE_INTERNATIONAL", "false").lower() == "true"
