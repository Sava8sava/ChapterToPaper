# main.py

import argparse
import logging
import sys
import os
from urllib.parse import urlparse
from src.orchestrator import WebnovelOrchestrator

# Configuração de logging alinhada com o terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("WebnovelToKindle")

def get_default_profile_from_url(url: str) -> str:
    """
    Tenta inferir o nome do perfil JSON com base no domínio da URL.
    Ex: 'https://novelmania.com.br/novels/...' -> 'config/sites/novelmania.json'
    """
    domain = urlparse(url).netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    
    # Extrai o nome base do domínio (ex: 'novelmania.com.br' -> 'novelmania')
    base_name = domain.split('.')[0]
    return f"config/sites/{base_name}.json"

def main():
    parser = argparse.ArgumentParser(
        description="Webnovel to Kindle - Baixa capítulos de webnovels e compila em um e-book EPUB."
    )

    # Parâmetros posicionais obrigatórios conforme o README
    parser.add_argument(
        "url",
        type=str,
        help="URL do capítulo inicial da novel"
    )
    parser.add_argument(
        "num_capitulos",
        type=int,
        help="Quantidade desejada de capítulos a serem baixados"
    )

    # Parâmetros opcionais
    parser.add_argument(
        "--profile",
        "-p",
        type=str,
        default=None,
        help="Caminho do arquivo JSON do perfil do site (Ex: config/sites/novelmania.json)"
    )
    parser.add_argument(
        "--title",
        "-t",
        type=str,
        default="Webnovel Traduzida",
        help="Título do e-book a ser gerado"
    )
    parser.add_argument(
        "--author",
        "-a",
        type=str,
        default="Desconhecido",
        help="Autor da obra"
    )

    args = parser.parse_args()

    # Define o perfil JSON: se não informado via --profile, tenta adivinhar pelo domínio da URL
    profile_path = args.profile
    if not profile_path:
        profile_path = get_default_profile_from_url(args.url)

    if not os.path.exists(profile_path):
        logger.error(f"Arquivo de perfil não encontrado: {profile_path}")
        logger.info("Certifique-se de passar o caminho correto usando '--profile' ou de ter o perfil correspondente em 'config/sites/'.")
        sys.exit(1)

    print("\n" + "="*60)
    print("         WEBNOVEL TO KINDLE - CONVERSOR AUTOMÁTICO")
    print("="*60)
    print(f" URL Inicial : {args.url}")
    print(f" Capítulos   : {args.num_capitulos}")
    print(f" Perfil JSON : {profile_path}")
    print("="*60 + "\n")

    try:
        # Instancia e executa o orquestrador
        orchestrator = WebnovelOrchestrator(profile_path)
        caminho_epub = orchestrator.run(
            start_url=args.url,
            book_title=args.title,
            author=args.author,
            max_chapters=args.num_capitulos
        )

        print("\n" + "="*60)
        print(" 🎉 E-BOOK GERADO COM SUCESSO!")
        print(f" Arquivo salvo em: {caminho_epub}")
        print("="*60 + "\n")

    except Exception as e:
        logger.critical(f"Erro crítico durante a execução: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
