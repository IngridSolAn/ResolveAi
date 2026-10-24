from pathlib import Path

from streamlit.testing.v1 import AppTest

CAMINHO_APP = Path(__file__).resolve().parents[1] / "app.py"


def test_exibe_previa_de_ate_dez_chamados_importados() -> None:
    app = AppTest.from_file(CAMINHO_APP, default_timeout=10).run()
    dados = "id,titulo,descricao\n" + "".join(
        f"INC-{numero},Falha {numero},Descricao {numero}\n"
        for numero in range(1, 13)
    )

    app.get("file_uploader")[0].set_value(
        ("chamados.csv", dados.encode("utf-8"), "text/csv")
    ).run()

    assert not app.exception
    assert "12 chamados importados para visualização." in app.success[0].value
    assert "Exibindo 10 de 12 chamados." in app.caption[-1].value
    assert app.dataframe[0].value.shape == (10, 3)
    assert app.dataframe[0].value.iloc[0]["id"] == "INC-1"


def test_exibe_todos_os_chamados_quando_arquivo_tem_menos_de_dez() -> None:
    app = AppTest.from_file(CAMINHO_APP, default_timeout=10).run()
    dados = b"id,titulo,descricao\nINC-1,Falha,Descricao\n"

    app.get("file_uploader")[0].set_value(
        ("chamados.csv", dados, "text/csv")
    ).run()

    assert not app.exception
    assert "Exibindo 1 de 1 chamados." in app.caption[-1].value
    assert app.dataframe[0].value.shape == (1, 3)


def test_pesquisa_chamados_importados_e_exibe_termos_correspondentes() -> None:
    app = AppTest.from_file(CAMINHO_APP, default_timeout=10).run()
    dados = (
        b"id,titulo,descricao,solucao\n"
        b"INC-1,Coletor desconecta,Falha de rede Wi-Fi,Canal ajustado\n"
        b"INC-2,Acesso lento,Sistema demora,Rede normalizada\n"
    )
    app.get("file_uploader")[0].set_value(
        ("chamados.csv", dados, "text/csv")
    ).run()

    app.text_input[0].set_value("coletor wifi").run()

    assert not app.exception
    assert any(
        "1 chamado(s) encontrado(s)." in elemento.value
        for elemento in app.markdown
    )
    assert app.dataframe[0].value.iloc[0]["id"] == "INC-1"
    assert app.dataframe[0].value.iloc[0]["termos_encontrados"] == "coletor, wifi"


def test_informa_quando_busca_nao_encontra_termos() -> None:
    app = AppTest.from_file(CAMINHO_APP, default_timeout=10).run()
    dados = b"id,titulo,descricao\nINC-1,Acesso lento,Sistema demora\n"
    app.get("file_uploader")[0].set_value(
        ("chamados.csv", dados, "text/csv")
    ).run()

    app.text_input[0].set_value("impressora").run()

    assert not app.exception
    assert "Nenhum chamado contém os termos informados." in app.info[0].value
