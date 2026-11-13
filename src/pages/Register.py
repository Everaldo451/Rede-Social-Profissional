# Tela de criação de conta com confirmação da senha e retorno das validações.
import logging
from pathlib import Path

import streamlit as st
from pymongo.errors import PyMongoError

from components.shared.sidebar import render_sidebar
from controllers.profile.user_controller import UserController
from repositories.profile.user_organizations_repository import (
    UserOrganizationsRepository,
)
from repositories.profile.user_repository import UserRepository
from repositories.profile.user_skill_repository import UserSkillRepository
from services.profile.user_service import UserService

logger = logging.getLogger(__name__)
THEME = Path(__file__).resolve().parents[1] / "assets" / "shared" / "page_theme.css"


# Monta o controller de usuários com os serviços e repositórios de perfil.
def _create_user_controller():
    user_service = UserService(
        UserRepository(),
        UserSkillRepository(),
        UserOrganizationsRepository(),
    )
    return UserController(user_service)


# Coleta os dados de cadastro, verifica a confirmação da senha e apresenta o resultado.
def render_registration():
    st.set_page_config(page_title="Criar conta", layout="centered")
    render_sidebar()
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
    # As verificações do formulário precedem a validação detalhada do controller e do DTO.
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

    # Envia somente os campos da conta; a confirmação da senha serve apenas ao formulário.
    response = controller.create(
        {"nome": name, "email": email, "senha": password}
    )
    if response.status:
        st.success(response.message)
        st.caption("Sua conta foi criada. Você já pode acessar a plataforma.")
    else:
        st.error(response.message)


render_registration()
