"""
core/ai_proposal.py - Motor Inteligente de Geração de Propostas Bilíngue (PT-BR / EN)
Combina a API Gratuita do Gemini com um gerador contextual determinístico de alta conversão
baseado no portfólio real e trajetória de Ricson Ramos.
"""

import json
import urllib.request
from typing import Dict, Any, Optional
from config import PROFILE, GEMINI_API_KEY

class ProposalGenerator:
    """
    Gera propostas altamente personalizadas em Português ou Inglês.
    """

    @classmethod
    def generate(cls, job: Dict[str, Any], quote: Dict[str, Any]) -> str:
        """
        Gera proposta via Gemini (Free Tier) ou fallback nativo contextual.
        Detecta automaticamente se a vaga é internacional e se é não-especialista.
        """
        is_international = (
            job.get("is_international", False)
            or job.get("language") == "en"
            or job.get("platform") in ["remoteok", "weworkremotely", "remotive"]
            or quote.get("currency") in ["USD", "EUR", "GBP"]
        )
        is_micro = (quote.get("tier") == "TIER_0_MICRO") or cls._is_non_specialist(job)

        if GEMINI_API_KEY and len(GEMINI_API_KEY.strip()) > 10:
            ai_proposal = cls._generate_with_gemini(job, quote, is_international, is_micro)
            if ai_proposal:
                return ai_proposal

        if is_international:
            return cls._generate_english_proposal(job, quote, is_micro)
        return cls._generate_portuguese_proposal(job, quote, is_micro)

    @classmethod
    def _is_non_specialist(cls, job: Dict[str, Any]) -> bool:
        text = f"{job.get('title', '')} {job.get('description', '')}".lower()
        non_spec_terms = [
            "digitação", "digitacao", "digitador", "digitadora", "data entry", "entrada de dados",
            "planilha", "excel", "sheets", "atendimento", "suporte", "sac", "chat", "whatsapp",
            "assistente virtual", "virtual assistant", "transcrição", "transcricao", "preenchimento",
            "cadastro", "copiar e colar", "copy paste", "web research", "pesquisa na web"
        ]
        tech_terms = ["python", "sql", "postgresql", "fastapi", "dbt", "docker", "mlops", "machine learning", "xgboost"]
        has_non_spec = any(w in text for w in non_spec_terms)
        has_tech = any(w in text for w in tech_terms)
        return has_non_spec and not has_tech

    @classmethod
    def _generate_with_gemini(cls, job: Dict[str, Any], quote: Dict[str, Any], is_international: bool = False, is_micro: bool = False) -> Optional[str]:
        """
        Chama o endpoint gratuito do Google Gemini 1.5 Flash via REST puro.
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        symbol = quote.get("currency_symbol", "R$")

        if is_international:
            system_instruction = f"""
You are the technical sales agent representing Ricson Ramos ({PROFILE['portfolio_url']}).
Ricson is a Data Science Technologist with 10+ years of operational intelligence, cybersecurity, and risk analysis background.
Core Specializations: Data Science & Machine Learning (XGBoost/Streamlit), OSINT & Threat Intelligence, Python Automation & Web Scraping, and Backend APIs (FastAPI/Docker/PostgreSQL).

PROPOSAL WRITING RULES:
1. NEVER start with generic cliches like "Hello, I read your job post with interest".
2. Open IMMEDIATELY with a sharp technical diagnosis of their requirements.
3. Outline a 3-bullet practical solution architecture tailored to their problem.
4. Reference one of Ricson's real open-source GitHub projects:
   - Data Science / ML: Streaming Churn Radar (native XGBoost + Streamlit ROI business simulator).
   - OSINT / Cybersecurity: Automated OSINT pipelines, entity resolution, and threat intelligence.
   - Scraping / Automation: Production-grade scrapers with exception handling, anti-bot evasion, and structured export.
   - ETL / Analytics: Olist Data Platform (dbt Core + PostgreSQL + Docker).
   - APIs / Backend: MacroPulse Intelligence (asynchronous FastAPI).
5. State the estimated timeline ({quote['delivery_days']} business days) and proposed quote ({symbol}{quote['platform_bid_price']:.2f}).
6. End with a straightforward call to action for a quick technical alignment.
7. Write in fluent, concise, native-level English (under 180 words).
"""
        else:
            system_instruction = f"""
Você é o assistente técnico de vendas de Ricson Ramos ({PROFILE['portfolio_url']}).
Ricson é Tecnólogo em Ciência de Dados com mais de 10 anos de histórico em inteligência operacional, análise de risco e missões críticas.
Especialidades: Ciência de Dados & Machine Learning (XGBoost/Streamlit), OSINT & Cibersegurança, Automação Avançada com Python (Scraping/Bots) e Engenharia de Backend (FastAPI/Docker/PostgreSQL).

REGRAS RÍGIDAS DESTA PROPOSTA:
1. NUNCA use clichês como "Olá! Li seu anúncio com grande interesse".
2. Comece a PRIMEIRA frase direto no diagnóstico técnico da dor do cliente.
3. Apresente em 3 tópicos numerados a arquitetura de solução prática.
4. Cite exatamente o projeto de Ricson mais alinhado à demanda:
   - Data Science / ML: Streaming Churn Radar (XGBoost nativo + simulador de ROI em Streamlit).
   - OSINT / Cibersegurança: Pipelines automatizados de inteligência de fontes abertas e mitigação de risco.
   - Automação / Scraping: Scripts Python resilientes com evasão anti-bloqueio e entrega estruturada.
   - Engenharia de Dados / SQL: Olist Data Platform com dbt Core, PostgreSQL e testes.
   - APIs / Backend: Terminal MacroPulse com FastAPI assíncrona.
5. Mencione o prazo estimado de {quote['delivery_days']} dias úteis e o valor de {symbol} {quote['platform_bid_price']:.2f}.
6. Finalize com chamada objetiva para alinhamento técnico.
7. Escreva em Português fluente e altamente profissional (máximo 180 palavras).
"""

        prompt = f"""
JOB DETAILS:
Title: {job.get('title', '')}
Description: {job.get('description', '')[:1000]}
Quote: {symbol}{quote['platform_bid_price']:.2f}
Delivery: {quote['delivery_days']} days
"""

        payload = {
            "contents": [{"parts": [{"text": f"{system_instruction}\n\n{prompt}"}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 600}
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"⚠️ Gemini indisponível ({e}). Usando gerador contextual nativo.")
            return None

    @classmethod
    def _generate_portuguese_proposal(cls, job: Dict[str, Any], quote: Dict[str, Any], is_micro: bool = False) -> str:
        """Gerador contextual em Português."""
        title = job.get("title", "")
        desc = job.get("description", "")
        full_text = f"{title} {desc}".lower()
        symbol = quote.get("currency_symbol", "R$")

        if is_micro:
            return f"""Olá! Analisei sua solicitação para "{title}" e tenho disponibilidade imediata para realizar esta demanda com máxima agilidade, precisão e total atenção aos detalhes.

Minha entrega contempla:
1. Execução Precisa e Sem Falhas: Cumprimento rigoroso das suas orientações e padrões de formatação, com dupla conferência para garantir precisão absoluta.
2. Domínio Operacional: Uso avançado de Excel, Google Sheets, processamento de texto e ferramentas de comunicação rápida.
3. Compromisso e Confiabilidade: Pontualidade estrita no prazo combinado e sigilo total dos seus dados e arquivos.

• Prazo de Entrega: {quote['delivery_days']} dia(s) útil(eis)
• Orçamento Proposto: {symbol} {quote['platform_bid_price']:.2f}

Estou à disposição no chat para receber as instruções e iniciar o trabalho imediatamente!"""

        if any(w in full_text for w in ["osint", "cybersecurity", "cibersegurança", "segurança", "pentest", "vulnerabilidade", "threat", "forense", "infosec"]):
            selected_case = PROFILE["featured_projects"]["osint_intel"]
            solution_summary = "coleta investigativa e estruturada com técnicas avançadas de OSINT, mapeamento de superfície e protocolos rígidos de segurança da informação"
        elif any(w in full_text for w in ["churn", "mlops", "machine learning", "xgboost", "prediç", "risco", "ciência de dados", "data science"]):
            selected_case = PROFILE["featured_projects"]["churn_radar"]
            solution_summary = "implementação de modelo preditivo com métricas de negócio claras e visualização interativa"
        elif any(w in full_text for w in ["dbt", "sql", "postgresql", "elt", "etl", "banco", "modelagem"]):
            selected_case = PROFILE["featured_projects"]["olist_platform"]
            solution_summary = "arquitetura de dados auditável com modelagem analítica, integridade e queries otimizadas"
        elif any(w in full_text for w in ["api", "fastapi", "backend", "microsserviço", "integrar"]):
            selected_case = PROFILE["featured_projects"]["macropulse"]
            solution_summary = "construção de API assíncrona de alta performance com endpoints documentados e validação estrita"
        else:
            selected_case = {
                "title": "Pipelines de Automação & Ingestão em Python",
                "url": PROFILE["github_url"],
                "desc": "Scripts resilientes com tratamento de falhas, paginação, rotação de headers e entrega estruturada."
            }
            solution_summary = "automação e extração limpa de dados garantindo integridade e conformidade de execução"

        return f"""Olá! Analisei sua demanda para "{title}" e posso implementar exatamente a solução necessária com foco em estabilidade e entrega rápida.

Minha proposta para este projeto contempla:
1. Arquitetura da Solução: Desenvolvimento com Python e padrões de código limpo, incluindo validação automática de dados e tratamento de exceções.
2. {solution_summary.capitalize()}.
3. Entrega Pronta para Execução: Código documentado passo a passo e preparado para rodar em seu ambiente (ou conteinerizado via Docker).

Para referência prática da qualidade das minhas entregas, desenvolvi o projeto "{selected_case['title']}" ({selected_case['desc']}), disponível com código aberto em:
👉 {selected_case['url']}

Portfólio Completo: {PROFILE['portfolio_url']}
• Prazo de Entrega: {quote['delivery_days']} dias úteis
• Orçamento Proposto: {symbol} {quote['platform_bid_price']:.2f}

Podemos alinhar os detalhes técnicos específicos e acessos necessários via chat para que eu inicie imediatamente!"""

    @classmethod
    def _generate_english_proposal(cls, job: Dict[str, Any], quote: Dict[str, Any], is_micro: bool = False) -> str:
        """Gerador contextual em Inglês para vagas internacionais."""
        title = job.get("title", "")
        desc = job.get("description", "")
        full_text = f"{title} {desc}".lower()
        symbol = quote.get("currency_symbol", "$")

        if is_micro:
            return f"""Hi there! I reviewed your project requirements for "{title}" and I am available to start immediately, delivering with high accuracy and fast turnaround.

What I bring to your project:
1. Accurate & Timely Execution: Strict adherence to your guidelines, format requirements, and quality standards, with thorough double-checking.
2. Tool Mastery: Advanced proficiency in Excel, Google Sheets, documents, web research, and prompt remote communication.
3. Reliability & Confidentiality: 100% committed to your deadline and complete discretion with your data.

• Estimated Delivery: {quote['delivery_days']} business day(s)
• Proposed Budget: {symbol}{quote['platform_bid_price']:.2f}

I am ready to review your files/guidelines and start right now. Looking forward to your message!"""

        if any(w in full_text for w in ["osint", "cybersecurity", "security", "pentest", "vulnerability", "threat", "forensic", "infosec"]):
            selected_case = PROFILE["featured_projects"]["osint_intel"]
            solution_summary = "open-source intelligence (OSINT) gathering, entity mapping, and rigorous information security protocols"
        elif any(w in full_text for w in ["churn", "mlops", "machine learning", "xgboost", "predict", "model", "data science"]):
            selected_case = PROFILE["featured_projects"]["churn_radar"]
            solution_summary = "predictive ML model implementation with business-focused metrics and interactive simulation"
        elif any(w in full_text for w in ["dbt", "sql", "postgres", "elt", "etl", "warehouse", "analytics"]):
            selected_case = PROFILE["featured_projects"]["olist_platform"]
            solution_summary = "audit-ready modern data pipeline with dimensional modeling, data integrity tests, and SQL optimization"
        elif any(w in full_text for w in ["api", "fastapi", "backend", "microservice", "integration"]):
            selected_case = PROFILE["featured_projects"]["macropulse"]
            solution_summary = "high-performance asynchronous REST API with auto-generated Swagger documentation and type validation"
        else:
            selected_case = {
                "title": "Python Automation & Resilient Scrapers",
                "url": PROFILE["github_url"],
                "desc_en": "Production-grade automated pipelines with robust error handling, rate limiting, and clean structured storage."
            }
            solution_summary = "end-to-end automation and clean data extraction ensuring reliable unattended execution"

        case_desc = selected_case.get("desc_en", selected_case.get("desc", ""))

        return f"""Hi there! I reviewed your project requirements for "{title}" and I can deliver a resilient, clean, and production-ready solution tailored directly to your workflow.

Key execution pillars for this project:
1. Architecture & Clean Code: Modular Python development with typed interfaces, automatic validation, and comprehensive error handling.
2. Core Delivery: {solution_summary.capitalize()}.
3. Turnkey Handover: Thoroughly documented code prepared for your environment, including containerization (Docker) to guarantee zero setup headaches.

As practical proof of my work standards, feel free to inspect my open-source repository "{selected_case['title']}" ({case_desc}):
👉 {selected_case['url']}

Executive Portfolio: {PROFILE['portfolio_url']}
• Estimated Delivery: {quote['delivery_days']} business days
• Proposed Rate/Budget: {symbol}{quote['platform_bid_price']:.2f}

I am ready to align on the technical specifications and get started immediately. Looking forward to discussing further!"""
