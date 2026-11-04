"""
core/auth_manager.py - Gerenciador de Autenticação e Sessão Persistente (Zero Captcha/2FA)
Utiliza Patchright (fork indetectável do Playwright sem vazamentos de CDP) e Google Chrome real
para superar desafios do Cloudflare Turnstile, além de suporte a importação manual de cookies.
"""

import re
import sys
import json
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any, List

# Garante inclusão do pacote pai no sys.path
_parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from config import SESSIONS_DIR, DATA_DIR

PLATFORM_LOGIN_URLS = {
    "99freelas": "https://www.99freelas.com.br/login",
    "workana": "https://www.workana.com/login",
    "linkedin": "https://www.linkedin.com/login"
}

PLATFORM_DOMAINS = {
    "99freelas": ".99freelas.com.br",
    "workana": ".workana.com",
    "linkedin": ".linkedin.com"
}

COOKIES_TXT_PATH = DATA_DIR / "cookies.txt"

def get_session_file(platform: str) -> Path:
    return SESSIONS_DIR / f"{platform.lower()}_state.json"

def has_saved_session(platform: str) -> bool:
    session_file = get_session_file(platform)
    return session_file.exists() and session_file.stat().st_size > 100

def get_browser_launch_args(headless: bool = False) -> Dict[str, Any]:
    """
    Retorna as opções de inicialização do navegador com evasão anti-detecção.
    Prioriza o Google Chrome nativo instalado no sistema.
    """
    chrome_bin = shutil.which("google-chrome") or shutil.which("google-chrome-stable") or shutil.which("brave-browser")
    
    launch_kwargs: Dict[str, Any] = {
        "headless": headless,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
        ],
        "ignore_default_args": ["--enable-automation"]
    }
    
    if chrome_bin:
        launch_kwargs["channel"] = "chrome"
        
    return launch_kwargs

def extract_cookies_from_raw(raw_input: str) -> str:
    """
    Extrai a sequência pura de cookies de comandos cURL, cabeçalhos HTTP ou texto direto.
    """
    raw_input = raw_input.strip()

    # Formato 1: -H 'cookie: ...' ou -H "cookie: ..."
    m = re.search(r"-H\s*['\"]cookie:\s*([^'\"]+)['\"]", raw_input, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # Formato 2: -b '...' ou --cookie '...'
    m = re.search(r"(?:-b|--cookie)\s*['\"]([^'\"]+)['\"]", raw_input, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # Formato 3: Linha Cookie: ...
    m = re.search(r"(?:^|\n)\s*cookie:\s*([^\r\n]+)", raw_input, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return raw_input

def save_manual_cookies(platform_key: str, raw_input: str) -> bool:
    """
    Converte entrada de cookies (cURL, cabeçalho de rede, JSON do Cookie Editor ou pares chave=valor)
    em um arquivo storage_state válido do Playwright/Patchright.
    """
    session_file = get_session_file(platform_key)
    domain = PLATFORM_DOMAINS.get(platform_key, f".{platform_key}.com")
    raw_input = raw_input.strip()

    cookies: List[Dict[str, Any]] = []

    # 1. Caso o usuário cole um JSON (ex: exportado de extensões como Cookie-Editor)
    if raw_input.startswith("[") and raw_input.endswith("]"):
        try:
            items = json.loads(raw_input)
            for it in items:
                name = it.get("name")
                value = it.get("value")
                if name and value:
                    cookies.append({
                        "name": str(name),
                        "value": str(value),
                        "domain": it.get("domain", domain),
                        "path": it.get("path", "/"),
                        "expires": it.get("expirationDate", -1),
                        "httpOnly": it.get("httpOnly", False),
                        "secure": it.get("secure", True),
                        "sameSite": "Lax"
                    })
        except Exception:
            pass

    # 2. Caso o usuário cole um comando cURL ou cabeçalho HTTP completo
    if not cookies:
        raw_cookie_str = extract_cookies_from_raw(raw_input)
        pairs = [p.strip() for p in raw_cookie_str.split(";") if p.strip()]
        for pair in pairs:
            if "=" in pair:
                k, v = pair.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                # Remove prefixos acidentais como 'cookie: '
                if k.lower().startswith("cookie:"):
                    k = k[7:].strip()
                if k:
                    cookies.append({
                        "name": k,
                        "value": v,
                        "domain": domain,
                        "path": "/",
                        "expires": -1,
                        "httpOnly": True if k in ["cf_clearance", "workana_session", "li_at", "JSESSIONID"] else False,
                        "secure": True,
                        "sameSite": "Lax"
                    })

    # 3. Caso o usuário cole diretamente apenas o valor do token li_at (LinkedIn)
    if not cookies and platform_key == "linkedin" and (raw_input.startswith("AQED") or "AQED" in raw_input):
        m = re.search(r"(AQED[a-zA-Z0-9_\-]+)", raw_input)
        token_val = m.group(1) if m else raw_input
        cookies.append({
            "name": "li_at",
            "value": token_val,
            "domain": domain,
            "path": "/",
            "expires": -1,
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        })
            
    if not cookies:
        print("\n❌ Nenhum cookie válido encontrado no texto informado.")
        if "wkncdn" in raw_input or ".js" in raw_input or ".css" in raw_input:
            print("💡 Diagnóstico: Você copiou uma requisição de arquivo estático (.js/.css) do CDN.")
            print("   Navegadores não enviam cookies para arquivos estáticos.")
            print("👉 Como resolver:")
            print("   1. Na aba Rede do F12, clique no filtro 'Doc' (ou Documento).")
            print("   2. Dê F5 na página e selecione a requisição principal do site.")
            print("   3. Copie o cURL dessa requisição ou copie o valor do cabeçalho 'Cookie:'.\n")
        return False

    state_data = {
        "cookies": cookies,
        "origins": [
            {
                "origin": f"https://www{domain}",
                "localStorage": []
            }
        ]
    }
    
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=2)
        
    print(f"\n✅ Sucesso! {len(cookies)} cookies importados com sucesso em: {session_file}")
    has_cf = False
    has_sess = False
    has_li = False
    for c in cookies:
        mark = " (Protegido/HttpOnly)" if c["httpOnly"] else ""
        print(f"   • {c['name']}{mark}")
        if "cf_clearance" in c["name"]:
            has_cf = True
        if "session" in c["name"] or "workana" in c["name"]:
            has_sess = True
        if "li_at" in c["name"]:
            has_li = True

    if platform_key == "linkedin":
        if has_li:
            print("\n🌟 Cookie principal do LinkedIn 'li_at' identificado com sucesso!")
        else:
            print("\n⚠️ Atenção: O cookie principal 'li_at' do LinkedIn não foi identificado nesta lista.")
            print("   Certifique-se de copiar a requisição autenticada do linkedin.com.")
    elif platform_key == "workana" and not has_cf:
        print("\n⚠️ Atenção: O cookie 'cf_clearance' não foi identificado nesta lista.")
        print("   Caso a Workana volte a solicitar verificação, garanta que copiou a requisição principal.")
    return True

def read_input_multiline() -> str:
    """Lê múltiplas linhas do terminal até uma linha em branco ou EOF."""
    print("👉 Cole o texto aqui e pressione [ENTER] duas vezes para confirmar:\n")
    lines = []
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            if line.strip() == "" and lines:
                break
            lines.append(line)
        except (EOFError, KeyboardInterrupt):
            break
    return "".join(lines).strip()

async def record_session(platform: str, manual: bool = False):
    """
    Inicia o navegador visível (headed) para login ou solicita importação manual de cookies.
    """
    platform_key = platform.lower()
    if platform_key not in PLATFORM_LOGIN_URLS:
        print(f"❌ Plataforma '{platform}' desconhecida. Use: {list(PLATFORM_LOGIN_URLS.keys())}")
        return

    session_file = get_session_file(platform_key)
    login_url = PLATFORM_LOGIN_URLS[platform_key]

    if manual:
        print(f"\n=======================================================")
        print(f"📋 IMPORTAÇÃO MANUAL DE COOKIES: {platform.upper()}")
        print(f"=======================================================")
        
        # Verifica se o usuário colocou o conteúdo no arquivo data/cookies.txt
        if COOKIES_TXT_PATH.exists() and COOKIES_TXT_PATH.stat().st_size > 20:
            with open(COOKIES_TXT_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
            # Ignora se for apenas o texto de instrução padrão
            if "cf_clearance" in content or "curl" in content or "workana" in content:
                print(f"📄 Arquivo '{COOKIES_TXT_PATH.name}' detectado com dados!")
                if save_manual_cookies(platform_key, content):
                    return
        
        print("Opção 1: Cole no arquivo 'data/cookies.txt' e execute novamente.")
        print("Opção 2: Cole o cURL ou texto de cookies diretamente aqui no terminal.\n")
        print("💡 DICA: Na aba 'Rede' (Network) do F12, filtre por 'Doc' e dê F5.")
        print("   Copie o cURL da primeira requisição ('jobs' ou 'workana.com').")
        print(f"=======================================================\n")
        
        raw_cookies = read_input_multiline()
        if raw_cookies:
            save_manual_cookies(platform_key, raw_cookies)
        return

    # Modo Automatizado com Patchright (sem vazamento de CDP)
    try:
        from patchright.async_api import async_playwright
    except ImportError:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("❌ Patchright/Playwright não instalado. Instale com: uv sync")
            return

    print(f"\n=======================================================")
    print(f"🔐 CONECTANDO CONTA PESSOAL: {platform.upper()}")
    print(f"=======================================================")
    if platform_key == "linkedin":
        print(f"1. O Google Chrome será aberto na página de login do LinkedIn.")
        print(f"2. Faça login normalmente na sua conta (senha, código 2FA ou conta Google).")
        print(f"3. Assim que você estiver conectado e visualizando seu Feed no LinkedIn:")
        print(f"   Volte AQUI neste terminal e pressione [ENTER].")
        print(f"4. Seus cookies de acesso (li_at) serão salvos com segurança.")
        print(f"💡 DICA: Se preferir colar os cookies diretamente, use: uv run python main.py --login linkedin --manual")
    else:
        print(f"1. O Google Chrome nativo será aberto via Patchright (anti-detecção de CDP).")
        print(f"2. Se o Cloudflare exibir uma caixinha de verificação, clique nela suavemente.")
        print(f"3. Efetue o login com seu e-mail e senha normalmente.")
        print(f"4. Quando estiver no painel logado, volte AQUI neste terminal e pressione [ENTER].")
        print(f"💡 DICA: Se o Cloudflare insistir em loop no seu IP, use: uv run python main.py --login {platform_key} --manual")
    print(f"=======================================================\n")

    launch_kwargs = get_browser_launch_args(headless=False)

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            locale="pt-BR",
            timezone_id="America/Sao_Paulo"
        )
        page = await context.new_page()
        print(f"🌐 Acessando {login_url}...")
        await page.goto(login_url)

        # Espera interação do usuário no terminal
        await asyncio.to_thread(input, f"\n👉 Pressione [ENTER] AQUI no terminal após concluir o login no {platform.capitalize()}...")

        # Salva o arquivo de estado de sessão com todos os cookies (inclusive HttpOnly)
        await context.storage_state(path=str(session_file))
        print(f"\n✅ Sucesso! Sessão salva em: {session_file}")
        print("Agora o robô poderá acessar sua conta com segurança.")
        await browser.close()

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "99freelas"
    is_manual = "--manual" in sys.argv
    asyncio.run(record_session(target, manual=is_manual))
