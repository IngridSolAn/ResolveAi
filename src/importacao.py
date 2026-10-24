"""Validação e importação local de arquivos CSV de chamados."""

import csv
from io import StringIO
from typing import BinaryIO

import pandas as pd

COLUNAS_OBRIGATORIAS = ("id", "titulo", "descricao")


class ErroImportacaoCSV(ValueError):
    """Erro de leitura ou validação de um arquivo CSV de chamados."""


def importar_chamados(arquivo: BinaryIO) -> pd.DataFrame:
    """Lê um CSV e valida os cabeçalhos mínimos para importar chamados."""
    arquivo.seek(0)
    conteudo_bytes = arquivo.read()
    if not conteudo_bytes:
        raise ErroImportacaoCSV("O arquivo CSV está vazio ou não contém cabeçalho.")

    try:
        conteudo = conteudo_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as erro:
        raise ErroImportacaoCSV(
            "Não foi possível ler o arquivo como UTF-8. "
            "Salve o CSV usando essa codificação e tente novamente."
        ) from erro

    primeira_linha = next(
        (linha for linha in conteudo.splitlines() if linha.strip()), ""
    )
    if not primeira_linha:
        raise ErroImportacaoCSV("O arquivo CSV está vazio ou não contém cabeçalho.")

    try:
        dialeto = csv.Sniffer().sniff(primeira_linha, delimiters=",;\t|")
        leitor = csv.reader(StringIO(conteudo), dialeto, strict=True)
        cabecalho = next((linha for linha in leitor if linha), None)
        if cabecalho is None:
            raise ErroImportacaoCSV(
                "O arquivo CSV está vazio ou não contém cabeçalho."
            )
        linhas = []
        numeros_linha = []
        for linha in leitor:
            if not linha:
                continue
            if len(linha) != len(cabecalho):
                raise ErroImportacaoCSV(
                    f"A linha {leitor.line_num} tem {len(linha)} campos, "
                    f"mas o cabeçalho tem {len(cabecalho)}. "
                    "Confira os delimitadores e as aspas dessa linha."
                )
            linhas.append(linha)
            numeros_linha.append(leitor.line_num)
    except StopIteration as erro:
        raise ErroImportacaoCSV(
            "O arquivo CSV está vazio ou não contém cabeçalho."
        ) from erro
    except csv.Error as erro:
        raise ErroImportacaoCSV(
            "O CSV está mal formatado. Confira o cabeçalho, o delimitador e as aspas."
        ) from erro

    cabecalho_normalizado = [coluna.strip().lower() for coluna in cabecalho]

    if any(not coluna for coluna in cabecalho_normalizado):
        raise ErroImportacaoCSV("Todas as colunas do CSV precisam ter um nome.")

    if len(set(cabecalho_normalizado)) != len(cabecalho_normalizado):
        raise ErroImportacaoCSV(
            "O arquivo contém nomes de colunas repetidos. "
            "Renomeie as colunas e tente novamente."
        )

    colunas_ausentes = [
        coluna for coluna in COLUNAS_OBRIGATORIAS if coluna not in cabecalho_normalizado
    ]
    if colunas_ausentes:
        nomes = ", ".join(colunas_ausentes)
        raise ErroImportacaoCSV(
            f"Faltam colunas obrigatórias: {nomes}. "
            "O CSV precisa conter id, titulo e descricao."
        )

    if not linhas:
        raise ErroImportacaoCSV(
            "O CSV contém o cabeçalho, mas não possui chamados para importar."
        )

    chamados = pd.DataFrame(linhas, columns=cabecalho_normalizado, dtype=str)
    colunas_obrigatorias = chamados[list(COLUNAS_OBRIGATORIAS)]
    campos_vazios = colunas_obrigatorias.apply(
        lambda coluna: coluna.str.strip().eq("")
    )
    linhas_invalidas = campos_vazios.any(axis=1)
    if linhas_invalidas.any():
        posicao = int(linhas_invalidas.to_numpy().argmax())
        campos = [
            coluna
            for coluna in COLUNAS_OBRIGATORIAS
            if campos_vazios.iloc[posicao][coluna]
        ]
        nomes = ", ".join(campos)
        raise ErroImportacaoCSV(
            f"O chamado na linha {numeros_linha[posicao]} está sem valor nas "
            f"colunas obrigatórias: {nomes}."
        )

    return chamados
