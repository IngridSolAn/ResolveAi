from pathlib import Path

import streamlit as st

from src.busca import buscar_chamados
from src.importacao import ErroImportacaoCSV, importar_chamados

LIMITE_PREVIA = 10

st.set_page_config(page_title="ResolveAI", page_icon="🔎")
st.title("ResolveAI")
st.write("Importe um arquivo CSV para visualizar chamados de forma local.")

st.caption(
    "O CSV precisa ter as colunas id, titulo e descricao preenchidas. "
    "status, data_abertura e solucao são opcionais."
)

arquivo_exemplo = (
    Path(__file__).resolve().parent
    / "data"
    / "samples"
    / "chamados_exemplo.csv"
)
st.download_button(
    "Baixar CSV de exemplo",
    data=arquivo_exemplo.read_bytes(),
    file_name="chamados_exemplo.csv",
    mime="text/csv",
)

arquivo_csv = st.file_uploader("Selecione um arquivo CSV", type=["csv"])

if arquivo_csv is not None:
    try:
        chamados = importar_chamados(arquivo_csv)
    except ErroImportacaoCSV as erro:
        st.error(str(erro))
    else:
        st.success(f"{len(chamados)} chamados importados para visualização.")
        st.subheader("Pesquisar chamados anteriores")
        st.caption(
            "A busca por palavras-chave verifica título, descrição e solução. "
            "Quando houver a coluna status, considera apenas chamados solucionados "
            "ou fechados. Os resultados são referências, não um diagnóstico automático."
        )
        consulta = st.text_input(
            "Descreva o problema ou informe palavras-chave",
            placeholder="Ex.: coletor desconecta Wi-Fi",
        )
        if consulta.strip():
            resultados = buscar_chamados(chamados, consulta)
            if resultados.empty:
                st.info("Nenhum chamado contém os termos informados.")
            else:
                st.write(f"{len(resultados)} chamado(s) encontrado(s).")
                colunas_explicacao = [
                    "termos_encontrados",
                    "campos_correspondentes",
                ]
                colunas_prioritarias = ["id", "titulo", *colunas_explicacao]
                colunas_exibicao = [
                    *[coluna for coluna in colunas_prioritarias if coluna in resultados],
                    *[
                        coluna
                        for coluna in resultados.columns
                        if coluna not in colunas_prioritarias
                    ],
                ]
                st.dataframe(resultados[colunas_exibicao], width="stretch")

        st.subheader("Prévia dos chamados importados")
        st.caption(
            f"Exibindo {min(len(chamados), LIMITE_PREVIA)} de {len(chamados)} chamados."
        )
        st.dataframe(chamados.head(LIMITE_PREVIA), width="stretch")
