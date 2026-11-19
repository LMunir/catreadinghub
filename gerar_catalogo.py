import json
import re
import unicodedata
from pathlib import Path

PASTA_ACERVO = Path("acervo")
ARQUIVO_SAIDA = Path("catalogo.json")
EXTENSOES_SUPORTADAS = {".pdf", ".epub"}


def gerar_slug(texto: str) -> str:
    """Gera um ID determinístico e limpo para manter o progresso salvo no IndexedDB."""
    normalizado = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    limpo = re.sub(r"[^a-zA-Z0-9]+", "-", normalizado.lower()).strip("-")
    return f"nativo-{limpo}"


def inferir_tipo(nome_bruto: str) -> str:
    """Detecta o tipo de documento caso conste no nome do arquivo."""
    lower = nome_bruto.lower()
    if "bula" in lower:
        return "Bula"
    if "exortação" in lower or "exortacao" in lower:
        return "Exortação"
    if "motu proprio" in lower:
        return "Motu Proprio"
    return "Encíclica"


def extrair_metadados(caminho: Path) -> dict:
    nome_sem_ext = caminho.stem
    formato = caminho.suffix.lstrip(".").lower()
    tipo = inferir_tipo(nome_sem_ext)

    # Remove prefixos explícitos de tipo caso existam (ex: "[Bula] " ou "Bula - ")
    nome_limpo = re.sub(
        r"^(\[?(encíclica|enciclica|bula|exortação|exortacao|motu proprio)\]?\s*[-–:]?\s*)",
        "",
        nome_sem_ext,
        flags=re.IGNORECASE,
    ).strip()

    partes = [p.strip() for p in re.split(r"\s+-\s+", nome_limpo) if p.strip()]

    papa = "Desconhecido"
    ano = 0
    titulo = nome_limpo

    # Padrão 1: Papa - Ano - Título (Ex: Leão XIII - 1891 - Rerum Novarum)
    if len(partes) >= 3 and re.fullmatch(r"\d{3,4}", partes[1]):
        papa = partes[0]
        ano = int(partes[1])
        titulo = " - ".join(partes[2:])

    # Padrão 2: Papa - Título (Ex: Pio XI - Quadragesimo Anno)
    elif len(partes) == 2:
        if re.fullmatch(r"\d{3,4}", partes[0]):
            ano = int(partes[0])
            titulo = partes[1]
        else:
            papa = partes[0]
            titulo = partes[1]

    # Padrão 3: Nome livre (tenta capturar algum ano solto no nome, ex: "Rerum Novarum (1891)")
    else:
        match_ano = re.search(r"\b(\d{4})\b", nome_limpo)
        if match_ano:
            ano = int(match_ano.group(1))
            titulo = re.sub(r"[\(\[\-]?\b\d{4}\b[\)\]]?", "", nome_limpo).strip(" -_")
        else:
            titulo = nome_limpo.replace("_", " ").strip()

    return {
        "id": gerar_slug(f"{papa}-{ano}-{titulo}" if ano else titulo),
        "titulo": titulo,
        "papa": papa,
        "ano": ano,
        "tipo": tipo,
        "formato": formato,
        # .as_posix() garante barras "/" mesmo rodando no Windows
        "arquivo": caminho.as_posix(),
    }


def main():
    if not PASTA_ACERVO.exists():
        PASTA_ACERVO.mkdir(parents=True)
        print(f"Pasta '{PASTA_ACERVO}/' criada. Adicione seus PDFs/EPUBs nela e rode novamente.")
        return

    arquivos = sorted(
        [
            f
            for f in PASTA_ACERVO.rglob("*")
            if f.is_file() and f.suffix.lower() in EXTENSOES_SUPORTADAS
        ],
        key=lambda x: x.name.lower(),
    )

    catalogo = [extrair_metadados(arq) for arq in arquivos]

    # Ordena cronologicamente (documentos sem ano vão para o final) e depois por título
    catalogo.sort(key=lambda item: (item["ano"] == 0, item["ano"], item["titulo"].lower()))

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)

    print(f"Sucesso: {len(catalogo)} documento(s) indexado(s) em '{ARQUIVO_SAIDA}'.")


if __name__ == "__main__":
    main()