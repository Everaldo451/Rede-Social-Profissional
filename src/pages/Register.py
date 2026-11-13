import logging
from pathlib import Path

import streamlit as st
from pymongo.errors import PyMongoError

from controllers.profile.user_controller import UserController
from repositories.profile.user_organizations_repository import (
    UserOrganizationsRepository,
)
from repositories.profile.user_repository import UserRepository
from repositories.profile.user_skill_repository import UserSkillRepository
from services.profile.user_service import UserService

logger = logging.getLogger(__name__)
THEME = Path(__file__).resolve().parents[1] / "assets" / "shared" / "page_theme.css"


def _create_user_controller():
    user_service = UserService(
        UserRepository(),
        UserSkillRepository(),
        UserOrganizationsRepository(),
    )
    return UserController(user_service)


def render_registration():
    st.set_page_config(page_title="Criar conta", layout="centered")
    st.html(THEME)
    st.title("Crie sua conta")
    st.write("Faça parte da Rede Social Profissional.")

    with st.form("registration_form"):
        name = st.text_input("Nome completo", max_chars=100)
        email = st.text_input("E-mail", max_chars=254)
        password = st.text_input("Senha", type="password")
        password_confirmation = st.text_input(
            "Confirme sua senha", type="password"
        )
        submitted = st.form_submit_button("Criar conta", type="primary")

    st.page_link("pages/Login.py", label="Já tem conta? Entre")

    if not submitted:
        return
    if not name.strip() or not email.strip() or not password:
        st.error("Preencha todos os campos obrigatórios.")
        return
    if password != password_confirmation:
        st.error("As senhas não conferem.")
        return

    try:
        controller = _create_user_controller()
    except PyMongoError:
        logger.exception("Falha ao preparar o cadastro de usuário.")
        st.error("Não foi possível criar a conta no momento.")
        return

    response = controller.create(
        {"nome": name, "email": email, "senha": password}
    )
    if response.status:
        st.success(response.message)
        st.caption("Sua conta foi criada. Você já pode acessar a plataforma.")
    else:
        st.error(response.message)


render_registration()
