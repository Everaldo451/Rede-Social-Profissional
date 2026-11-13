# Testes de navegador para consulta, foto e permissões de edição do perfil profissional.
import os
from datetime import datetime, timezone
from pathlib import Path
from secrets import token_urlsafe

from bson import ObjectId
from gridfs import GridFSBucket
from playwright.sync_api import Page

from repositories.profile.organization_repository import OrganizationRepository
from repositories.profile.skill_repository import SkillRepository
from repositories.profile.user_organizations_repository import (
    UserOrganizationsRepository,
)
from repositories.profile.user_repository import UserRepository
from repositories.profile.user_skill_repository import UserSkillRepository
from repositories.shared.media_repository import MediaRepository
from repositories.sessions.online_presence_repository import OnlinePresenceRepository
from repositories.sessions.session_repository import SessionRepository

BASE_URL = os.getenv("BASE_URL", "http://localhost:8501")


# Prepara os dados de perfil e suas referências para os cenários de navegador.
def _create_profile_records(repository_resources):
    database = repository_resources.mongo
    user_repository = UserRepository(database)
    skill_repository = SkillRepository(database)
    organization_repository = OrganizationRepository(database)
    user_skill_repository = UserSkillRepository(
        database=database,
        session_factory=repository_resources.neo4j_session_factory,
    )
    user_organization_repository = UserOrganizationsRepository(
        database=database,
        session_factory=repository_resources.neo4j_session_factory,
    )

    user = user_repository.create(
        {
            "nome": "Ana Silva",
            "email": f"ana+{ObjectId()}@example.com",
            "senha": "$2b$12$fake-test-hash",
            "headline": "Desenvolvedora Backend",
            "resumo": "Desenvolve APIs para produtos digitais.",
            "localizacao": "João Pessoa, PB",
            "nivel_carreira": "Pleno",
            "aceita_mentoria": True,
            "experiencias": [],
            "formacao": [],
            "certificacoes": [],
        }
    )
    repository_resources.track_document("usuarios", user["_id"])

    skill = skill_repository.create(
        {
            "nome": "Python",
            "categoria": "Linguagem de Programação",
            "descricao": "Linguagem usada em aplicações e automação.",
        }
    )
    repository_resources.track_document("habilidades", skill["_id"])

    organizations = [
        {
            "nome": "Tech Solutions",
            "tipos": ["empresa"],
            "setor": "Tecnologia",
        },
        {
            "nome": "Universidade Federal da Paraíba",
            "tipos": ["instituicao_ensino"],
        },
        {
            "nome": "Amazon Web Services",
            "tipos": ["empresa", "emissor_certificacao"],
        },
    ]
    organization_ids = []
    for organization_data in organizations:
        organization = organization_repository.create(organization_data)
        repository_resources.track_document("organizacoes", organization["_id"])
        organization_ids.append(organization["_id"])
    organization_id, institution_id, issuer_id = organization_ids

    repository_resources.track_graph_nodes(
        user["_id"],
        skill["_id"],
        organization_id,
        institution_id,
        issuer_id,
    )

    user_skill_repository.add_skill(
        user["_id"],
        skill["_id"],
        "has",
        nivel="intermediario",
        experiencia_anos=2,
    )
    user_skill_repository.add_skill(
        user["_id"],
        skill["_id"],
        "teaches",
        nivel="avancado",
        experiencia_anos=4,
        modalidade="online",
        disponibilidade="noite",
    )
    user_organization_repository.add_experience(
        user["_id"],
        {
            "organizacao_id": organization_id,
            "cargo": "Desenvolvedora Backend",
            "data_inicio": datetime(2024, 3, 1, tzinfo=timezone.utc),
            "atual": True,
            "descricao": "Desenvolvimento de APIs REST",
        },
    )
    user_organization_repository.add_education(
        user["_id"],
        {
            "instituicao_id": institution_id,
            "curso": "Ciência da Computação",
            "grau": "bacharelado",
            "ano_inicio": 2022,
        },
    )
    user_organization_repository.add_membership(
        user["_id"],
        organization_id,
        "Mentora",
        "ativa",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    database["usuarios"].update_one(
        {"_id": ObjectId(user["_id"])},
        {
            "$set": {
                "certificacoes": [
                    {
                        "nome": "AWS Cloud Practitioner",
                        "emissor_id": ObjectId(issuer_id),
                        "data_emissao": datetime(2025, 6, 15, tzinfo=timezone.utc),
                        "url": "https://example.com/certificado",
                    }
                ]
            }
        },
    )
    return user


# Confere a apresentação dos dados do usuário e de seus vínculos na visualização do perfil.
def test_profile_page_displays_read_only_user_and_relationship_data(
    page: Page, repository_resources
):
    user = _create_profile_records(repository_resources)
    page.goto(f"{BASE_URL}/profile?user_id={user['_id']}")

    page.get_by_role("heading", name="Ana Silva").wait_for()
    page.get_by_text("Python", exact=True).first.wait_for()
    body = page.locator("body").inner_text()

    assert "Desenvolvedora Backend" in body
    assert "João Pessoa, PB" in body
    assert "Python" in body
    assert "Ensina" in body
    assert "Tech Solutions" in body
    assert "Universidade Federal da Paraíba" in body
    assert "Amazon Web Services" in body
    assert "Desenvolvimento de APIs REST" in body
    assert "AWS Cloud Practitioner" in body
    assert user["email"] not in body
    assert "fake-test-hash" not in body
    assert page.get_by_role("textbox").count() == 0
    assert page.get_by_role("button", name="Conectar").count() == 0
    assert page.locator(".profile-photo-svg svg").count() == 1


# Exercita o cenário de consulta da presença por um visitante anônimo.
def test_profile_page_shows_presence_to_anonymous_visitors(
    page: Page, repository_resources
):
    user = _create_profile_records(repository_resources)
    presence = OnlinePresenceRepository()
    key = f"presence:{user['_id']}"
    presence.client.set(key, "online", ex=60)

    try:
        page.goto(f"{BASE_URL}/profile?user_id={user['_id']}")

        page.get_by_role("heading", name="Ana Silva").wait_for()
        page.get_by_text("Presença: 🟢 Online", exact=True).wait_for()
        assert page.get_by_role("button", name="Conectar").count() == 0
    finally:
        presence.client.delete(key)


# Verifica a apresentação da foto pública do perfil.
def test_profile_page_displays_public_profile_photo(page: Page, repository_resources):
    user = _create_profile_records(repository_resources)
    media_repository = MediaRepository(repository_resources.mongo)
    media = media_repository.create(
        {
            "filename": "profile-test.svg",
            "content": (
                Path(__file__).parents[2] / "media" / "assets" / "profile-test.svg"
            ).read_bytes(),
            "metadata": {
                "proprietario_tipo": "usuario",
                "tipo_mime": "image/svg+xml",
                "tipo": "imagem_perfil",
                "visibilidade": "publica",
                "proprietario_id": user["_id"],
            },
        }
    )
    try:
        page.goto(f"{BASE_URL}/profile?user_id={user['_id']}")
        page.locator(".profile-photo-svg svg").wait_for()
        assert page.locator(".profile-photo-svg svg").count() == 1
    finally:
        GridFSBucket(
            repository_resources.mongo, bucket_name="midias"
        ).delete(ObjectId(media["media_id"]))


# Confere o tratamento de um usuário inexistente na tela.
def test_profile_page_reports_missing_user(page: Page, repository_resources):
    missing_user_id = repository_resources.ids["user"]
    page.goto(f"{BASE_URL}/profile?user_id={missing_user_id}")

    page.get_by_text("Usuário não encontrado.", exact=True).wait_for()


# Exercita a edição do perfil pelo próprio proprietário.
def test_profile_page_allows_owner_to_edit_their_profile(
    page: Page, repository_resources
):
    user = _create_profile_records(repository_resources)
    session_id = token_urlsafe(32)
    sessions = SessionRepository()
    sessions.create(session_id, user["_id"])
    page.context.add_cookies(
        [
            {
                "name": "rede_social_session",
                "value": session_id,
                "url": BASE_URL,
            }
        ]
    )

    try:
        page.goto(BASE_URL)
        page.get_by_role("button", name="Perfil").wait_for()
        page.get_by_role("button", name="Perfil").click()
        page.wait_for_url(f"**/profile?user_id={user['_id']}")
        page.get_by_role("button", name="Salvar perfil").wait_for()
        page.get_by_role("textbox", name="Título profissional").fill(
            "Engenheira de Plataforma"
        )
        page.get_by_role("button", name="Salvar perfil").click()
        page.get_by_text("Perfil atualizado com sucesso.").wait_for()
        page.get_by_text("Engenheira de Plataforma", exact=True).wait_for()
        page.get_by_text("Alterar imagem de perfil", exact=True).wait_for()
    finally:
        sessions.delete(session_id)


# Verifica a ausência de permissão para editar o perfil de outra pessoa.
def test_profile_page_does_not_allow_editing_another_user_profile(
    page: Page, repository_resources
):
    viewer = _create_profile_records(repository_resources)
    profile_owner = UserRepository(repository_resources.mongo).create(
        {
            "nome": "Bruno Costa",
            "email": f"bruno+{ObjectId()}@example.com",
            "senha": "$2b$12$fake-test-hash",
            "headline": "Analista de Dados",
            "experiencias": [],
            "formacao": [],
            "certificacoes": [],
        }
    )
    repository_resources.track_document("usuarios", profile_owner["_id"])
    session_id = token_urlsafe(32)
    sessions = SessionRepository()
    sessions.create(session_id, viewer["_id"])
    page.context.add_cookies(
        [
            {
                "name": "rede_social_session",
                "value": session_id,
                "url": BASE_URL,
            }
        ]
    )

    try:
        page.goto(f"{BASE_URL}/profile?user_id={profile_owner['_id']}")
        page.get_by_role("heading", name="Bruno Costa").wait_for()
        page.get_by_role("button", name="Conectar").wait_for()
        page.get_by_role("button", name="Logout").wait_for()
        page.get_by_role("link", name="Rede de Conexões").wait_for()
        page.get_by_role("link", name="Mentoria").wait_for()
        page.get_by_role("link", name="Notificações").wait_for()
        page.get_by_role("link", name="Sessões").wait_for()
        assert page.get_by_text("Alterar imagem de perfil", exact=True).count() == 0
        assert page.get_by_role("button", name="Salvar perfil").count() == 0
        assert page.get_by_role("button", name="Adicionar habilidade").count() == 0
        page.get_by_role("button", name="Logout").click()
        page.get_by_text("Sessão encerrada.", exact=True).wait_for()
        assert sessions.get_by_id(session_id) is None
    finally:
        sessions.delete(session_id)


# Confere o tratamento de um identificador de usuário inválido.
def test_profile_page_rejects_invalid_user_id(page: Page):
    page.goto(f"{BASE_URL}/profile?user_id=invalid")

    page.get_by_text("O identificador do usuário é inválido.", exact=True).wait_for()
