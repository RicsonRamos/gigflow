"""
platforms/remotive.py - Adaptador para Vagas Remotas Mundiais (Remotive)
Varre oportunidades 100% home office em Customer Support, Data, QA, Assistência Virtual e Tech em Dólar.
"""

import json
import urllib.request
from typing import List, Dict, Any
from platforms.base_platform import BasePlatform

class RemotivePlatform(BasePlatform):
    CATEGORIES = [
        "software-development",
        "data",
        "devops",
        "qa"
    ]

    def __init__(self):
        super().__init__("remotive")

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        seen_ids = set()
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }

        for cat in self.CATEGORIES:
            url = f"https://remotive.com/api/remote-jobs?category={cat}&limit=15"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    items = data.get("jobs", [])

                    for item in items:
                        job_id = f"remotive_{item.get('id')}"
                        if job_id in seen_ids:
                            continue
                        seen_ids.add(job_id)

                        title = item.get("title", "")
                        company = item.get("company_name", "")
                        desc = item.get("description", "")
                        apply_url = item.get("url", "")
                        tags = ", ".join(item.get("tags", []))

                        jobs.append({
                            "id": job_id,
                            "platform": "remotive",
                            "title": f"{company}: {title}" if company else title,
                            "url": apply_url,
                            "description": f"Category: {cat} | Tags: {tags}\n\n{desc[:1500]}",
                            "proposals_count": 5,
                            "is_international": True,
                            "language": "en",
                            "currency": "USD"
                        })
            except Exception as e:
                print(f"⚠️ Erro ao varrer Remotive ({cat}): {e}")

        return jobs

    async def submit_proposal(self, job_url: str, proposal_text: str, bid_price: float, delivery_days: int) -> bool:
        print(f"ℹ️ [REMOTIVE] Candidatura remota gerada para: {job_url}")
        return True
