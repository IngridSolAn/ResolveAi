"""Busca local e explicável por palavras-chave em chamados importados."""

import re
import unicodedata

import pandas as pd

CAMPOS_BUSCA = ("titulo", "descricao", "solucao")
STATUS_CONCLUIDOS = {"solucionado", "resolvido", "fechado", "solved", "closed"}


def _normalizar(texto: str) -> str:
    texto_sem_hifens = re.sub(r"(?<=\w)-(?=\w)", "", texto.casefold())
    texto_sem_acentos = unicodedata.normalize("NFKD", texto_sem_hifens)
    return "".join(
        caractere
        for caractere in texto_sem_acentos
        if not unicodedata.combining(caractere)
    )


def buscar_chamados(chamados: pd.DataFrame, consulta: str) -> pd.DataFrame:
    """Busca termos em título, descrição e solução e explica cada correspondência."""
    termos = list(dict.fromkeys(re.findall(r"\w+", _normalizar(consulta))))
    if not termos:
        return pd.DataFrame(
            columns=[
                *chamados.columns,
                "termos_encontrados",
                "campos_correspondentes",
            ]
        )

    campos_disponiveis = [campo for campo in CAMPOS_BUSCA if campo in chamados.columns]
    resultados: list[tuple[int, int, dict[str, str]]] = []

    for posicao, (_, chamado) in enumerate(chamados.iterrows()):
        if "status" in chamados.columns:
            status = _normalizar(str(chamado["status"]).strip())
            if status not in STATUS_CONCLUIDOS:
                continue

        textos = {
            campo: _normalizar(str(chamado[campo]))
            for campo in campos_disponiveis
        }
        termos_encontrados = [
            termo
            for termo in termos
            if any(
                re.search(rf"\b{re.escape(termo)}\b", texto)
                for texto in textos.values()
            )
        ]
        if not termos_encontrados:
            continue

        campos_correspondentes = [
            campo
            for campo, texto in textos.items()
            if any(
                re.search(rf"\b{re.escape(termo)}\b", texto)
                for termo in termos_encontrados
            )
        ]
        registro = chamado.to_dict()
        registro["termos_encontrados"] = ", ".join(termos_encontrados)
        registro["campos_correspondentes"] = ", ".join(campos_correspondentes)
        resultados.append((len(termos_encontrados), posicao, registro))

    resultados.sort(key=lambda resultado: (-resultado[0], resultado[1]))
    return pd.DataFrame(
        [resultado[2] for resultado in resultados],
        columns=[*chamados.columns, "termos_encontrados", "campos_correspondentes"],
    )
