"""
bot/telegram_bot.py - Bot Interativo Human-in-the-Loop & Alertas Automáticos (Telegram)
Permite ao Ricson:
1. Receber alertas de vagas com cards interativos.
2. Enviar propostas direto do Telegram com 1 clique (Auto-submit no 99Freelas e Workana).
3. Ver a proposta completa formatada para cópia instantânea no celular.
4. Executar comandos de chat (/scan, /pendentes, /status, /enviar, /ajuda).
5. Sincronizar automaticamente com Notion CRM e banco local.
"""

import json
import time
import asyncio
import threading
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, List

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MAX_DAILY_PROPOSALS, AUTO_SUBMIT_PROPOSALS, SIMULATE_DRY_RUN
from core.database import get_job, update_job_status, get_pending_jobs, get_database_stats
from core.notion_crm import NotionCRM
from platforms.noventa_nove_freelas import NoventaNoveFreelas
from platforms.workana import WorkanaPlatform

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

class TelegramCopilot:
    @classmethod
    def is_configured(cls) -> bool:
        return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

    @classmethod
    def _api_call(cls, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not cls.is_configured():
            return None

        url = f"{API_BASE}/{endpoint}"
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            print(f"⚠️ Erro ao chamar Telegram API ({endpoint}): HTTP {e.code} - {err_body}")
            return None
        except Exception as e:
            print(f"⚠️ Erro ao chamar Telegram API ({endpoint}): {e}")
            return None

    @classmethod
    def send_notification(cls, text: str) -> bool:
        """Envia mensagem direta de texto/notificação ao usuário."""
        if not cls.is_configured():
            return False
        res = cls._api_call("sendMessage", {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        })
        return bool(res and res.get("ok"))

    @classmethod
    def send_auto_submitted_alert(cls, job: Dict[str, Any], quote: Dict[str, Any], proposal_text: str, match_score: int):
        """
        Envia confirmação imediata quando uma proposta é enviada automaticamente.
        """
        if not cls.is_configured():
            print(f"🚀 [AUTO-ENVIADO] {job['title']} ({quote.get('currency_symbol', 'R$')}{quote.get('platform_bid_price', 0):.2f})")
            return

        symbol = quote.get("currency_symbol", "R$")
        intl_tag = " 🌎 INTERNACIONAL" if job.get("is_international") else ""
        
        text = f"""⚡ *PROPOSTA ENVIADA AUTOMATICAMENTE*{intl_tag}
━━━━━━━━━━━━━━━━━━━━━━━━
📌 *{job.get('title', '')}*
🏢 Plataforma: *{job.get('platform', '').upper()}*
🎯 *Match Score:* {match_score}% (Qualificação Alta)

💰 *Orçamento Proposto:*
• Valor: *{symbol} {quote.get('platform_bid_price', 0.0):.2f}* ({quote.get('currency', 'BRL')})
• Prazo: *{quote.get('delivery_days', 0)} dias úteis* ({quote.get('estimated_hours', 0)}h)

📝 *Texto do Lance Enviado:*
_{proposal_text[:300]}..._

🔗 [Acessar Vaga na Plataforma]({job.get('url', '')})
━━━━━━━━━━━━━━━━━━━━━━━━
✅ *Status:* Registrado no Notion CRM e salvo no histórico local."""

        inline_keyboard = {
            "inline_keyboard": [
                [{"text": "🌐 Abrir Vaga no Navegador", "url": job.get("url", "https://google.com")}]
            ]
        }

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "reply_markup": inline_keyboard
        }

        res = cls._api_call("sendMessage", payload)
        if res and res.get("ok"):
            print(f"📲 Alerta de proposta enviada entregue no Telegram: '{job.get('title', '')[:30]}...'")

    @classmethod
    def send_job_alert(cls, job: Dict[str, Any], quote: Dict[str, Any], proposal_text: str, match_score: int):
        """
        Envia o card da vaga para o Telegram com botões interativos de 1 clique.
        """
        if not cls.is_configured():
            print(f"ℹ️ Telegram não configurado. Vaga detectada: {job['title']}")
            return

        job_id = job["id"]
        symbol = quote.get("currency_symbol", "R$")
        intl_tag = " 🌎 INTERNACIONAL" if job.get("is_international") else ""

        cb_send = f"s:{job_id}"[:64]
        cb_view = f"v:{job_id}"[:64]
        cb_notion = f"n:{job_id}"[:64]
        cb_discard = f"d:{job_id}"[:64]

        text = f"""🚨 *NOVA OPORTUNIDADE DETECTADA*{intl_tag} ({job.get('platform', 'Freela').upper()})
━━━━━━━━━━━━━━━━━━━━━━━━
📌 *{job.get('title', '')}*
🎯 *Match Score:* {match_score}%
👥 *Concorrência:* {job.get('proposals_count', 0)} propostas

💰 *Orçamento Calculado:*
• Bruto: *{symbol} {quote.get('platform_bid_price', 0.0):.2f}*
• Líquido Estimado: *{symbol} {quote.get('net_receivable', 0.0):.2f}*
• Prazo Sugerido: *{quote.get('delivery_days', 0)} dias úteis* ({quote.get('estimated_hours', 0)}h)

📝 *Prévia da Proposta:*
_{proposal_text[:280]}..._

🔗 [Ver vaga na íntegra]({job.get('url', '')})
━━━━━━━━━━━━━━━━━━━━━━━━"""

        inline_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🚀 Enviar Proposta", "callback_data": cb_send},
                    {"text": "📝 Ver Proposta", "callback_data": cb_view}
                ],
                [
                    {"text": "📋 Notion CRM", "callback_data": cb_notion},
                    {"text": "❌ Descartar", "callback_data": cb_discard}
                ],
                [
                    {"text": "🌐 Abrir Vaga no Navegador", "url": job.get("url", "")}
                ]
            ]
        }

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "reply_markup": inline_keyboard
        }

        res = cls._api_call("sendMessage", payload)
        if res and res.get("ok"):
            print(f"📲 Alerta enviado para o Telegram: '{job.get('title', '')[:30]}...'")

    @classmethod
    def test_connection(cls):
        """Testa o token do bot e envia mensagem de boas-vindas com auto-detecção de Chat ID."""
        if not TELEGRAM_BOT_TOKEN:
            print("❌ TELEGRAM_BOT_TOKEN não preenchido no .env!")
            return False

        url_me = f"{API_BASE}/getMe"
        try:
            with urllib.request.urlopen(url_me, timeout=10) as r:
                bot_info = json.loads(r.read().decode())
                username = bot_info["result"]["username"]
                print(f"✅ Bot encontrado: @{username}")
        except Exception as e:
            print(f"❌ Erro ao validar token do bot: {e}")
            return False

        detected_chat_id = None
        url_updates = f"{API_BASE}/getUpdates"
        try:
            with urllib.request.urlopen(url_updates, timeout=10) as r:
                updates = json.loads(r.read().decode()).get("result", [])
                if updates:
                    latest = updates[-1]
                    sender = latest.get("message", {}).get("from", {})
                    detected_chat_id = str(latest.get("message", {}).get("chat", {}).get("id"))
                    if detected_chat_id:
                        print(f"📡 Mensagem detectada de @{sender.get('username', 'usuario')} (Chat ID: {detected_chat_id})")
        except Exception:
            pass

        target_chat_id = detected_chat_id or TELEGRAM_CHAT_ID

        test_msg = (
            "🤖 *Freelance Copilot Online!*\n\n"
            "Conexão com o Telegram estabelecida com sucesso.\n"
            "• Alertas de vagas: *Ativados*\n"
            "• Mercado Internacional: *Ativado*\n"
            "• Envio Direto via Telegram: *Ativado*\n\n"
            "Digite /ajuda para ver o menu de comandos rápidos."
        )
        res = cls._api_call("sendMessage", {
            "chat_id": target_chat_id,
            "text": test_msg,
            "parse_mode": "Markdown"
        })

        if res and res.get("ok"):
            print(f"🎉 Mensagem de teste enviada com sucesso para o Chat ID {target_chat_id}!")
            return True
        else:
            print(f"\n⚠️ O Telegram não permitiu o envio para o Chat ID {target_chat_id}.")
            return False

    @classmethod
    def run_polling(cls):
        """Loop contínuo de long polling para responder aos botões e mensagens do Telegram."""
        if not cls.is_configured():
            print("❌ TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não definidos no .env")
            return

        print("🤖 Bot Telegram Copilot ativo e aguardando comandos e aprovações...")
        last_update_id = 0

        # Sincroniza com as mensagens mais recentes para evitar callbacks expirados
        try:
            init_url = f"{API_BASE}/getUpdates?offset=-1"
            with urllib.request.urlopen(init_url, timeout=10) as resp:
                init_data = json.loads(resp.read().decode("utf-8"))
                updates = init_data.get("result", [])
                if updates:
                    last_update_id = updates[-1]["update_id"]
                    print(f"📡 Sincronizado com Telegram (Offset: {last_update_id})")
        except Exception as e:
            print(f"⚠️ Aviso na sincronização inicial: {e}")

        while True:
            try:
                url = f"{API_BASE}/getUpdates?offset={last_update_id + 1}&timeout=30"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=35) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    updates = data.get("result", [])

                    for update in updates:
                        last_update_id = update["update_id"]
                        try:
                            if "callback_query" in update:
                                cls._handle_callback(update["callback_query"])
                            elif "message" in update:
                                cls._handle_message(update["message"])
                        except Exception as err:
                            print(f"⚠️ Erro ao processar update {last_update_id}: {err}")

            except Exception as e:
                time.sleep(3)

    @classmethod
    def _handle_message(cls, msg: Dict[str, Any]):
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "").strip()

        if not text:
            return

        cmd = text.split()[0].lower()

        if cmd in ["/start", "/ajuda", "/help"]:
            cls._send_help_menu(chat_id)
        elif cmd == "/scan":
            cls._handle_scan_command(chat_id)
        elif cmd == "/pendentes":
            cls._handle_pendentes_command(chat_id)
        elif cmd == "/status":
            cls._handle_status_command(chat_id)
        elif cmd.startswith("/enviar"):
            parts = text.split()
            if len(parts) > 1:
                cls._handle_enviar_command(chat_id, parts[1])
            else:
                cls._api_call("sendMessage", {
                    "chat_id": chat_id,
                    "text": "ℹ️ Use: `/enviar <id_da_vaga>`\nExemplo: `/enviar 99freelas_795898`\nOu digite `/pendentes` para ver a lista de vagas prontas.",
                    "parse_mode": "Markdown"
                })
        else:
            cls._api_call("sendMessage", {
                "chat_id": chat_id,
                "text": "🤖 Comando não reconhecido. Digite /ajuda para ver as opções disponíveis.",
                "parse_mode": "Markdown"
            })

    @classmethod
    def _send_help_menu(cls, chat_id: int):
        help_text = """🤖 *PAINEL DE CONTROLE - FREELANCE COPILOT*
━━━━━━━━━━━━━━━━━━━━━━━━
Olá, Ricson! Você pode gerenciar suas vagas e enviar propostas diretamente daqui pelo Telegram.

Comandos Rápidos:
🔍 /scan - Iniciar nova varredura de vagas agora
⏳ /pendentes - Ver as melhores vagas aguardando aprovação
📊 /status - Estatísticas de hoje e limite de envios
💡 /ajuda - Exibir este menu de opções

Dica: Em cada alerta de vaga recebido, você pode clicar em:
• *🚀 Enviar Proposta* (envio automatizado com 1 clique)
• *📝 Ver Proposta* (ver texto na íntegra e copiar com 1 toque)
• *📋 Notion CRM* (salvar para análise posterior)
• *❌ Descartar* (remover da lista)"""

        inline_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🔍 Iniciar Varredura (/scan)", "callback_data": "c:scan"},
                    {"text": "⏳ Vagas Pendentes (/pendentes)", "callback_data": "c:pendentes"}
                ],
                [
                    {"text": "📊 Ver Estatísticas (/status)", "callback_data": "c:status"}
                ]
            ]
        }
        cls._api_call("sendMessage", {
            "chat_id": chat_id,
            "text": help_text,
            "parse_mode": "Markdown",
            "reply_markup": inline_keyboard
        })

    @classmethod
    def _handle_scan_command(cls, chat_id: int):
        cls._api_call("sendMessage", {
            "chat_id": chat_id,
            "text": "🔍 *Varredura iniciada em segundo plano!*\nBuscando oportunidades em 99Freelas, Workana, Freelancer.com, RemoteOK, Remotive e WeWorkRemotely.\nVocê receberá alertas aqui caso novas vagas sejam encontradas.",
            "parse_mode": "Markdown"
        })

        def _do_scan():
            try:
                from main import run_scan
                run_scan()
                cls._api_call("sendMessage", {
                    "chat_id": chat_id,
                    "text": "🏁 *Varredura concluída!* Todas as novas oportunidades foram catalogadas.",
                    "parse_mode": "Markdown"
                })
            except Exception as e:
                cls._api_call("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"⚠️ Erro durante a varredura: {e}",
                    "parse_mode": "Markdown"
                })

        threading.Thread(target=_do_scan, daemon=True).start()

    @classmethod
    def _handle_pendentes_command(cls, chat_id: int):
        jobs = get_pending_jobs(limit=4)
        if not jobs:
            cls._api_call("sendMessage", {
                "chat_id": chat_id,
                "text": "✨ *Nenhuma vaga pendente no momento!* Todas as vagas analisadas já foram decididas ou você pode rodar /scan para buscar mais.",
                "parse_mode": "Markdown"
            })
            return

        cls._api_call("sendMessage", {
            "chat_id": chat_id,
            "text": f"⏳ *Encontradas {len(jobs)} vagas pendentes com maior qualificação:*\nEnviando cards com opção de envio direto abaixo...",
            "parse_mode": "Markdown"
        })

        for job in jobs:
            quote = {
                "platform_bid_price": job.get("quote_gross", 0.0),
                "net_receivable": job.get("quote_net", 0.0),
                "delivery_days": job.get("delivery_days", 1),
                "estimated_hours": 3,
                "currency_symbol": "R$" if job.get("platform") == "99freelas" else "$"
            }
            cls.send_job_alert(job, quote, job.get("proposal_text", ""), job.get("match_score", 70))

    @classmethod
    def _handle_status_command(cls, chat_id: int):
        stats = get_database_stats()
        mode_str = "Simulação (Dry-Run)" if SIMULATE_DRY_RUN else ("Envio Automático Ativo" if AUTO_SUBMIT_PROPOSALS else "Manual (Via Telegram)")

        msg = f"""📊 *STATUS DO FREELANCE COPILOT*
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ Modo: *{mode_str}*
🚀 Propostas Enviadas Hoje: *{stats['today_sent']} / {MAX_DAILY_PROPOSALS}*
📦 Total de Vagas Coletadas: *{stats['total']}*
⏳ Pendentes de Aprovação: *{stats['pending']}*
✅ Total Geral de Propostas Enviadas: *{stats['sent']}*
🗑️ Vagas Descartadas: *{stats['discarded']}*
━━━━━━━━━━━━━━━━━━━━━━━━
📡 *Plataformas Ativas:*
• 99Freelas (Nacional)
• Workana (Nacional & Internacional)
• Freelancer.com (Global / Multimoedas)
• RemoteOK (Global USD)
• Remotive (Global USD)
• WeWorkRemotely (Global USD)"""

        cls._api_call("sendMessage", {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "Markdown"
        })

    @classmethod
    def _handle_enviar_command(cls, chat_id: int, job_id: str):
        job_data = get_job(job_id)
        if not job_data:
            cls._api_call("sendMessage", {
                "chat_id": chat_id,
                "text": f"⚠️ Vaga com ID `{job_id}` não encontrada no banco local.",
                "parse_mode": "Markdown"
            })
            return
        cls._execute_proposal_submission(chat_id, job_data)

    @classmethod
    def _handle_callback(cls, cq: Dict[str, Any]):
        cq_id = cq["id"]
        data = cq.get("data", "")
        message = cq.get("message", {})
        chat_id = message.get("chat", {}).get("id")

        if not data or ":" not in data:
            return

        action, payload = data.split(":", 1)

        # Comandos rápidos via botão do menu
        if action == "c":
            if payload == "scan":
                cls._answer_callback(cq_id, "🔍 Iniciando varredura...")
                cls._handle_scan_command(chat_id)
            elif payload == "pendentes":
                cls._answer_callback(cq_id, "⏳ Buscando vagas pendentes...")
                cls._handle_pendentes_command(chat_id)
            elif payload == "status":
                cls._answer_callback(cq_id, "📊 Carregando estatísticas...")
                cls._handle_status_command(chat_id)
            return

        job_id = payload
        job_data = get_job(job_id)

        if not job_data:
            cls._answer_callback(cq_id, "⚠️ Vaga não encontrada no banco local.")
            return

        if action == "s": # Enviar Proposta
            cls._answer_callback(cq_id, "⏳ Processando envio de proposta...")
            threading.Thread(target=cls._execute_proposal_submission, args=(chat_id, job_data), daemon=True).start()

        elif action == "v": # Ver Proposta Completa
            cls._answer_callback(cq_id, "📝 Carregando texto da proposta...")
            proposal = job_data.get("proposal_text", "Texto indisponível.")
            title = job_data.get("title", "")
            gross = job_data.get("quote_gross", 0.0)
            days = job_data.get("delivery_days", 1)
            url = job_data.get("url", "")
            platform = job_data.get("platform", "").upper()

            cb_confirm = f"s:{job_id}"[:64]
            inline_keyboard = {
                "inline_keyboard": [
                    [{"text": "🚀 Confirmar Envio da Proposta", "callback_data": cb_confirm}],
                    [{"text": "🌐 Abrir Vaga no Navegador", "url": url}]
                ]
            }

            msg = f"""📝 *PROPOSTA PRONTA PARA ENVIO* ({platform})
📌 *{title}*
💰 *Valor Calculado:* R$ {gross:.2f} (ou USD) | ⏱️ *Prazo:* {days} dias úteis

📋 *Texto da Proposta (toque no bloco abaixo para copiar):*
```{proposal}```"""

            cls._api_call("sendMessage", {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
                "reply_markup": inline_keyboard
            })

        elif action == "n": # Salvar apenas no Notion
            cls._answer_callback(cq_id, "📋 Salvando no Notion CRM...")
            quote_dict = {
                "platform_bid_price": job_data["quote_gross"],
                "net_receivable": job_data["quote_net"],
                "delivery_days": job_data["delivery_days"],
                "currency": job_data.get("currency", "BRL")
            }
            page_id = NotionCRM.create_project_card(job_data, quote_dict, job_data["proposal_text"], status="Em Análise")
            update_job_status(job_id, "IN_REVIEW", page_id)
            cls._api_call("sendMessage", {
                "chat_id": chat_id,
                "text": f"📋 Vaga arquivada no Notion para análise:\n*{job_data['title']}*",
                "parse_mode": "Markdown"
            })

        elif action == "d": # Descartar
            cls._answer_callback(cq_id, "🗑️ Vaga descartada.")
            update_job_status(job_id, "DISCARDED")
            cls._api_call("sendMessage", {
                "chat_id": chat_id,
                "text": f"❌ Vaga descartada: _{job_data['title']}_",
                "parse_mode": "Markdown"
            })

    @classmethod
    def _execute_proposal_submission(cls, chat_id: int, job_data: Dict[str, Any]):
        """
        Executa a submissão da proposta:
        1. Abre a vaga no navegador com a sessão salva do usuário.
        2. Preenche o orçamento e o prazo calculados.
        3. Insere a mensagem personalizada da proposta.
        4. Submete de forma 100% automática.
        5. Atualiza o banco local e o Notion CRM.
        """
        platform_name = job_data.get("platform", "99freelas").lower()
        job_id = job_data["id"]
        title = job_data.get("title", "")
        url = job_data.get("url", "")
        proposal_text = job_data.get("proposal_text", "")
        gross = job_data.get("quote_gross", 0.0)
        days = job_data.get("delivery_days", 1)
        curr = job_data.get("currency", "BRL")
        symbol = "R$" if curr == "BRL" else "$"

        # Notificação de início do processo automático no Telegram
        cls._api_call("sendMessage", {
            "chat_id": chat_id,
            "text": (
                f"⚡ *Iniciando Envio Automático ({platform_name.upper()})*\n"
                f"📌 *Projeto:* _{title[:45]}..._\n"
                f"🌐 1. Abrindo vaga e formulário de proposta...\n"
                f"💰 2. Inserindo orçamento: *{symbol} {gross:.2f}* (Prazo: {days} dias)...\n"
                f"📝 3. Inserindo mensagem da proposta personalizada..."
            ),
            "parse_mode": "Markdown"
        })

        success = False

        if platform_name == "99freelas":
            crawler = NoventaNoveFreelas()
            try:
                success = asyncio.run(crawler.submit_proposal(url, proposal_text, gross, days))
            except Exception as e:
                print(f"⚠️ Erro ao submeter proposta 99Freelas: {e}")
                success = False

        elif platform_name == "workana":
            workana = WorkanaPlatform()
            try:
                success = asyncio.run(workana.submit_proposal(url, proposal_text, gross, days))
            except Exception as e:
                print(f"⚠️ Erro ao submeter proposta Workana: {e}")
                success = False

        else:
            # Portais com formulários externos (RemoteOK, Remotive, Freelancer, WeWorkRemotely)
            success = True

        quote_dict = {
            "platform_bid_price": gross,
            "net_receivable": job_data.get("quote_net", gross * 0.9),
            "delivery_days": days,
            "currency": curr
        }

        # Registra no Notion CRM
        page_id = NotionCRM.create_project_card(job_data, quote_dict, proposal_text, status="Proposta Enviada")
        update_job_status(job_id, "SENT", page_id)

        if success and platform_name in ["99freelas", "workana"]:
            confirm_msg = f"""🎉 *PROPOSTA SUBMETIDA COM SUCESSO!* ({platform_name.upper()})
━━━━━━━━━━━━━━━━━━━━━━━━
📌 *{title}*
💰 *Orçamento Enviado:* {symbol} {gross:.2f}
⏱️ *Prazo Proposto:* {days} dia(s) útil(eis)
📋 *Notion CRM:* Registrado com sucesso!
━━━━━━━━━━━━━━━━━━━━━━━━
✅ Vaga aberta, orçamento preenchido e mensagem enviada automaticamente."""

            inline_keyboard = {
                "inline_keyboard": [
                    [{"text": "🌐 Ver Vaga / Proposta na Plataforma", "url": url}]
                ]
            }

            cls._api_call("sendMessage", {
                "chat_id": chat_id,
                "text": confirm_msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
                "reply_markup": inline_keyboard
            })
        elif not success and platform_name in ["99freelas", "workana"]:
            error_msg = f"""⚠️ *Atenção:* Não foi possível submeter automaticamente nesta vaga do {platform_name.upper()} (a vaga pode ter sido encerrada pelo cliente ou exigir confirmação adicional).

📄 *Sua proposta foi salva e está pronta abaixo:*
```{proposal_text}```

👉 [Clique aqui para abrir a vaga e colar a proposta]({url})"""

            inline_keyboard = {
                "inline_keyboard": [
                    [{"text": "🌐 Abrir Vaga no Navegador", "url": url}]
                ]
            }

            cls._api_call("sendMessage", {
                "chat_id": chat_id,
                "text": error_msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
                "reply_markup": inline_keyboard
            })
        else:
            # Portais internacionais
            intl_tag = f" ({platform_name.upper()})"
            guide_msg = f"""🚀 *PROPOSTA PRONTA PARA ENVIO!*{intl_tag}
━━━━━━━━━━━━━━━━━━━━━━━━
📌 *{title}*
💰 *Orçamento Sugerido:* {symbol} {gross:.2f} | ⏱️ *Prazo:* {days} dias úteis

📋 *Texto da Proposta (toque no bloco abaixo para copiar):*
```{proposal_text}```

👉 [Clique aqui para abrir a página de candidatura]({url})
━━━━━━━━━━━━━━━━━━━━━━━━
✅ *Status:* Registrado no Notion CRM e marcado como Enviado!"""

            inline_keyboard = {
                "inline_keyboard": [
                    [{"text": "🌐 Abrir Página de Candidatura", "url": url}]
                ]
            }

            cls._api_call("sendMessage", {
                "chat_id": chat_id,
                "text": guide_msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
                "reply_markup": inline_keyboard
            })

    @classmethod
    def _answer_callback(cls, cq_id: str, text: str):
        try:
            cls._api_call("answerCallbackQuery", {
                "callback_query_id": cq_id,
                "text": text,
                "show_alert": False
            })
        except Exception:
            pass
