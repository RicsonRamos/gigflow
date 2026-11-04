"""
platforms/workana.py - Adaptador para Workana Brasil & Internacional
Utiliza Playwright/Patchright com evasão anti-detecção para renderização dinâmica das vagas
e envio de lances com base no perfil de Ricson Ramos.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from platforms.base_platform import BasePlatform
from core.auth_manager import (
    get_session_file,
    has_saved_session,
    get_browser_launch_args
)
from config import SIMULATE_DRY_RUN, ENABLE_INTERNATIONAL

DEFAULT_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"

def get_session_user_agent(session_path: str) -> str:
    try:
        p = Path(session_path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("user_agent", DEFAULT_UA)
    except Exception:
        pass
    return DEFAULT_UA

class WorkanaPlatform(BasePlatform):
    BASE_URL = "https://www.workana.com"
    SEARCH_CONFIGS = [
        {"url": "https://www.workana.com/jobs?language=pt&query=python", "lang": "pt", "curr": "BRL", "intl": False},
        {"url": "https://www.workana.com/jobs?language=pt&query=data+science", "lang": "pt", "curr": "BRL", "intl": False},
        {"url": "https://www.workana.com/jobs?language=pt&query=automacao", "lang": "pt", "curr": "BRL", "intl": False},
        {"url": "https://www.workana.com/jobs?language=pt&query=scraping", "lang": "pt", "curr": "BRL", "intl": False},
        {"url": "https://www.workana.com/jobs?language=pt&query=seguranca", "lang": "pt", "curr": "BRL", "intl": False},
        {"url": "https://www.workana.com/jobs?language=pt&query=python+junior", "lang": "pt", "curr": "BRL", "intl": False},
        {"url": "https://www.workana.com/jobs?language=pt&query=dados+junior", "lang": "pt", "curr": "BRL", "intl": False},
        {"url": "https://www.workana.com/jobs?language=en&query=python", "lang": "en", "curr": "USD", "intl": True},
        {"url": "https://www.workana.com/jobs?language=en&query=data+science", "lang": "en", "curr": "USD", "intl": True},
        {"url": "https://www.workana.com/jobs?language=en&query=automation", "lang": "en", "curr": "USD", "intl": True},
        {"url": "https://www.workana.com/jobs?language=en&query=cybersecurity", "lang": "en", "curr": "USD", "intl": True},
        {"url": "https://www.workana.com/jobs?language=en&query=osint", "lang": "en", "curr": "USD", "intl": True}
    ]

    def __init__(self):
        super().__init__("workana")

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Coleta vagas do Workana (Nacional e Internacional). Se o Patchright estiver disponível com sessão salva,
        acessa a interface autenticada; caso contrário, retorna lista vazia.
        """
        session_file = get_session_file("workana")
        if not has_saved_session("workana"):
            print("ℹ️ Workana requer sessão salva para busca profunda. Execute 'uv run python main.py --login workana'.")
            return []

        import asyncio
        return asyncio.run(self._fetch_jobs_async(str(session_file)))

    async def _fetch_jobs_async(self, session_path: str) -> List[Dict[str, Any]]:
        jobs = []
        seen_ids = set()
        try:
            try:
                from patchright.async_api import async_playwright
            except ImportError:
                from playwright.async_api import async_playwright

            launch_kwargs = get_browser_launch_args(headless=True)
            ua = get_session_user_agent(session_path)

            async with async_playwright() as p:
                browser = await p.chromium.launch(**launch_kwargs)
                context = await browser.new_context(
                    storage_state=session_path,
                    locale="pt-BR",
                    timezone_id="America/Sao_Paulo",
                    user_agent=ua
                )
                page = await context.new_page()

                active_searches = [c for c in self.SEARCH_CONFIGS if not c.get("intl", False)] if not ENABLE_INTERNATIONAL else self.SEARCH_CONFIGS
                for cfg in active_searches:
                    try:
                        await page.goto(cfg["url"], wait_until="domcontentloaded", timeout=30000)
                        
                        # Aguarda validação do cf_clearance se necessário
                        for _ in range(4):
                            page_title = await page.title()
                            if "Just a moment" not in page_title and "Um momento" not in page_title:
                                break
                            await page.wait_for_timeout(1000)

                        page_title = await page.title()
                        if "Just a moment" in page_title or "Um momento" in page_title:
                            print(f"⚠️ Workana ({cfg['lang']}): Desafio de segurança Cloudflare detectado. O token expirou.")
                            continue

                        project_cards = await page.locator("div.project-item").all()
                        for card in project_cards[:10]:
                            title_elem = card.locator("h2.project-title a").first
                            if not await title_elem.is_visible():
                                continue

                            title = await title_elem.text_content()
                            href = await title_elem.get_attribute("href")
                            if not href:
                                continue

                            job_id = f"workana_{href.split('/')[-1]}"
                            if job_id in seen_ids:
                                continue
                            seen_ids.add(job_id)

                            desc_elem = card.locator("div.project-details").first
                            desc = await desc_elem.text_content() if await desc_elem.is_visible() else ""

                            jobs.append({
                                "id": job_id,
                                "platform": "workana",
                                "title": title.strip() if title else "Projeto Workana",
                                "url": f"{self.BASE_URL}{href}",
                                "description": desc.strip() if desc else "",
                                "proposals_count": 0,
                                "language": cfg["lang"],
                                "currency": cfg["curr"],
                                "is_international": cfg["intl"]
                            })
                    except Exception as err:
                        print(f"⚠️ Erro ao varrer Workana ({cfg['lang']}): {err}")

                await browser.close()
        except Exception as e:
            print(f"⚠️ Erro ao inicializar navegador no Workana: {e}")

        return jobs

    async def submit_proposal(self, job_url: str, proposal_text: str, bid_price: float, delivery_days: int) -> bool:
        if SIMULATE_DRY_RUN:
            print(f"\n🧪 [SIMULAÇÃO DRY-RUN - WORKANA] Submissão para: {job_url}")
            print(f"Valor: {bid_price:.2f} | Prazo: {delivery_days} dias")
            return True

        session_file = get_session_file("workana")
        if not has_saved_session("workana"):
            print("❌ Sessão do Workana não encontrada. Execute 'uv run python main.py --login workana' primeiro.")
            return False

        try:
            try:
                from patchright.async_api import async_playwright
            except ImportError:
                from playwright.async_api import async_playwright

            launch_kwargs = get_browser_launch_args(headless=True)
            ua = get_session_user_agent(str(session_file))

            async with async_playwright() as p:
                browser = await p.chromium.launch(**launch_kwargs)
                context = await browser.new_context(
                    storage_state=str(session_file),
                    locale="pt-BR",
                    timezone_id="America/Sao_Paulo",
                    user_agent=ua
                )
                
                page = await context.new_page()
                await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                btn_fazer_proposta = page.locator("a:has-text('Fazer uma proposta')").first
                if await btn_fazer_proposta.is_visible():
                    await btn_fazer_proposta.click()
                    await page.wait_for_timeout(2000)

                textarea = page.locator("textarea#BidDescription").first
                if await textarea.is_visible():
                    await textarea.fill(proposal_text)

                input_price = page.locator("input#BidAmount").first
                if await input_price.is_visible():
                    await input_price.fill(f"{bid_price:.2f}")

                submit = page.locator("input#saveBid").first
                if await submit.is_visible():
                    await submit.click()
                    await page.wait_for_timeout(3000)
                    print(f"✅ Proposta enviada com sucesso no Workana: {job_url}")
                    await browser.close()
                    return True
                await browser.close()
                return False
        except Exception as e:
            print(f"❌ Erro ao enviar lance no Workana: {e}")
            return False
