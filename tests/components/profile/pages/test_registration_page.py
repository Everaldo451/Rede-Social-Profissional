import os

from bson import ObjectId
from playwright.sync_api import Page

from common.security import verify_password
from repositories.profile.user_repository import UserRepository

BASE_URL = os.getenv("BASE_URL", "http://localhost:8501")


def test_login_and_registration_pages_link_to_each_other(page: Page):
    page.goto(f"{BASE_URL}/login")
    page.get_by_role("link", name="Home").wait_for()
    page.get_by_role("link", name="Login").wait_for()
    page.get_by_role("link", name="Cadastro").wait_for()
    page.get_by_role(
        "link", name="Não tem uma conta? Cadastre-se"
    ).click()
    page.get_by_role("heading", name="Crie sua conta").wait_for()
    page.get_by_role("link", name="Já tem conta? Entre").click()
    page.get_by_role("button", name="Entrar").wait_for()


def _fill_registration_form(page, *, name, email, password, confirmation=None):
    page.get_by_label("Nome completo").fill(name)
    page.get_by_label("E-mail").fill(email)
    page.get_by_role("textbox", name="Senha", exact=True).fill(password)
    page.get_by_label("Confirme sua senha").fill(
        confirmation if confirmation is not None else password
    )


def test_registration_page_creates_user_and_hashes_password(
    page: Page, repository_resources
):
    email = f"novo+{ObjectId()}@example.com"
    password = "senha-segura-123"
    page.goto(f"{BASE_URL}/register")

    _fill_registration_form(
        page,
        name="  Nova Pessoa ",
        email=email.upper(),
        password=password,
    )
    page.get_by_role("button", name="Criar conta").click()

    page.get_by_text("Conta criada com sucesso!", exact=True).wait_for()
    user = UserRepository(repository_resources.mongo).get_by_email(email)
    assert user is not None
    assert user["nome"] == "Nova Pessoa"
    assert user["email"] == email
    assert user["senha"] != password
    assert verify_password(password, user["senha"])
    repository_resources.track_document("usuarios", user["_id"])


def test_registration_page_reports_duplicate_email(page: Page, repository_resources):
    email = f"existente+{ObjectId()}@example.com"
    users = UserRepository(repository_resources.mongo)
    user = users.create(
        {
            "nome": "Conta existente",
            "email": email,
            "senha": "$2b$12$fake-test-hash",
        }
    )
    repository_resources.track_document("usuarios", user["_id"])
    page.goto(f"{BASE_URL}/register")

    _fill_registration_form(
        page,
        name="Outra Pessoa",
        email=email,
        password="senha-segura-123",
    )
    page.get_by_role("button", name="Criar conta").click()

    page.get_by_text("Este e-mail já está cadastrado.", exact=True).wait_for()


def test_registration_page_rejects_mismatched_passwords(page: Page):
    page.goto(f"{BASE_URL}/register")
    _fill_registration_form(
        page,
        name="Nova Pessoa",
        email=f"novo+{ObjectId()}@example.com",
        password="senha-segura-123",
        confirmation="outra-senha-123",
    )
    page.get_by_role("button", name="Criar conta").click()

    page.get_by_text("As senhas não conferem.", exact=True).wait_for()
