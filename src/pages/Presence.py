# Painel paginado que combina os perfis do MongoDB com o estado de presença no Redis.
import logging
from pathlib import Path

import streamlit as st
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from components.shared.profile_identity import render_profile_identity
from components.shared.sidebar import render_sidebar
from repositories.profile.user_repository import UserRepository

logger = logging.getLogger(__name__)
THEME = Path(__file__).resolve().parents[1] / "assets" / "shared" / "page_theme.css"
PAGE_SIZE = 10


# Exige uma sessão autenticada antes de permitir o acesso à lista de presença.
def _current_user_id():
    from pages.Sessoes import get_authenticated_user_id

    user_id = get_authenticated_user_id()
    if not user_id:
        st.info("Entre na sua conta para acessar as presenças.")
        st.page_link("pages/Login.py", label="Ir para o login")
        st.stop()
    return user_id


# Carrega uma página de perfis, consulta quem está online e apresenta os cartões de identificação.
def main():
    st.set_page_config(page_title="Presenças", layout="wide")
    render_sidebar()
    st.html(THEME)
    _current_user_id()

    from database import get_mongo_database
    from pages.Sessoes import (
        COOKIE_NAME,
        get_cookie_controller,
        get_presence_controller,
    )

    st.title("Presenças")
    st.caption("Status de presença dos usuários, atualizado a cada 10 segundos.")
    try:
        users = UserRepository(get_mongo_database())
        total = users.count_presence_profiles()
        if not total:
            st.info("Ainda não há usuários para exibir.")
            return

        # Calcula a quantidade de páginas arredondando para cima.
        pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        page = (
            st.number_input("Página", 1, pages, 1, key="presence_page")
            if pages > 1
            else 1
        )
        profiles = users.list_presence_profiles(
            offset=(page - 1) * PAGE_SIZE,
            limit=PAGE_SIZE,
        )
        session_id = get_cookie_controller().get(COOKIE_NAME)
        # Consulta de uma vez a presença dos usuários incluídos na página atual.
        response = get_presence_controller().get_online_users(
            {"session_id": session_id},
            [profile["user_id"] for profile in profiles],
        )
    except (PyMongoError, RedisError):
        logger.exception("Falha ao carregar o painel de presenças.")
        st.error("Não foi possível carregar as presenças. Tente novamente.")
        return

    if not response.status:
        st.warning(response.message)
        return

    online_users = response.data
    st.metric(
        "Online nesta página",
        sum(profile["user_id"] in online_users for profile in profiles),
    )
    for profile in profiles:
        status = (
            "🟢 Online"
            if profile["user_id"] in online_users
            else "⚪ Offline"
        )
        with st.container(border=True):
            render_profile_identity(
                profile["user_id"],
                profile["name"],
                f"presence_{profile['user_id']}",
                status,
            )


if __name__ == "__main__":
    main()
