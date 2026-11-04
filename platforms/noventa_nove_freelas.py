"""
platforms/noventa_nove_freelas.py - Crawler e Executor de Propostas para o 99Freelas
Utiliza requisições HTTP ultrarrápidas para monitorar novas vagas (Custo Zero)
e Playwright com sessão persistente para submeter lances aprovados via Telegram.
"""

import re
import html
import urllib.request
from typing import List, Dict, Any
from platforms.base_platform import BasePlatform
from core.auth_manager import get_session_file, has_saved_session, get_browser_launch_args
from config import SIMULATE_DRY_RUN

class NoventaNoveFreelas(BasePlatform):
    BASE_URL = "https://www.99freelas.com.br"
    SEARCH_URLS = [
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&order=mais-recentes",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=python",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=dados",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=data+science",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=automacao",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=scraping",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=crawler",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=bot",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=seguranca",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=osint",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=api",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=sql",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=machine+learning",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=junior",
        "https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&q=estagio"
    ]

    def __init__(self):
        super().__init__("99freelas")

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Varre as categorias e buscas do 99Freelas (Home Office geral e tecnologia), extrai as vagas e remove duplicatas.
        """
        all_jobs: Dict[str, Dict[str, Any]] = {}
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8"
        }

        for url in self.SEARCH_URLS:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read().decode("utf-8", errors="ignore")
                    jobs_found = self._parse_html(content)
                    for j in jobs_found:
                        job_id = j["id"]
                        if job_id not in all_jobs:
                            all_jobs[job_id] = j
            except Exception as e:
                print(f"⚠️ Erro ao buscar 99Freelas ({url.split('/')[-1]}): {e}")

        return list(all_jobs.values())

    def _parse_html(self, raw_html: str) -> List[Dict[str, Any]]:
        """
        Extrai títulos, links, propostas e descrições dos blocos HTML do 99Freelas.
        """
        results = []
        splits = re.split(r'<h1 class="title">', raw_html)

        for block in splits[1:]:
            # 1. URL e Título
            link_match = re.search(r'href="(/project/[a-zA-Z0-9\-]+-(\d+)[^"]*)"[^>]*>([^<]+)</a>', block)
            if not link_match:
                continue

            rel_url = link_match.group(1).split("?")[0]
            job_id = link_match.group(2)
            title = html.unescape(link_match.group(3).strip())
            full_url = f"{self.BASE_URL}{rel_url}"

            # 2. Contagem de propostas já enviadas
            proposals_count = 0
            prop_match = re.search(r'Propostas:\s*<b>(\d+)</b>', block)
            if prop_match:
                proposals_count = int(prop_match.group(1))

            # 3. Descrição completa
            desc_match = re.search(r'<div class="item-text description formatted-text"[^>]*data-content="([^"]+)"', block)
            if desc_match:
                raw_desc = desc_match.group(1)
                # Limpa quebras e tags HTML da descrição
                description = html.unescape(raw_desc.replace("<br/>", "\n").replace("<br>", "\n"))
            else:
                description = "Descrição indisponível no resumo da listagem."

            results.append({
                "id": f"99freelas_{job_id}",
                "platform": "99freelas",
                "title": title,
                "url": full_url,
                "description": description.strip(),
                "proposals_count": proposals_count
            })

        return results

    async def submit_proposal(self, job_url: str, proposal_text: str, bid_price: float, delivery_days: int) -> bool:
        """
        Executa o envio do lance via Playwright utilizando a sessão autenticada.
        """
        if SIMULATE_DRY_RUN:
            print("\n-----------------------------------------------------------")
            print(f"🧪 [SIMULAÇÃO DRY-RUN - 99FREELAS]")
            print(f"URL: {job_url}")
            print(f"Valor: R$ {bid_price:.2f} | Prazo: {delivery_days} dias")
            print(f"Proposta a ser enviada:\n{proposal_text}")
            print("-----------------------------------------------------------\n")
            return True

        session_file = get_session_file("99freelas")
        if not has_saved_session("99freelas"):
            print("❌ Sessão do 99Freelas não encontrada. Execute 'uv run python main.py --login 99freelas' primeiro.")
            return False

        try:
            try:
                from patchright.async_api import async_playwright
            except ImportError:
                from playwright.async_api import async_playwright

            launch_kwargs = get_browser_launch_args(headless=True)

            async with async_playwright() as p:
                browser = await p.chromium.launch(**launch_kwargs)
                context = await browser.new_context(
                    storage_state=str(session_file),
                    locale="pt-BR",
                    timezone_id="America/Sao_Paulo"
                )
                page = await context.new_page()

                # 1. Abre a página direta de proposta do 99Freelas
                bid_url = job_url.replace("99freelas.com.br/project/", "99freelas.com.br/project/bid/")
                print(f"🌐 [99FREELAS] Acessando formulário de proposta: {bid_url}")
                await page.goto(bid_url, wait_until="networkidle", timeout=30000)

                # Se não carregou direto na página de bid, tenta clicar no botão 'Enviar proposta'
                oferta_input = page.locator("input#oferta")
                if not await oferta_input.is_visible():
                    btn_proposta = page.locator("a:has-text('Enviar proposta'), a[href*='/project/bid/'], a.btn.blue").first
                    if await btn_proposta.is_visible():
                        await btn_proposta.click()
                        await page.wait_for_timeout(2000)

                # 2. Preenche o orçamento no campo 'oferta'
                oferta_input = page.locator("input#oferta")
                if await oferta_input.is_visible():
                    val_str = f"{bid_price:.2f}".replace(".", ",")
                    await oferta_input.fill(val_str)
                    print(f"💰 [99FREELAS] Orçamento preenchido: R$ {val_str}")
                else:
                    print("⚠️ [99FREELAS] Campo de oferta não encontrado.")
                    await browser.close()
                    return False

                # 3. Preenche a duração estimada
                prazo_input = page.locator("input#duracao-estimada")
                if await prazo_input.is_visible():
                    await prazo_input.fill(str(delivery_days))
                    print(f"⏱️ [99FREELAS] Prazo preenchido: {delivery_days} dias")

                # 4. Preenche a mensagem personalizada da proposta
                proposta_textarea = page.locator("textarea#proposta")
                if await proposta_textarea.is_visible():
                    await proposta_textarea.fill(proposal_text)
                    print(f"📝 [99FREELAS] Mensagem da proposta preenchida ({len(proposal_text)} caracteres)")
                else:
                    print("⚠️ [99FREELAS] Campo de proposta não encontrado.")
                    await browser.close()
                    return False

                # 5. Marca caixas de confirmação caso existam
                chk_suspeito = page.locator("input#confirmar-padrao-suspeito-mensagem")
                if await chk_suspeito.is_visible():
                    await chk_suspeito.check()

                chk_envio = page.locator("input#confirmar-envio-proposta")
                if await chk_envio.is_visible():
                    await chk_envio.check()

                # 6. Clica no botão final de submissão
                submit_btn = page.locator("button#btnConcluirEnvioProposta, button:has-text('Enviar proposta')").first
                if await submit_btn.is_visible():
                    await submit_btn.click()
                    await page.wait_for_timeout(4000)

                    # Verifica se o envio concluiu com sucesso
                    current_url = page.url
                    page_content = await page.content()
                    if "/project/bid/" not in current_url or "proposta enviada" in page_content.lower():
                        print(f"✅ [99FREELAS] Proposta enviada com sucesso no 99Freelas: {job_url}")
                        await browser.close()
                        return True
                    else:
                        print(f"ℹ️ [99FREELAS] Formulário submetido. URL resultante: {current_url}")
                        await browser.close()
                        return True
                else:
                    print("⚠️ [99FREELAS] Botão 'btnConcluirEnvioProposta' não encontrado.")
                    await browser.close()
                    return False
        except Exception as e:
            print(f"❌ Erro ao enviar proposta no 99Freelas: {e}")
            return False

if __name__ == "__main__":
    crawler = NoventaNoveFreelas()
    jobs = crawler.fetch_jobs()
    print(f"Total de vagas encontradas no 99Freelas: {len(jobs)}")
    for j in jobs[:3]:
        print(f"\n[VAGA] {j['title']} ({j['proposals_count']} propostas)")
        print(f"URL: {j['url']}")
        print(f"Resumo: {j['description'][:150]}...")
