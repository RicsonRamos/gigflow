"""
platforms/remoteok.py - Adaptador para Vagas Internacionais Remotas (RemoteOK)
Varre oportunidades globais em Python, Dados, Automação e Engenharia em Dólar (USD).
"""

import json
import urllib.request
from typing import List, Dict, Any
from platforms.base_platform import BasePlatform

class RemoteOKPlatform(BasePlatform):
    API_URLS = [
        "https://remoteok.com/api?tag=python",
        "https://remoteok.com/api?tag=data",
        "https://remoteok.com/api?tag=machine-learning",
        "https://remoteok.com/api?tag=security",
        "https://remoteok.com/api?tag=automation",
        "https://remoteok.com/api?tag=devops"
    ]

    def __init__(self):
        super().__init__("remoteok")

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        seen_ids = set()
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        for url in self.API_URLS:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    # O primeiro item da lista do RemoteOK é um aviso legal
                    items = data[1:] if len(data) > 1 and isinstance(data[0], dict) and "legal" in data[0] else data

                    for item in items[:25]:
                        job_id = f"remoteok_{item.get('id', item.get('slug'))}"
                        if job_id in seen_ids:
                            continue
                        seen_ids.add(job_id)

                        title = item.get("position", "")
                        company = item.get("company", "")
                        desc = item.get("description", "")
                        apply_url = item.get("url", f"https://remoteok.com/remote-jobs/{item.get('slug')}")
                        tags = ", ".join(item.get("tags", []))

                        jobs.append({
                            "id": job_id,
                            "platform": "remoteok",
                            "title": f"{company}: {title}" if company else title,
                            "url": apply_url,
                            "description": f"Tags: {tags}\n\n{desc[:1500]}",
                            "proposals_count": 5, # RemoteOK não exibe contagem exata de lances
                            "is_international": True,
                            "language": "en",
                            "currency": "USD"
                        })
            except Exception as e:
                print(f"⚠️ Erro ao varrer RemoteOK ({url}): {e}")

        return jobs

    async def submit_proposal(self, job_url: str, proposal_text: str, bid_price: float, delivery_days: int) -> bool:
        """
        RemoteOK é um portal de candidatura direta / formulário web.
        A proposta gerada em inglês é entregue no Telegram para envio rápido no link de candidatura.
        """
        print(f"ℹ️ [REMOTEOK] Candidatura internacional gerada para: {job_url}")
        return True
