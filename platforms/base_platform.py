"""
platforms/base_platform.py - Classe Base para Adaptadores de Plataformas de Freelancers
Define os contratos para busca de vagas, filtragem algorítmica e submissão automatizada.
Filtro estrito: Vagas Brasileiras, 100% Remoto (Zero Presencial/Híbrido), Foco em Estágio, Júnior, Freelance e PJ.
"""

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from config import (
    TARGET_KEYWORDS,
    EXCLUDE_KEYWORDS,
    EXCLUDE_SENIORITY_KEYWORDS,
    EXCLUDE_PRESENTIAL_KEYWORDS,
    EXCLUDE_OTHER_KEYWORDS,
    LEVEL_BOOST_KEYWORDS,
    MAX_PROPOSALS_PER_JOB,
    DATA_SCIENCE_KEYWORDS,
    OSINT_CYBERSECURITY_KEYWORDS,
    AUTOMATION_KEYWORDS,
    PROGRAMMING_KEYWORDS,
    ENABLE_INTERNATIONAL
)

def _match_keyword(kw: str, text: str) -> bool:
    """
    Evita falsos positivos em palavras curtas ou abreviações (ex: 'ia' em 'engenharia', 'bi' em 'habilidade', 'sr' em 'brasil').
    """
    kw = kw.strip().lower()
    text = text.lower()
    if not kw:
        return False
    if " " in kw or "-" in kw or "/" in kw:
        return kw in text
    # Se for palavra curta ou abreviação alfanumérica, usa fronteira regex com suporte a caracteres latinos
    if len(kw) <= 5:
        return bool(re.search(r'(?<![a-z0-9áàâãéêíóôõúç])' + re.escape(kw) + r'(?![a-z0-9áàâãéêíóôõúç])', text))
    return kw in text

class BasePlatform(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Coleta e retorna as oportunidades recentes da plataforma.
        """
        pass

    @abstractmethod
    async def submit_proposal(self, job_url: str, proposal_text: str, bid_price: float, delivery_days: int) -> bool:
        """
        Executa o envio automatizado da proposta via Playwright com sessão persistente.
        """
        pass

    def evaluate_job_match(self, job: Dict[str, Any]) -> Tuple[bool, int, str]:
        """
        Calcula o score de afinidade com o perfil especialista de Ricson Ramos com restrições estritas:
        1. Vagas Brasileiras (Descarte de internacionais quando ENABLE_INTERNATIONAL=False)
        2. 100% Remoto / Home Office (Descarte imediato de Presencial e Híbrido)
        3. Nível Atual: Estágios, Trainee, Júnior / Jr, Freelance e PJ (Descarte imediato de Sênior / Liderança)
        4. Especialidades: Ciência de Dados, OSINT, Cibersegurança, Automação, Python
        """
        title = job.get("title", "")
        desc = job.get("description", "")
        loc = job.get("location", "")
        full_text = f"{title} {desc} {loc}".lower()
        title_lower = title.lower()

        # 1. Filtro de Nacionalidade: Descarte de oportunidades internacionais se desativado
        if not ENABLE_INTERNATIONAL:
            if (
                job.get("is_international")
                or job.get("currency") in ["USD", "EUR", "GBP"]
                or job.get("language") == "en"
            ):
                return False, 0, "Descartado: Vaga internacional (Filtro configurado exclusivamente para Vagas Brasileiras)"

        # 2. Restrição Presencial / Híbrida: Descarte imediato se exigir presença física
        for bad_presential in EXCLUDE_PRESENTIAL_KEYWORDS:
            if _match_keyword(bad_presential, full_text):
                return False, 0, f"Descartado por restrição presencial/híbrida: '{bad_presential}' (Exigência: 100% Remoto/Home Office)"

        # 3. Restrição de Nível / Senioridade: Descarte imediato de vagas Sênior, Tech Lead, Gerência, etc.
        # Checagem prioritária no título
        for sr_word in EXCLUDE_SENIORITY_KEYWORDS:
            if _match_keyword(sr_word, title_lower):
                return False, 0, f"Descartado por nível sênior/liderança no título: '{sr_word}' (Foco: Estágio / Júnior / Nível Inicial / Freelance)"

        # Checagem na descrição completa
        for sr_word in EXCLUDE_SENIORITY_KEYWORDS:
            if _match_keyword(sr_word, full_text):
                return False, 0, f"Descartado por exigência de senioridade avançada: '{sr_word}' (Foco: Estágio / Júnior / Freelance)"

        # 4. Checagem de outros ruídos não-técnicos (vendas ativas, telemarketing, motorista, etc.)
        for bad_word in EXCLUDE_OTHER_KEYWORDS:
            if _match_keyword(bad_word, full_text):
                return False, 0, f"Descartado por categoria excluída: '{bad_word}'"

        # 5. Identificação de aderência aos 4 pilares especialistas de Ricson
        ds_matches = [kw for kw in DATA_SCIENCE_KEYWORDS if _match_keyword(kw, full_text)]
        sec_matches = [kw for kw in OSINT_CYBERSECURITY_KEYWORDS if _match_keyword(kw, full_text)]
        auto_matches = [kw for kw in AUTOMATION_KEYWORDS if _match_keyword(kw, full_text)]
        prog_matches = [kw for kw in PROGRAMMING_KEYWORDS if _match_keyword(kw, full_text)]

        all_matches = list(set(ds_matches + sec_matches + auto_matches + prog_matches))
        if not all_matches:
            return False, 0, "Fora do escopo especialista (Sem requisitos de Data Science, OSINT, Cibersegurança, Automação ou Programação)"

        # 6. Cálculo de pontuação base por pilares técnicos
        score = 40
        matched_pillars = []

        if sec_matches:
            score += 25
            matched_pillars.append("OSINT/Cybersecurity")
        if ds_matches:
            score += 25
            matched_pillars.append("Data Science/ML")
        if auto_matches:
            score += 20
            matched_pillars.append("Automação/Scraping")
        if prog_matches:
            score += 20
            matched_pillars.append("Python/Dev")

        # 7. Bônus por Nível Atual (Estágio, Júnior, Trainee, PJ ou Freelance)
        has_junior_or_intern = any(_match_keyword(kw, full_text) for kw in [
            "estágio", "estagio", "estagiário", "estagiária", "estagiario", "estagiaria",
            "trainee", "júnior", "junior", "jr", "jr.", "iniciante", "entry level", "assistente"
        ])
        has_freelance_pj = any(_match_keyword(kw, full_text) for kw in [
            "pj", "freelance", "freelancer", "prestador", "prestação de serviços"
        ])

        if has_junior_or_intern:
            score += 30
            matched_pillars.append("🎯 Nível: Júnior/Estágio")
        elif has_freelance_pj or job.get("platform") in ["99freelas", "workana"]:
            score += 15
            matched_pillars.append("💼 Contrato: Freelance/PJ")

        # Bônus por densidade de competências técnicas encontradas
        score += min(15, len(all_matches) * 5)
        score = min(100, score)

        # 8. Análise da Concorrência (Vagas com menos lances ganham prioridade)
        proposals_count = job.get("proposals_count", 0)
        if proposals_count > 150:
            return False, 10, f"Vaga saturada: {proposals_count} propostas já enviadas"
        elif proposals_count > MAX_PROPOSALS_PER_JOB:
            score = max(40, score - 20)
        elif proposals_count < 15:
            score = min(100, score + 10)

        status = score >= 60
        pillars_str = " + ".join(matched_pillars)
        matches_preview = ", ".join(all_matches[:4])
        return status, score, f"Match Qualificado [{pillars_str}]: {matches_preview} (Concorrência: {proposals_count} lances)"
