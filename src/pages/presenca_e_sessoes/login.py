from pathlib import Path

import streamlit as st


ASSETS = Path(__file__).resolve().parents[2] / "assets" / "login"


def render_login(sessions, *, logout_requested):
    login_area = st.empty()
    with login_area.container():
        st.html(ASSETS / "login.css")
        if logout_requested:
            st.html('<p class="login-notice" role="status">Sessão encerrada.</p>')
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
                    login_feedback = st.empty()
    if submitted:
        result = sessions.login({"email": email, "password": password})
        if not result.status:
            login_feedback.error(result.message)
            return None
        login_area.empty()
        return result.data
    return None
