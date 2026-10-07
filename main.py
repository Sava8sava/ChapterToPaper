# main.py

import argparse
import logging
import sys
import os
from urllib.parse import urlparse
from src.orchestrator import WebnovelOrchestrator
from src.persistence import SQLitePersistence

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


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("o valor deve ser maior que zero")
    return parsed

def main():
    parser = argparse.ArgumentParser(
        description="Webnovel to Kindle - Baixa capítulos de webnovels e compila em um e-book EPUB."
    )

    # Parâmetros posicionais obrigatórios conforme o README
    parser.add_argument(
        "url",
        nargs="?",
        type=str,
        help="URL do capítulo inicial da novel"
    )
    parser.add_argument(
        "num_capitulos",
        nargs="?",
        type=positive_integer,
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
        default=None,
        help="Título do e-book (padrão: título persistido ou Webnovel Traduzida)"
    )
    parser.add_argument(
        "--author",
        "-a",
        type=str,
        default=None,
        help="Autor da obra (padrão: autor persistido ou Desconhecido)"
    )
    parser.add_argument(
        "--start-number",
        type=positive_integer,
        default=1,
        help="Número correspondente à URL inicial ao cadastrar um livro novo",
    )
    parser.add_argument(
        "--book-id",
        type=positive_integer,
        default=None,
        help="ID persistido do livro (alternativa para resolver pelo URL inicial)",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Diretório do banco, cache de capítulos e EPUBs (padrão: data)",
    )
    parser.add_argument(
        "--rebuild-cache",
        nargs=2,
        type=positive_integer,
        metavar=("INICIO", "FIM"),
        help="Regenera um EPUB usando somente o cache; requer --book-id",
    )

    args = parser.parse_args()

    if args.rebuild_cache is None and (
        args.url is None or args.num_capitulos is None
    ):
        parser.error("url e num_capitulos são obrigatórios para baixar capítulos")
    if args.rebuild_cache is not None and args.book_id is None:
        parser.error("--rebuild-cache requer --book-id")

    persistence = SQLitePersistence(args.data_dir)
    persisted_book = None
    if args.book_id is not None:
        persisted_book = persistence.books.get_by_id(args.book_id)
        if persisted_book is None:
            logger.error(f"Livro não encontrado: {args.book_id}")
            persistence.close()
            sys.exit(1)

    # Define o perfil JSON: se não informado via --profile, tenta adivinhar pelo domínio da URL
    profile_path = args.profile
    if not profile_path:
        profile_path = (
            persisted_book.profile_path
            if persisted_book is not None
            else get_default_profile_from_url(args.url)
        )

    if not os.path.exists(profile_path):
        logger.error(f"Arquivo de perfil não encontrado: {profile_path}")
        logger.info("Certifique-se de passar o caminho correto usando '--profile' ou de ter o perfil correspondente em 'config/sites/'.")
        persistence.close()
        sys.exit(1)

    start_url = persisted_book.start_url if persisted_book is not None else args.url
    book_title = args.title or (
        persisted_book.title if persisted_book is not None else "Webnovel Traduzida"
    )
    author = args.author or (
        persisted_book.author if persisted_book is not None else "Desconhecido"
    )

    print("\n" + "="*60)
    print("         WEBNOVEL TO KINDLE - CONVERSOR AUTOMÁTICO")
    print("="*60)
    print(f" URL Inicial : {start_url}")
    if args.rebuild_cache is None:
        print(f" Capítulos   : {args.num_capitulos}")
    else:
        print(f" Cache       : {args.rebuild_cache[0]}-{args.rebuild_cache[1]}")
    print(f" Perfil JSON : {profile_path}")
    print("="*60 + "\n")

    try:
        # Instancia e executa o orquestrador
        orchestrator = WebnovelOrchestrator(profile_path, persistence=persistence)
        if args.rebuild_cache is None:
            caminho_epub = orchestrator.run(
                start_url=start_url,
                book_title=book_title,
                author=author,
                max_chapters=args.num_capitulos,
                start_number=args.start_number,
                book_id=args.book_id,
            )
        else:
            caminho_epub = orchestrator.rebuild_epub(
                book_id=args.book_id,
                start=args.rebuild_cache[0],
                end=args.rebuild_cache[1],
                book_title=book_title,
                author=author,
            )

        print("\n" + "="*60)
        if orchestrator.last_run_status == "partial":
            print(" E-BOOK PARCIAL GERADO; CONSULTE O LOG PARA O ERRO.")
        else:
            print(" E-BOOK GERADO COM SUCESSO!")
        print(f" Job          : {orchestrator.last_job_id}")
        print(f" Arquivo salvo em: {caminho_epub}")
        print("="*60 + "\n")

    except Exception as e:
        logger.critical(f"Erro crítico durante a execução: {e}")
        sys.exit(1)
    finally:
        persistence.close()

if __name__ == "__main__":
    main()
