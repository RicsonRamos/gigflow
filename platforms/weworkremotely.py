"""
platforms/weworkremotely.py - Adaptador para WeWorkRemotely (Internacional)
Varre oportunidades remotas internacionais em Python, Dados e Engenharia via feeds RSS.
"""

import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from platforms.base_platform import BasePlatform

class WeWorkRemotelyPlatform(BasePlatform):
    RSS_FEEDS = [
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"
    ]

    def __init__(self):
        super().__init__("weworkremotely")

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        seen_urls = set()
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }

        for feed_url in self.RSS_FEEDS:
            try:
                req = urllib.request.Request(feed_url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    root = ET.fromstring(resp.read())
                    items = root.findall(".//item")

                    for item in items[:20]:
                        link_elem = item.find("link")
                        if link_elem is None or not link_elem.text:
                            continue
                        link = link_elem.text.strip()
                        if link in seen_urls:
                            continue
                        seen_urls.add(link)

                        title = item.find("title").text if item.find("title") is not None else "Remote Job"
                        desc = item.find("description").text if item.find("description") is not None else ""
                        guid = item.find("guid").text if item.find("guid") is not None else link

                        jobs.append({
                            "id": f"wwr_{guid.split('/')[-1]}",
                            "platform": "weworkremotely",
                            "title": title.strip(),
                            "url": link,
                            "description": desc[:1500].strip(),
                            "proposals_count": 5,
                            "is_international": True,
                            "language": "en",
                            "currency": "USD"
                        })
            except Exception as e:
                print(f"⚠️ Erro ao varrer WeWorkRemotely ({feed_url}): {e}")

        return jobs

    async def submit_proposal(self, job_url: str, proposal_text: str, bid_price: float, delivery_days: int) -> bool:
        print(f"ℹ️ [WEWORKREMOTELY] Candidatura internacional gerada para: {job_url}")
        return True
