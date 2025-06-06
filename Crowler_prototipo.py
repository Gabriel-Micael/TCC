import requests
from bs4 import BeautifulSoup
import re
import os
import json
import time
from urllib.parse import urljoin, urlparse

URLS_INICIAIS = [
    "https://dlmf.nist.gov/"
]

DOMINIOS_PUBLICOS = {
    "gmail.com", "hotmail.com", "outlook.com", "yahoo.com",
    "icloud.com", "live.com", "aol.com", "protonmail.com",
    "bol.com.br", "uol.com.br", "terra.com.br", "msn.com",
    "gmx.com", "ymail.com"
}

EXTENSOES_ARQUIVOS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".mp3", ".mp4",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".csv"
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

ARQUIVO_JSON = "dominios.json"
LIMITE_PAGINAS = 10000000


def carregar_dominios_existentes():
    if not os.path.exists(ARQUIVO_JSON):
        return set()
    with open(ARQUIVO_JSON, "r") as f:
        return set(json.load(f))


def salvar_dominios_json(dominios):
    with open(ARQUIVO_JSON, "w") as f:
        json.dump(sorted(dominios), f, indent=2)


def extrair_dominios_emails(html):
    padrao_email = r"[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
    return re.findall(padrao_email, html)


def url_permitida(url, host_base):
    try:
        parsed_url = urlparse(url)
        return parsed_url.scheme + "://" + parsed_url.netloc == host_base
    except:
        return False


def eh_arquivo_estatico(url):
    caminho = urlparse(url).path.lower()
    return any(caminho.endswith(ext) for ext in EXTENSOES_ARQUIVOS)


def crawler_harvard(urls_iniciais):
    visitadas = {}  # URL → status ("ok", "erro", etc.)
    fila = {url: 0 for url in urls_iniciais}  # URL → profundidade
    dominios_encontrados = carregar_dominios_existentes()

    parsed_base = urlparse(urls_iniciais[0])
    host_base = parsed_base.scheme + "://" + parsed_base.netloc

    paginas_visitadas = 0

    while fila and paginas_visitadas < LIMITE_PAGINAS:
        url, profundidade = fila.popitem()

        url = url.split("#")[0]  # Remove âncoras
        print(f"[URL LIMPA] Visitando: {url}")

        if url in visitadas or eh_arquivo_estatico(url):
            print(f"[IGNORADA] Já visitada ou é arquivo estático: {url}")
            continue

        try:
            resposta = requests.get(url, headers=HEADERS, timeout=10)
            resposta.raise_for_status()
            conteudo = resposta.text.lower()
            visitadas[url] = "ok"
            paginas_visitadas += 1
        except (requests.RequestException, UnicodeDecodeError) as e:
            print(f"[ERRO] Erro ao acessar {url}: {e}")
            visitadas[url] = f"erro: {e}"
            continue
        except Exception as e:
            print(f"[ERRO] Erro inesperado ao acessar {url}: {e}")
            visitadas[url] = f"erro: {e}"
            continue

        try:
            soup = BeautifulSoup(conteudo, "html.parser")
        except Exception as e:
            print(f"[ERRO] Erro ao parsear HTML de {url}: {e}")
            visitadas[url] = f"erro_parse: {e}"
            continue

        html = str(soup)

        for dominio in set(extrair_dominios_emails(html)):
            dominio = dominio.lower()
            if dominio not in DOMINIOS_PUBLICOS and dominio not in dominios_encontrados:
                dominios_encontrados.add(dominio)
                print(f"[NOVO DOMÍNIO] {dominio}")

        for link in soup.find_all("a", href=True):
            href = link['href']
            nova_url = urljoin(url, href).split("#")[0]

            if (
                    nova_url not in visitadas and
                    nova_url not in fila and
                    url_permitida(nova_url, host_base) and
                    not eh_arquivo_estatico(nova_url)
            ):
                fila[nova_url] = profundidade + 1
                print(f"[ADICIONADA À FILA] {nova_url}")

        print(f"[FILA] Tamanho atual: {len(fila)} URLs")

    salvar_dominios_json(dominios_encontrados)
    print(f"\n[Crawling finalizado] Páginas visitadas: {paginas_visitadas}")
    print(f"Domínios salvos: {len(dominios_encontrados)} → Arquivo: {ARQUIVO_JSON}")


if __name__ == "__main__":
    inicio = time.time()
    crawler_harvard(URLS_INICIAIS)
    fim = time.time()
    duracao = fim - inicio
    print(f"[DURAÇÃO] Tempo total de execução: {duracao:.2f} segundos")
