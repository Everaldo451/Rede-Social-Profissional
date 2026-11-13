from pathlib import Path

import streamlit as st

from components.shared.sidebar import render_sidebar

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "login"
THEME = Path(__file__).resolve().parents[1] / "assets" / "shared" / "page_theme.css"


def render_login(sessions, *, logout_requested, logout_error=None):
    login_area = st.empty()
    with login_area.container():
        st.html(THEME)
        st.html(ASSETS / "login.css")
        if logout_requested:
            st.html('<p class="login-notice" role="status">Sessão encerrada.</p>')
        if logout_error:
            st.warning(logout_error)
        with st.container(key="login_card"):
            illustration, credentials = st.columns([1.25, 1], gap=None)
            with illustration:
                st.image(str(ASSETS / "login.png"), width="stretch")
            with credentials:
                with st.container(key="login_credentials"):
                    st.html("""
                        <div class="login-brand">Rede Social Profissional</div>
                        <h1 class="login-heading">Olá,<br>boas-vindas!</h1>
                        <p class="login-copy">Entre na sua conta para acessar sua rede.</p>
                    """)
                    with st.form("login", clear_on_submit=True, border=False):
                        email = st.text_input("E-mail", placeholder="voce@exemplo.com")
                        password = st.text_input("Senha", type="password")
                        submitted = st.form_submit_button("Entrar", width="stretch")
                    st.page_link(
                        "pages/Register.py",
                        label="Não tem uma conta? Cadastre-se",
                    )
                    login_feedback = st.empty()
    if submitted:
        result = sessions.login({"email": email, "password": password})
        if not result.status:
            login_feedback.error(result.message)
            return None
        login_area.empty()
        return result.data
    return None


def render_page():
    st.set_page_config(page_title="Entrar", layout="wide")
    render_sidebar()
    from pages.Sessoes import COOKIE_NAME, build_runtime, get_cookie_controller

    sessions, _, _ = build_runtime()
    cookies = get_cookie_controller()
    session = {"session_id": cookies.get(COOKIE_NAME)}
    logout_requested = st.session_state.pop("logout_requested", False)
    logout_error = st.session_state.pop("logout_error", None)
    if session["session_id"] and sessions.get_current_user(session).status:
        st.switch_page("pages/Sessoes.py")
        return

    session_id = render_login(
        sessions,
        logout_requested=logout_requested,
        logout_error=logout_error,
    )
    if session_id is not None:
        cookies.set(
            COOKIE_NAME,
            session_id,
            secure=(st.context.url or "").startswith("https://"),
        )
        st.switch_page("pages/Sessoes.py")


if __name__ == "__main__":
    render_page()
