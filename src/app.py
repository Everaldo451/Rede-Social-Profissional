import sys
from pathlib import Path

import streamlit as st
from bson import ObjectId


def welcome() -> None:
    st.title("Rede Social Profissional")
    st.info("Rede de Conexões e Mentoria ficam disponíveis após o login da equipe.")


def main() -> None:
    st.set_page_config(page_title="Rede Social Profissional")
    user_id = st.session_state.get("authenticated_user_id")
    if not ObjectId.is_valid(user_id):
        st.navigation([st.Page(welcome, title="Início")], position="hidden").run()
        return

    # O comando do Streamlit adiciona src/ ao caminho de imports.
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from src.database import get_mongo_database, get_neo4j_session
    from src.pages.connections import connection_pages

    pages = connection_pages(user_id, get_mongo_database(), get_neo4j_session)
    st.navigation(pages).run()


if __name__ == "__main__":
    main()
