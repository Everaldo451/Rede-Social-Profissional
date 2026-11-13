import logging

import streamlit as st
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


@st.fragment(run_every="10s")
def _update_presence(session_id):
    from pages.Sessoes import get_presence_controller

    try:
        response = get_presence_controller().update_last_seen(
            {"session_id": session_id}
        )
    except RedisError:
        logger.exception("Falha ao atualizar a presença do usuário.")
        st.warning("Não foi possível atualizar sua presença.")
        return
    if not response.status:
        st.warning(response.message)


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
    sidebar.markdown("### Rede Social")

    try:
        from pages.Sessoes import get_authenticated_user_id

        user_id = get_authenticated_user_id()
    except RedisError:
        logger.exception("Falha ao verificar a sessão na barra lateral.")
        sidebar.error("Não foi possível verificar sua sessão.")
        return

    sidebar.page_link("app.py", label="Feed", icon=":material/dynamic_feed:")
    if not user_id:
        sidebar.page_link("pages/Login.py", label="Entrar", icon=":material/login:")
        sidebar.page_link("pages/Register.py", label="Criar conta", icon=":material/person_add:")
        return

    from pages.Sessoes import COOKIE_NAME, get_cookie_controller

    session_id = get_cookie_controller().get(COOKIE_NAME)
    if session_id:
        _update_presence(session_id)

    sidebar.caption("Minha rede")
    sidebar.page_link("pages/RedeDeConexoes.py", label="Conexões", icon=":material/hub:")
    sidebar.page_link("pages/Mentoria.py", label="Mentoria", icon=":material/school:")
    sidebar.page_link("pages/Presence.py", label="Presenças", icon=":material/groups:")
    sidebar.page_link("pages/Notificacoes.py", label="Notificações", icon=":material/notifications:")
    sidebar.caption("Minha conta")
    if sidebar.button("Meu perfil", key="current_profile", icon=":material/person:", width="stretch"):
        st.switch_page(
            "pages/Profile.py",
            query_params={"user_id": str(user_id)},
        )
    sidebar.page_link("pages/Sessoes.py", label="Sessões", icon=":material/devices:")
    if sidebar.button("Sair", icon=":material/logout:"):
        _logout()
