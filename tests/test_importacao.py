from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from src.importacao import ErroImportacaoCSV, importar_chamados


def test_importa_csv_com_virgulas_e_cabecalho_utf8() -> None:
    arquivo = BytesIO(
        "id,titulo,descricao\nINC-1,Falha de acesso,Erro ao entrar\n".encode("utf-8")
    )

    chamados = importar_chamados(arquivo)

    assert list(chamados.columns) == ["id", "titulo", "descricao"]
    assert chamados.iloc[0]["id"] == "INC-1"


def test_importa_csv_com_ponto_e_virgula_e_bom_utf8() -> None:
    arquivo = BytesIO(
        "\ufeffid;titulo;descricao\nINC-1;Falha de acesso;Erro ao entrar\n".encode(
            "utf-8"
        )
    )

    chamados = importar_chamados(arquivo)

    assert chamados.iloc[0]["titulo"] == "Falha de acesso"


def test_ignora_linhas_em_branco_antes_do_cabecalho() -> None:
    arquivo = BytesIO(b"\nid,titulo,descricao\nINC-1,Falha,Erro\n")

    chamados = importar_chamados(arquivo)

    assert chamados.iloc[0]["id"] == "INC-1"


def test_normaliza_espacos_e_maiusculas_nos_cabecalhos() -> None:
    arquivo = BytesIO(b" ID , Titulo , Descricao \nINC-1,Falha,Erro\n")

    chamados = importar_chamados(arquivo)

    assert list(chamados.columns) == ["id", "titulo", "descricao"]


def test_preserva_ids_com_zeros_a_esquerda() -> None:
    arquivo = BytesIO(b"id,titulo,descricao\n00123,Falha,Erro\n")

    chamados = importar_chamados(arquivo)

    assert chamados.iloc[0]["id"] == "00123"


def test_rejeita_colunas_obrigatorias_ausentes() -> None:
    arquivo = BytesIO(b"id,titulo\nINC-1,Falha\n")

    with pytest.raises(ErroImportacaoCSV, match="descricao"):
        importar_chamados(arquivo)


@pytest.mark.parametrize(
    ("linha", "coluna"),
    [
        (",,", "id"),
        ("INC-1,,Erro", "titulo"),
        ("INC-1,Falha,", "descricao"),
        ("INC-1,   ,Erro", "titulo"),
    ],
)
def test_rejeita_campo_obrigatorio_vazio(linha: str, coluna: str) -> None:
    arquivo = BytesIO(f"id,titulo,descricao\n{linha}\n".encode("utf-8"))

    with pytest.raises(ErroImportacaoCSV, match=fr"linha 2.*{coluna}"):
        importar_chamados(arquivo)


@pytest.mark.parametrize(
    "linha",
    [
        "INC-1,Falha",
        "INC-1,Falha,Erro,Campo extra",
    ],
)
def test_rejeita_linha_com_quantidade_incorreta_de_campos(linha: str) -> None:
    arquivo = BytesIO(f"id,titulo,descricao\n{linha}\n".encode("utf-8"))

    with pytest.raises(ErroImportacaoCSV, match="linha 2.*campos"):
        importar_chamados(arquivo)


def test_rejeita_aspas_nao_fechadas() -> None:
    arquivo = BytesIO(b'id,titulo,descricao\nINC-1,"Falha,Erro\n')

    with pytest.raises(ErroImportacaoCSV, match="mal formatado"):
        importar_chamados(arquivo)


def test_indica_linha_correta_apos_linha_em_branco() -> None:
    arquivo = BytesIO(b"id,titulo,descricao\n\nINC-1,,Erro\n")

    with pytest.raises(ErroImportacaoCSV, match="linha 3"):
        importar_chamados(arquivo)


def test_rejeita_csv_sem_registros() -> None:
    arquivo = BytesIO(b"id,titulo,descricao\n")

    with pytest.raises(ErroImportacaoCSV, match="importar"):
        importar_chamados(arquivo)


def test_rejeita_csv_vazio() -> None:
    with pytest.raises(ErroImportacaoCSV, match="vazio"):
        importar_chamados(BytesIO())


def test_rejeita_cabecalhos_duplicados_apos_normalizacao() -> None:
    arquivo = BytesIO(b"id, ID ,titulo,descricao\nINC-1,INC-2,Falha,Erro\n")

    with pytest.raises(ErroImportacaoCSV, match="repetidos"):
        importar_chamados(arquivo)


def test_rejeita_arquivo_com_codificacao_invalida() -> None:
    arquivo = BytesIO(b"id,titulo,descricao\nINC-1,\xff,Erro\n")

    with pytest.raises(ErroImportacaoCSV, match="UTF-8"):
        importar_chamados(arquivo)


def test_importa_arquivo_de_exemplo() -> None:
    caminho = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "samples"
        / "chamados_exemplo.csv"
    )

    with caminho.open("rb") as arquivo:
        chamados = importar_chamados(arquivo)

    assert len(chamados) == 3
    assert chamados.iloc[0]["id"] == "INC-1001"


def test_resultado_e_dataframe() -> None:
    arquivo = BytesIO(b"id,titulo,descricao\nINC-1,Falha,Erro\n")

    assert isinstance(importar_chamados(arquivo), pd.DataFrame)
