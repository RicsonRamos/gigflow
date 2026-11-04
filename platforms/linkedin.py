"""
platforms/linkedin.py - Adaptador Otimizado para Vagas do LinkedIn Brasil
Suporta dois modos:
1. Sessão Pessoal Conectada (Playwright/Patchright): Vagas recomendadas para seu perfil e buscas autenticadas.
2. Modo Público Consolidado (HTTP REST Guest API): Consultas booleanas consolidadas com filtros nativos f_WT=2 e f_E=1,2.
"""

import re
import json
import time
import random
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from platforms.base_platform import BasePlatform, _match_keyword
from config import EXCLUDE_SENIORITY_KEYWORDS, EXCLUDE_PRESENTIAL_KEYWORDS
from core.auth_manager import (
    get_session_file,
    has_saved_session,
    get_browser_launch_args
)

class LinkedInPlatform(BasePlatform):
    BASE_URL = "https://www.linkedin.com"
    API_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
    ]

    # Consultas consolidadas estritamente brasileiras focadas em Estágio, Júnior, PJ e Remoto
    CONSOLIDATED_SEARCHES = [
        # 1. Brasil - Python & Backend (Júnior / Estágio / Trainee / Remoto)
        {
            "query": 'python (junior OR jr OR estagio OR trainee OR assistente) remoto',
            "location": "Brazil",
            "is_intl": False,
            "currency": "BRL",
            "lang": "pt"
        },
        # 2. Brasil - Ciência de Dados, IA & Analytics (Júnior / Estágio / Trainee / Remoto)
        {
            "query": '("data science" OR "ciência de dados" OR "analista de dados" OR "machine learning") (junior OR jr OR estagio OR trainee) remoto',
            "location": "Brazil",
            "is_intl": False,
            "currency": "BRL",
            "lang": "pt"
        },
        # 3. Brasil - Cibersegurança, OSINT & Segurança da Informação (Júnior / Estágio / Trainee / Remoto)
        {
            "query": '(cibersegurança OR "segurança da informação" OR osint OR pentest) (junior OR jr OR estagio OR trainee) remoto',
            "location": "Brazil",
            "is_intl": False,
            "currency": "BRL",
            "lang": "pt"
        },
        # 4. Brasil - Automação, Scraping & Bots (Júnior / PJ / Remoto)
        {
            "query": '(automacao OR scraping OR "web scraping" OR bot) (python OR junior OR jr OR estagio) remoto',
            "location": "Brazil",
            "is_intl": False,
            "currency": "BRL",
            "lang": "pt"
        }
    ]

    def __init__(self):
        super().__init__("linkedin")

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Executa a busca de vagas. Se houver sessão salva do LinkedIn pessoal,
        prioriza a varredura autenticada (incluindo recomendações do perfil).
        Caso contrário, utiliza as buscas consolidadas da API pública.
        """
        session_file = get_session_file("linkedin")
        if has_saved_session("linkedin"):
            print("👤 [LINKEDIN] Sessão pessoal conectada detectada. Coletando vagas autenticadas e personalizadas...")
            try:
                import asyncio
                auth_jobs = asyncio.run(self._fetch_jobs_authenticated_async(str(session_file)))
                if auth_jobs:
                    print(f"✅ [LINKEDIN] {len(auth_jobs)} vagas obtidas diretamente da sua conta.")
                    return auth_jobs
                else:
                    print("ℹ️ [LINKEDIN] Nenhuma vaga retornada na sessão autenticada. Utilizando busca pública como fallback...")
            except Exception as e:
                print(f"⚠️ Erro ao varrer LinkedIn autenticado ({e}). Utilizando busca pública como fallback...")
        else:
            print("ℹ️ [LINKEDIN] Conexão pessoal não configurada. Utilizando API pública.")
            print("   👉 Para conectar sua conta e ver vagas recomendadas para seu perfil, execute: 'uv run python main.py --login linkedin'")

        return self._fetch_jobs_guest()

    async def _fetch_jobs_authenticated_async(self, session_path: str) -> List[Dict[str, Any]]:
        """
        Varre o LinkedIn diretamente como usuário autenticado utilizando a sessão salva em session_path.
        Acessa as coleções de recomendações do perfil e buscas focadas em Estágio / Júnior / Remoto.
        """
        jobs = []
        seen_ids = set()

        try:
            from patchright.async_api import async_playwright
        except ImportError:
            from playwright.async_api import async_playwright

        launch_kwargs = get_browser_launch_args(headless=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(**launch_kwargs)
            context = await browser.new_context(
                storage_state=session_path,
                locale="pt-BR",
                timezone_id="America/Sao_Paulo"
            )
            page = await context.new_page()

            # URLs alvo na conta conectada:
            urls_to_scan = [
                ("https://www.linkedin.com/jobs/collections/recommended/", "Recomendadas para Você (Algoritmo LinkedIn)"),
                ("https://www.linkedin.com/jobs/search/?keywords=python%20junior%20remoto&location=Brazil&f_WT=2&f_E=1%2C2", "Python Júnior Remoto"),
                ("https://www.linkedin.com/jobs/search/?keywords=dados%20junior%20remoto&location=Brazil&f_WT=2&f_E=1%2C2", "Dados/Data Science Júnior Remoto"),
                ("https://www.linkedin.com/jobs/search/?keywords=ciberseguranca%20junior%20remoto&location=Brazil&f_WT=2&f_E=1%2C2", "Cibersegurança/OSINT Júnior Remoto"),
                ("https://www.linkedin.com/jobs/search/?keywords=automacao%20python%20remoto&location=Brazil&f_WT=2&f_E=1%2C2", "Automação Python Remoto")
            ]

            for url, label in urls_to_scan:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_timeout(2000)

                    # Verifica se foi redirecionado para tela de login (sessão expirada)
                    current_url = page.url
                    if "/login" in current_url or "/checkpoint" in current_url:
                        print("⚠️ [LINKEDIN] Sessão expirada. Reconecte via: uv run python main.py --login linkedin")
                        break

                    cards = await page.locator("div.job-card-container, li.jobs-search-results__list-item, div[data-job-id], li[data-occludable-job-id]").all()

                    for card in cards[:15]:
                        try:
                            link_elem = card.locator("a[href*='/jobs/view/'], a.job-card-list__title--link, a.job-card-container__link").first
                            if not await link_elem.is_visible():
                                continue

                            href = await link_elem.get_attribute("href")
                            if not href:
                                continue

                            match_id = re.search(r"(\d{8,})", href)
                            if not match_id:
                                continue

                            job_raw_id = match_id.group(1)
                            job_id = f"linkedin_{job_raw_id}"
                            if job_id in seen_ids:
                                continue
                            seen_ids.add(job_id)

                            title_raw = (await link_elem.inner_text()).strip()
                            title = title_raw.split("\n")[0].strip()

                            comp_elem = card.locator(".artdeco-entity-lockup__subtitle, .job-card-container__primary-description").first
                            company = (await comp_elem.inner_text()).strip().split("\n")[0].strip() if await comp_elem.is_visible() else "Empresa Confidencial"

                            loc_elem = card.locator(".job-card-container__metadata-item, span.job-search-card__location").first
                            location = (await loc_elem.inner_text()).strip().split("\n")[0].strip() if await loc_elem.is_visible() else "Brasil (Remoto)"

                            card_text = (await card.inner_text()).lower()
                            easy_apply_badge = " [⚡ Candidatura Simplificada]" if ("candidatura simplificada" in card_text or "easy apply" in card_text) else ""

                            # Exclusão prévia por senioridade ou formato presencial
                            title_lower = title.lower()
                            loc_lower = location.lower()
                            if any(_match_keyword(sr_kw, title_lower) for sr_kw in EXCLUDE_SENIORITY_KEYWORDS):
                                continue
                            if any(_match_keyword(pres_kw, loc_lower) for pres_kw in EXCLUDE_PRESENTIAL_KEYWORDS):
                                continue

                            description = (
                                f"Vaga LinkedIn Conectado ({label}):\n"
                                f"Cargo: {title}{easy_apply_badge}\n"
                                f"Empresa: {company}\n"
                                f"Modalidade / Local: {location} (100% Remoto - PJ ou CLT)\n"
                                f"Nível de Experiência: Estágio / Júnior / Nível Inicial\n"
                                f"Origem: Perfil Conectado no LinkedIn\n"
                            )

                            jobs.append({
                                "id": job_id,
                                "platform": "linkedin",
                                "title": f"{company}: {title}{easy_apply_badge}",
                                "url": f"https://www.linkedin.com/jobs/view/{job_raw_id}/",
                                "description": description,
                                "location": location,
                                "proposals_count": 5,
                                "is_international": False,
                                "language": "pt",
                                "currency": "BRL"
                            })
                        except Exception:
                            continue

                except Exception as err:
                    print(f"⚠️ Erro ao varrer '{label}' no LinkedIn autenticado: {err}")

            await browser.close()

        return jobs

    def _fetch_jobs_guest(self) -> List[Dict[str, Any]]:
        """
        Varre a API pública do LinkedIn para visitantes com consultas consolidadas.
        """
        jobs = []
        seen_ids = set()

        for cfg in self.CONSOLIDATED_SEARCHES:
            ua = random.choice(self.USER_AGENTS)
            headers = {
                "User-Agent": ua,
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }

            params = urllib.parse.urlencode({
                "keywords": cfg["query"],
                "location": cfg["location"],
                "f_WT": "2",     # 100% Remoto
                "f_E": "1,2",    # Estágio e Júnior
                "start": "0"
            })
            url = f"{self.API_SEARCH_URL}?{params}"

            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    html_content = resp.read().decode("utf-8", errors="ignore")
                    soup = BeautifulSoup(html_content, "html.parser")
                    cards = soup.find_all("li")

                    for card in cards:
                        title_el = card.find("h3", class_="base-search-card__title")
                        comp_el = card.find("h4", class_="base-search-card__subtitle")
                        link_el = card.find("a", href=True)
                        loc_el = card.find("span", class_="job-search-card__location")

                        if not title_el or not link_el:
                            continue

                        raw_link = link_el["href"].split("?")[0]
                        match_id = re.search(r"(\d{8,})", raw_link)
                        if not match_id:
                            continue

                        job_raw_id = match_id.group(1)
                        job_id = f"linkedin_{job_raw_id}"

                        if job_id in seen_ids:
                            continue
                        seen_ids.add(job_id)

                        title = title_el.get_text(strip=True)
                        company = comp_el.get_text(strip=True) if comp_el else "Empresa Confidencial"
                        location = loc_el.get_text(strip=True) if loc_el else cfg["location"]

                        title_lower = title.lower()
                        loc_lower = location.lower()

                        if any(_match_keyword(sr_kw, title_lower) for sr_kw in EXCLUDE_SENIORITY_KEYWORDS):
                            continue

                        if any(_match_keyword(pres_kw, loc_lower) for pres_kw in EXCLUDE_PRESENTIAL_KEYWORDS):
                            continue

                        description = (
                            f"Vaga LinkedIn Brasil (100% Remoto / Home Office):\n"
                            f"Cargo: {title}\n"
                            f"Empresa: {company}\n"
                            f"Modalidade / Local: {location} (100% Remoto - Contrato PJ ou CLT)\n"
                            f"Nível: Estágio / Júnior / Nível Inicial\n"
                            f"Critério de Busca: {cfg['query']}\n"
                        )

                        jobs.append({
                            "id": job_id,
                            "platform": "linkedin",
                            "title": f"{company}: {title}",
                            "url": f"https://www.linkedin.com/jobs/view/{job_raw_id}",
                            "description": description,
                            "location": location,
                            "proposals_count": 5,
                            "is_international": False,
                            "language": "pt",
                            "currency": "BRL"
                        })

                time.sleep(2.0)

            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"ℹ️ [LINKEDIN] Limite temporário da API pública atingido (HTTP 429). Retomando no próximo ciclo.")
                    break
                else:
                    print(f"⚠️ Erro ao consultar LinkedIn ({cfg['location']}): HTTP {he.code}")
            except Exception as e:
                print(f"⚠️ Erro ao consultar LinkedIn ({cfg['location']}): {e}")

        return jobs

    async def submit_proposal(self, job_url: str, proposal_text: str, bid_price: float, delivery_days: int) -> bool:
        """
        No LinkedIn, a candidatura é realizada pelo candidato diretamente via Easy Apply ou site externo.
        A proposta / cover letter personalizada é entregue pronta no Telegram para cópia em 1 toque.
        """
        print(f"ℹ️ [LINKEDIN] Cover letter / Proposta gerada para candidatura: {job_url}")
        return True
