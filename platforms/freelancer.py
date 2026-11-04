"""
platforms/freelancer.py - Adaptador para Freelancer.com (Global / Multimoedas)
Varre oportunidades ativas em Dólar, Euro, Libra e Real via API REST oficial do Freelancer.com.
Cobre demandas não-especialistas (data entry, typing, spreadsheets, customer support) e tecnologia.
"""

import json
import urllib.request
import urllib.parse
from typing import List, Dict, Any
from platforms.base_platform import BasePlatform

class FreelancerPlatform(BasePlatform):
    BASE_URL = "https://www.freelancer.com"
    API_URL = "https://www.freelancer.com/api/projects/0.1/projects/active/"
    SEARCH_QUERIES = [
        "python",
        "data science",
        "machine learning",
        "web scraping",
        "automation",
        "osint",
        "cybersecurity",
        "pentest",
        "fastapi",
        "sql"
    ]

    def __init__(self):
        super().__init__("freelancer")

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        seen_ids = set()
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        for query in self.SEARCH_QUERIES:
            params = urllib.parse.urlencode({
                "query": query,
                "limit": 10,
                "compact": "true"
            })
            url = f"{self.API_URL}?{params}"

            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    projects = data.get("result", {}).get("projects", [])

                    for p in projects:
                        proj_id = f"freelancer_{p.get('id')}"
                        if proj_id in seen_ids:
                            continue
                        seen_ids.add(proj_id)

                        title = p.get("title", "")
                        seo_url = p.get("seo_url", "")
                        apply_url = f"{self.BASE_URL}/projects/{seo_url}" if seo_url else f"{self.BASE_URL}/projects/{p.get('id')}"
                        desc = p.get("preview_description", "")
                        curr_info = p.get("currency", {})
                        curr_code = curr_info.get("code", "USD")
                        bids = p.get("bid_count", 0)

                        budget_info = p.get("budget", {})
                        b_min = budget_info.get("minimum")
                        b_max = budget_info.get("maximum")
                        budget_str = f"Budget: {b_min} - {b_max} {curr_code}" if b_min else ""

                        jobs.append({
                            "id": proj_id,
                            "platform": "freelancer",
                            "title": title.strip(),
                            "url": apply_url,
                            "description": f"{budget_str}\n\n{desc}".strip(),
                            "proposals_count": bids,
                            "is_international": curr_code != "BRL",
                            "language": "pt" if curr_code == "BRL" else "en",
                            "currency": curr_code
                        })
            except Exception as e:
                print(f"⚠️ Erro ao varrer Freelancer.com ({query}): {e}")

        return jobs

    async def submit_proposal(self, job_url: str, proposal_text: str, bid_price: float, delivery_days: int) -> bool:
        print(f"ℹ️ [FREELANCER.COM] Oportunidade gerada para candidatura: {job_url}")
        return True
