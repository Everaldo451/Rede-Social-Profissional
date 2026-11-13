import logging

import streamlit as st
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


def _logout():
    from pages.Sessoes import COOKIE_NAME, build_runtime, get_cookie_controller

    cookies = get_cookie_controller()
    session_id = cookies.get(COOKIE_NAME)
    if session_id:
        try:
            sessions, _, _ = build_runtime()
            response = sessions.logout({"session_id": session_id})
            if not response.status:
                st.session_state["logout_error"] = response.message
        except RedisError:
            logger.exception("Falha ao encerrar a sessão pela barra lateral.")
            st.session_state["logout_error"] = (
                "Não foi possível confirmar o encerramento da sessão."
            )
        finally:
            cookies.remove(
                COOKIE_NAME,
                secure=(st.context.url or "").startswith("https://"),
            )

    st.session_state["logout_requested"] = True
    st.switch_page("pages/Login.py")


def render_sidebar():
    sidebar = st.sidebar
    sidebar.title("Rede Social")

    try:
        from pages.Sessoes import get_authenticated_user_id

        user_id = get_authenticated_user_id()
    except RedisError:
        logger.exception("Falha ao verificar a sessão na barra lateral.")
        sidebar.error("Não foi possível verificar sua sessão.")
        return

    sidebar.page_link("app.py", label="Home")
    if not user_id:
        sidebar.page_link("pages/Login.py", label="Login")
        sidebar.page_link("pages/Register.py", label="Cadastro")
        return

    sidebar.divider()
    sidebar.page_link("pages/Profile.py", label="Perfil")
    sidebar.page_link("pages/RedeDeConexoes.py", label="Rede de Conexões")
    sidebar.page_link("pages/Mentoria.py", label="Mentoria")
    sidebar.page_link("pages/Notificacoes.py", label="Notificações")
    sidebar.page_link("pages/Sessoes.py", label="Sessões")
    sidebar.divider()
    if sidebar.button("Logout", type="secondary", use_container_width=True):
        _logout()