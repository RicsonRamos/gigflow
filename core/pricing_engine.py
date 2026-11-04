"""
core/pricing_engine.py - Motor de Orçamentos e Precificação Dinâmica (Nacional R$ e Internacional US$)
Calcula automaticamente horas estimadas, complexidade do projeto, prazo de entrega e
embutimento das taxas da plataforma para garantir a rentabilidade líquida desejada.
"""

import re
from typing import Dict, Any
from config import PRICING_CONFIG, PRICING_CONFIG_USD

class PricingEngine:
    TIER_0 = "TIER_0_MICRO"          # Tarefas simples: Digitação, Planilhas, Transcrição, Atendimento, SAC, Pesquisa Web
    TIER_1 = "TIER_1_SIMPLES"        # Scripts pontuais, raspadores simples, automação de dados
    TIER_2 = "TIER_2_INTERMEDIARIO"  # Dashboards Streamlit, Pipelines dbt/Postgres, APIs FastAPI
    TIER_3 = "TIER_3_AVANCADO"       # Soluções completas: MLOps, Modelagem Preditiva, Docker, Risco

    ADVANCED_INDICATORS = [
        "mlops", "machine learning", "xgboost", "modelo preditivo", "fraude", "churn",
        "arquitetura", "lakehouse", "data warehouse", "cluster", "produção", "docker-compose",
        "deep learning", "llm", "fine-tuning", "agent", "langchain", "rag",
        "osint", "cybersecurity", "cibersegurança", "pentest", "vulnerabilidade",
        "threat intelligence", "forense", "ethical hacking", "infosec", "security"
    ]
    INTERMEDIATE_INDICATORS = [
        "dashboard", "streamlit", "power bi", "fastapi", "dbt", "postgresql", "sql",
        "api rest", "banco de dados", "pipeline", "etl", "elt", "automação completa",
        "backend", "scraping", "crawler", "selenium", "playwright", "bot", "crawler",
        "automacao", "automation", "raspagem", "django", "flask"
    ]
    MICRO_INDICATORS = [
        "digitação", "digitacao", "digitador", "digitadora", "data entry", "entrada de dados",
        "cadastro de produtos", "cadastrar produtos", "cadastramento", "copiar e colar", "copy paste",
        "preenchimento", "organização de dados", "alimentar sistema", "inserir dados",
        "transcrição", "transcricao", "transcrever áudio", "transcrever video", "transcrever",
        "assistente virtual", "virtual assistant", "atendimento", "suporte ao cliente", "customer support",
        "customer service", "helpdesk", "sac", "chat", "whatsapp", "respondente", "secretariado",
        "secretaria", "pesquisa na web", "web research", "coleta de contatos", "lista de contatos",
        "revisão de texto", "revisao de texto", "microtarefa", "tarefas simples"
    ]

    @classmethod
    def evaluate_complexity(cls, title: str, description: str) -> str:
        text = f"{title} {description}".lower()

        for word in cls.ADVANCED_INDICATORS:
            if word in text:
                return cls.TIER_3

        for word in cls.INTERMEDIATE_INDICATORS:
            if word in text:
                return cls.TIER_2

        for word in cls.MICRO_INDICATORS:
            if word in text:
                return cls.TIER_0

        return cls.TIER_1

    @classmethod
    def calculate_quote(cls, title: str, description: str, platform: str = "99freelas", currency: str = "BRL") -> Dict[str, Any]:
        """
        Retorna o orçamento detalhado (bruto, líquido, comissão da plataforma, horas e prazo).
        Suporta cotação em Real (BRL), Dólar (USD), Euro (EUR) e Libra (GBP).
        """
        tier = cls.evaluate_complexity(title, description)
        curr_upper = currency.upper()

        if curr_upper in ["USD", "EUR", "GBP"] or (platform.lower() in ["remoteok", "weworkremotely", "remotive"]):
            symbol = "€" if curr_upper == "EUR" else ("£" if curr_upper == "GBP" else "$")
            curr_code = curr_upper if curr_upper in ["USD", "EUR", "GBP"] else "USD"
            hourly_rate = (
                PRICING_CONFIG_USD.get("default_hourly_rate_usd", 20.00)
                if tier == cls.TIER_0
                else PRICING_CONFIG_USD.get("tech_hourly_rate_usd", 45.00)
            )
            fee_rate = PRICING_CONFIG_USD.get("platform_fees", {}).get(platform.lower(), 0.0)

            tier_settings = {
                cls.TIER_0: {
                    "label": "Micro-task / Remote Support & Data Entry",
                    "hours": 3,
                    "days": 1,
                    "base_price": 35.00
                },
                cls.TIER_1: {
                    "label": "Simple / Script & Scraping",
                    "hours": 6,
                    "days": 2,
                    "base_price": 180.00
                },
                cls.TIER_2: {
                    "label": "Intermediate / Pipeline & Dashboard",
                    "hours": 20,
                    "days": 5,
                    "base_price": 750.00
                },
                cls.TIER_3: {
                    "label": "Advanced / Architecture & ML/AI",
                    "hours": 45,
                    "days": 10,
                    "base_price": 2000.00
                }
            }
        else:
            symbol = "R$"
            curr_code = "BRL"
            hourly_rate = (
                PRICING_CONFIG.get("default_hourly_rate_brl", 45.00)
                if tier == cls.TIER_0
                else PRICING_CONFIG.get("tech_hourly_rate_brl", 85.00)
            )
            fee_rate = PRICING_CONFIG.get("platform_fees", {}).get(platform.lower(), 0.10)

            tier_settings = {
                cls.TIER_0: {
                    "label": "Microtarefa / Suporte Remoto & Digitação",
                    "hours": 3,
                    "days": 1,
                    "base_price": 80.00
                },
                cls.TIER_1: {
                    "label": "Simples / Automação Pontual",
                    "hours": 6,
                    "days": 2,
                    "base_price": 350.00
                },
                cls.TIER_2: {
                    "label": "Intermediário / Engenharia & Dashboard",
                    "hours": 20,
                    "days": 5,
                    "base_price": 1600.00
                },
                cls.TIER_3: {
                    "label": "Avançado / Arquitetura & Machine Learning",
                    "hours": 45,
                    "days": 12,
                    "base_price": 3800.00
                }
            }

        config = tier_settings[tier]
        hours = config["hours"]
        days = config["days"]

        suggested_net = max(config["base_price"], hours * hourly_rate)
        
        # Embutimento da comissão da plataforma
        if fee_rate > 0 and fee_rate < 1.0:
            platform_bid = suggested_net / (1.0 - fee_rate)
        else:
            platform_bid = suggested_net
        platform_fee_amount = platform_bid - suggested_net

        return {
            "tier": tier,
            "tier_label": config["label"],
            "currency": curr_code,
            "currency_symbol": symbol,
            "estimated_hours": hours,
            "delivery_days": days,
            "net_receivable": round(suggested_net, 2),
            "platform_bid_price": round(platform_bid, 2),
            "platform_fee_rate": fee_rate,
            "platform_fee_amount": round(platform_fee_amount, 2),
            "summary_text": (
                f"{symbol} {platform_bid:,.2f} bruto (Líquido: {symbol} {suggested_net:,.2f}) "
                f"| Prazo: {days} dias úteis | Estimativa: {hours}h"
            )
        }
