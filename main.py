"""
main.py - Orquestrador Central do GigFlow
Autor: Ricson Ramos
Executa a busca nacional e internacional, triagem algorítmica, orçamentação dinâmica,
propostas bilíngues com IA, envio automático de propostas e sincronização com Telegram & Notion.
"""

import sys
from pathlib import Path

# Garante inclusão no sys.path para execução direta ou modular
BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import time
import argparse
import asyncio
from typing import List

from config import (
    SCRAPE_INTERVAL_MINUTES,
    AUTO_SUBMIT_PROPOSALS,
    AUTO_SUBMIT_MIN_SCORE,
    MAX_DAILY_PROPOSALS,
    SIMULATE_DRY_RUN,
    ENABLE_INTERNATIONAL
)
from core.database import (
    is_job_seen,
    save_job,
    update_job_status,
    count_today_submitted_proposals
)
from core.pricing_engine import PricingEngine
from core.ai_proposal import ProposalGenerator
from core.notion_crm import NotionCRM
from core.auth_manager import record_session
from platforms.noventa_nove_freelas import NoventaNoveFreelas
from platforms.workana import WorkanaPlatform
from platforms.remoteok import RemoteOKPlatform
from platforms.weworkremotely import WeWorkRemotelyPlatform
from platforms.remotive import RemotivePlatform
from platforms.freelancer import FreelancerPlatform
from platforms.linkedin import LinkedInPlatform
from bot.telegram_bot import TelegramCopilot

def get_active_platforms() -> list:
    # Plataformas Focadas no Mercado Brasileiro (Remoto / PJ / Estágio / Júnior / Freela)
    platforms = [
        NoventaNoveFreelas(),
        WorkanaPlatform(),
        LinkedInPlatform()
    ]
    # Plataformas Internacionais em Dólar / Euro (Habilitadas apenas se ENABLE_INTERNATIONAL=True)
    if ENABLE_INTERNATIONAL:
        platforms.append(FreelancerPlatform())
        platforms.append(RemoteOKPlatform())
        platforms.append(RemotivePlatform())
        platforms.append(WeWorkRemotelyPlatform())
    return platforms

def run_scan(force_auto_submit: bool = False):
    """
    Executa um ciclo completo de varredura, pontuação, orçamentação e despacho de propostas.
    """
    intl_msg = "Nacional & Internacional (USD)" if ENABLE_INTERNATIONAL else "Nacional"
    print(f"\n🔍 Iniciando varredura de oportunidades ({intl_msg})...")

    auto_submit_enabled = force_auto_submit or AUTO_SUBMIT_PROPOSALS
    daily_submitted = count_today_submitted_proposals()
    
    if auto_submit_enabled and not SIMULATE_DRY_RUN:
        print(f"⚡ MODO ENVIO AUTOMÁTICO ATIVO: Min Score {AUTO_SUBMIT_MIN_SCORE}% | Limite Diário: {daily_submitted}/{MAX_DAILY_PROPOSALS}")
    elif SIMULATE_DRY_RUN:
        print("🧪 MODO SIMULAÇÃO (DRY-RUN) ATIVO: Lances serão simulados sem submissão real.")

    platforms = get_active_platforms()
    total_scanned = 0
    total_matched = 0
    total_auto_submitted = 0

    for platform in platforms:
        print(f"📡 Varrendo {platform.name.upper()}...")
        jobs = platform.fetch_jobs()
        total_scanned += len(jobs)

        for job in jobs:
            job_id = job["id"]

            # Evita reprocessar vagas já visualizadas
            if is_job_seen(job_id):
                continue

            # Avalia compatibilidade com o perfil de Ricson
            approved, score, reason = platform.evaluate_job_match(job)
            if not approved or score < 40:
                continue

            total_matched += 1
            curr = job.get("currency", "BRL")
            intl_badge = " 🌎 [INTERNACIONAL]" if job.get("is_international") else ""
            print(f"\n🎯 [MATCH {score}%]{intl_badge} {job['title']}")
            print(f"   Motivo: {reason}")
            print(f"   URL: {job['url']}")

            # Calcula orçamento e prazo de acordo com a complexidade e moeda
            quote = PricingEngine.calculate_quote(
                job["title"],
                job["description"],
                platform=platform.name,
                currency=curr
            )

            # Gera a proposta personalizada (PT ou EN)
            proposal_text = ProposalGenerator.generate(job, quote)

            # Salva no banco de dados local
            save_job(job, score, quote, proposal_text, status="NEW")

            # Checagem de Elegibilidade para Auto-Submit:
            can_auto_submit = (
                auto_submit_enabled
                and not SIMULATE_DRY_RUN
                and score >= AUTO_SUBMIT_MIN_SCORE
                and (daily_submitted + total_auto_submitted) < MAX_DAILY_PROPOSALS
            )

            if can_auto_submit:
                print(f"   🚀 Qualificação alta ({score}% >= {AUTO_SUBMIT_MIN_SCORE}%). Enviando proposta automaticamente...")
                try:
                    success = asyncio.run(platform.submit_proposal(
                        job["url"],
                        proposal_text,
                        quote["platform_bid_price"],
                        quote["delivery_days"]
                    ))
                except Exception as err:
                    print(f"   ⚠️ Erro na submissão automática: {err}")
                    success = False

                if success:
                    total_auto_submitted += 1
                    update_job_status(job_id, "SENT")

                    # Cria registro no Notion CRM
                    if NotionCRM.is_configured():
                        page_id = NotionCRM.create_project_card(job, quote, proposal_text, status="Proposta Enviada")
                        update_job_status(job_id, "SENT", page_id)

                    # Alerta imediato no Telegram informando o envio
                    TelegramCopilot.send_auto_submitted_alert(job, quote, proposal_text, score)
                else:
                    # Se falhar a submissão direta, envia card interativo para aprovação manual
                    TelegramCopilot.send_job_alert(job, quote, proposal_text, score)
            else:
                # Envia card interativo no Telegram para aprovação em 1 clique
                TelegramCopilot.send_job_alert(job, quote, proposal_text, score)

    print(f"\n🏁 Varredura concluída. Vagas analisadas: {total_scanned} | Oportunidades: {total_matched} | Auto-enviadas: {total_auto_submitted}")

def run_daemon():
    """
    Executa o monitoramento contínuo em intervalos regulares e mantém o bot ativo.
    """
    print("🚀 Iniciando Modo Daemon (Monitoramento Contínuo + Bot Telegram)...")
    import threading

    # Inicia o bot do Telegram em thread paralela se configurado
    if TelegramCopilot.is_configured():
        bot_thread = threading.Thread(target=TelegramCopilot.run_polling, daemon=True)
        bot_thread.start()
    else:
        print("⚠️ Telegram não configurado no .env. Alertas serão impressos apenas no terminal.")

    while True:
        try:
            run_scan()
        except Exception as e:
            print(f"❌ Erro durante o ciclo de varredura: {e}")

        print(f"💤 Aguardando {SCRAPE_INTERVAL_MINUTES} minutos até o próximo ciclo...")
        time.sleep(SCRAPE_INTERVAL_MINUTES * 60)

def main():
    parser = argparse.ArgumentParser(description="GigFlow - Autonomous Freelance Intelligence & Automated Bidding Engine")
    parser.add_argument("--scan", action="store_true", help="Executa uma única varredura de vagas")
    parser.add_argument("--daemon", action="store_true", help="Executa monitoramento contínuo e polling do Telegram")
    parser.add_argument("--bot", action="store_true", help="Inicia somente o bot do Telegram")
    parser.add_argument("--login", type=str, choices=["99freelas", "workana", "linkedin"], help="Abre navegador para salvar sessão de login")
    parser.add_argument("--manual", action="store_true", help="Permite colar cookies/tokens manualmente caso o Cloudflare bloqueie o navegador")
    parser.add_argument("--test-notion", action="store_true", help="Testa conexão com o banco do Notion")
    parser.add_argument("--test-telegram", action="store_true", help="Testa o token do bot e envia mensagem no Telegram")
    parser.add_argument("--auto-submit", action="store_true", help="Força envio automático de propostas com match qualificado nesta execução")

    args = parser.parse_args()

    if args.test_telegram:
        TelegramCopilot.test_connection()
    elif args.login:
        asyncio.run(record_session(args.login, manual=args.manual))
    elif args.test_notion:
        NotionCRM.test_connection()
    elif args.bot:
        TelegramCopilot.run_polling()
    elif args.daemon:
        run_daemon()
    else:
        # Por padrão, executa uma varredura
        run_scan(force_auto_submit=args.auto_submit)

if __name__ == "__main__":
    main()
