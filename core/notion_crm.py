"""
core/notion_crm.py - Integração Oficial com a API do Notion (CRM de Freelas Custo Zero)
Cria e atualiza automaticamente os cards de projetos na base de dados do Notion de Ricson,
registrando propostas, orçamentos, status de negociação e projetos aceitos.
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from config import NOTION_API_KEY, NOTION_DATABASE_ID

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

class NotionCRM:
    @classmethod
    def is_configured(cls) -> bool:
        return bool(NOTION_API_KEY and NOTION_DATABASE_ID)

    @classmethod
    def _headers(cls) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION
        }

    @classmethod
    def test_connection(cls) -> bool:
        """
        Verifica se a integração e o ID do Database estão configurados e acessíveis.
        """
        if not NOTION_API_KEY or not NOTION_DATABASE_ID:
            print("⚠️ Notion API Key ou Database ID não configurados no arquivo .env")
            return False

        url = f"{NOTION_API_URL}/databases/{NOTION_DATABASE_ID}"
        req = urllib.request.Request(url, headers=cls._headers(), method="GET")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                db_name = data.get("title", [{}])[0].get("plain_text", "Base de Freelas")
                print(f"✅ Conexão com o Notion estabelecida! Database: '{db_name}'")
                return True
        except urllib.error.HTTPError as e:
            print(f"❌ Erro ao conectar ao Notion (HTTP {e.code}): {e.read().decode('utf-8')}")
            return False
        except Exception as e:
            print(f"❌ Falha inesperada ao conectar ao Notion: {e}")
            return False

    @classmethod
    def create_project_card(cls, job: Dict[str, Any], quote: Dict[str, Any], proposal_text: str, status: str = "Proposta Enviada") -> Optional[str]:
        """
        Cria uma nova página (card) no Database de Projetos do Notion.
        """
        if not NOTION_API_KEY or not NOTION_DATABASE_ID:
            print("⚠️ Notion não configurado. Pulando sincronização.")
            return None

        url = f"{NOTION_API_URL}/pages"
        
        # Estrutura padrão tolerante a variações comuns no schema do Notion
        payload = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "Nome do Projeto": {
                    "title": [
                        {"text": {"content": job.get("title", "Novo Projeto Freela")[:100]}}
                    ]
                },
                "Plataforma": {
                    "select": {
                        "name": job.get("platform", "99Freelas").capitalize()
                    }
                },
                "Status": {
                    "status": {
                        "name": status
                    }
                },
                "Valor Bruto (R$)": {
                    "number": float(quote.get("platform_bid_price", 0.0))
                },
                "Valor Líquido (R$)": {
                    "number": float(quote.get("net_receivable", 0.0))
                },
                "URL da Vaga": {
                    "url": job.get("url", "")
                }
            },
            "children": [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "📋 Escopo e Diagnóstico"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": job.get("description", "Sem descrição")[:1900]}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "✉️ Proposta Enviada"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": proposal_text[:1900]}}]
                    }
                }
            ]
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=cls._headers(),
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                page_id = result.get("id")
                page_url = result.get("url")
                print(f"✅ Card criado com sucesso no Notion: {page_url}")
                return page_id
        except urllib.error.HTTPError as e:
            # Tenta um payload simplificado caso o schema do Notion tenha nomes de colunas diferentes
            print(f"⚠️ Erro ao criar card detalhado no Notion (HTTP {e.code}). Tentando formato compatível...")
            return cls._create_fallback_card(job, quote, proposal_text)
        except Exception as e:
            print(f"❌ Erro ao criar card no Notion: {e}")
            return None

    @classmethod
    def _create_fallback_card(cls, job: Dict[str, Any], quote: Dict[str, Any], proposal_text: str) -> Optional[str]:
        """
        Formato de fallback minimalista (apenas título e conteúdo da página) caso colunas customizadas não coincidam.
        """
        url = f"{NOTION_API_URL}/pages"
        payload = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "title": {
                    "title": [
                        {"text": {"content": f"[{job.get('platform', 'Freela').upper()}] {job.get('title', 'Projeto')}"[:100]}}
                    ]
                }
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": f"Orçamento: R$ {quote.get('platform_bid_price', 0):.2f} | Prazo: {quote.get('delivery_days', 0)} dias\nURL: {job.get('url', '')}\n\nProposta:\n{proposal_text}"}}
                        ]
                    }
                }
            ]
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=cls._headers(), method="POST")
            with urllib.request.urlopen(req, timeout=12) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                print(f"✅ Card de fallback criado no Notion: {res.get('url')}")
                return res.get("id")
        except Exception as e:
            print(f"❌ Fallback do Notion também falhou: {e}")
            return None

if __name__ == "__main__":
    NotionCRM.test_connection()
