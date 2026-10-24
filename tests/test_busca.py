import pandas as pd

from src.busca import buscar_chamados


def test_busca_encontra_termos_em_titulo_descricao_e_solucao() -> None:
    chamados = pd.DataFrame(
        [
            {
                "id": "INC-1",
                "titulo": "Coletor desconecta",
                "descricao": "Falha de rede Wi-Fi",
                "solucao": "Canal ajustado",
            },
            {
                "id": "INC-2",
                "titulo": "Acesso lento",
                "descricao": "Sistema demora",
                "solucao": "Rede normalizada",
            },
        ]
    )

    resultados = buscar_chamados(chamados, "coletor wifi canal")

    assert resultados["id"].tolist() == ["INC-1"]
    assert resultados.iloc[0]["termos_encontrados"] == "coletor, wifi, canal"
    assert resultados.iloc[0]["campos_correspondentes"] == "titulo, descricao, solucao"


def test_busca_ignora_acentos_e_diferenca_entre_maiusculas() -> None:
    chamados = pd.DataFrame(
        [{"id": "INC-1", "titulo": "Conexão Wi-Fi", "descricao": "Falha", "solucao": ""}]
    )

    resultados = buscar_chamados(chamados, "CONEXAO wifi")

    assert resultados["id"].tolist() == ["INC-1"]
    assert resultados.iloc[0]["termos_encontrados"] == "conexao, wifi"


def test_ordena_por_quantidade_de_termos_encontrados() -> None:
    chamados = pd.DataFrame(
        [
            {"id": "INC-1", "titulo": "Impressora", "descricao": "Falha", "solucao": ""},
            {
                "id": "INC-2",
                "titulo": "Impressora sem conexão",
                "descricao": "Falha de rede",
                "solucao": "",
            },
        ]
    )

    resultados = buscar_chamados(chamados, "impressora conexão rede")

    assert resultados["id"].tolist() == ["INC-2", "INC-1"]


def test_nao_corresponde_apenas_parte_de_uma_palavra() -> None:
    chamados = pd.DataFrame(
        [{"id": "INC-1", "titulo": "Coletores sem conexão", "descricao": "Falha"}]
    )

    resultados = buscar_chamados(chamados, "coletor")

    assert resultados.empty


def test_consulta_vazia_nao_retorna_resultados() -> None:
    chamados = pd.DataFrame([{"id": "INC-1", "titulo": "Impressora"}])

    resultados = buscar_chamados(chamados, "   ")

    assert resultados.empty
    assert "termos_encontrados" in resultados.columns


def test_consulta_sem_correspondencias_nao_retorna_chamados() -> None:
    chamados = pd.DataFrame(
        [{"id": "INC-1", "titulo": "Impressora", "descricao": "Sem papel"}]
    )

    assert buscar_chamados(chamados, "coletor").empty


def test_busca_funciona_sem_coluna_opcional_solucao() -> None:
    chamados = pd.DataFrame(
        [{"id": "INC-1", "titulo": "Acesso", "descricao": "Erro de rede"}]
    )

    resultados = buscar_chamados(chamados, "rede")

    assert resultados["id"].tolist() == ["INC-1"]
    assert resultados.iloc[0]["campos_correspondentes"] == "descricao"


def test_busca_exclui_chamados_nao_concluidos_quando_status_existe() -> None:
    chamados = pd.DataFrame(
        [
            {
                "id": "INC-1",
                "titulo": "Coletor desconecta",
                "descricao": "Falha de rede",
                "status": "Em andamento",
            },
            {
                "id": "INC-2",
                "titulo": "Coletor desconecta",
                "descricao": "Falha de rede",
                "status": "Solucionado",
            },
            {
                "id": "INC-3",
                "titulo": "Coletor desconecta",
                "descricao": "Falha de rede",
                "status": "Fechado",
            },
        ]
    )

    resultados = buscar_chamados(chamados, "coletor")

    assert resultados["id"].tolist() == ["INC-2", "INC-3"]
