import streamlit as st

from components.shared.flash import set_flash, show_flash
from components.shared.header import render_header


def render_auth(container, cookies) -> None:
    render_header()
    st.write("")
    show_flash()
    login_tab, register_tab = st.tabs(["Entrar", "Criar conta"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("E-mail")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", type="primary")
        if submitted:
            result = container.sessions.login({"email": email, "password": password})
            if result.status:
                st.session_state["token"] = result.data["token"]
                cookies.set("session_token", result.data["token"])
                st.rerun()
            st.error(result.message)

    with register_tab:
        with st.form("register_form"):
            name = st.text_input("Nome completo")
            headline = st.text_input("Cargo ou área (ex.: Dev Backend Python)")
            email = st.text_input("E-mail", key="register_email")
            password = st.text_input("Senha (mín. 8 caracteres)", type="password", key="register_password")
            submitted = st.form_submit_button("Criar conta", type="primary")
        if submitted:
            result = container.users.register(
                {"name": name, "headline": headline, "email": email, "password": password}
            )
            if result.status:
                set_flash("success", "Conta criada! Entre com seu e-mail e senha.")
                st.rerun()
            st.error(result.message)
