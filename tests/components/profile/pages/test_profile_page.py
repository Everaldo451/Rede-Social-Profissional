import os
from datetime import datetime, timezone

from bson import ObjectId
from playwright.sync_api import Page

from repositories.profile.organization_repository import OrganizationRepository
from repositories.profile.skill_repository import SkillRepository
from repositories.profile.user_organizations_repository import (
    UserOrganizationsRepository,
)
from repositories.profile.user_repository import UserRepository
from repositories.profile.user_skill_repository import UserSkillRepository

BASE_URL = os.getenv("BASE_URL", "http://localhost:8501")


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


def test_profile_page_displays_read_only_user_and_relationship_data(
    page: Page, repository_resources
):
    user = _create_profile_records(repository_resources)
    page.goto(f"{BASE_URL}/profile?user_id={user['_id']}")

    page.get_by_role("heading", name="Ana Silva").wait_for()
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


def test_profile_page_reports_missing_user(page: Page, repository_resources):
    missing_user_id = repository_resources.ids["user"]
    page.goto(f"{BASE_URL}/profile?user_id={missing_user_id}")

    page.get_by_text("Usuário não encontrado.", exact=True).wait_for()


def test_profile_page_rejects_invalid_user_id(page: Page):
    page.goto(f"{BASE_URL}/profile?user_id=invalid")

    page.get_by_text("O identificador do usuário é inválido.", exact=True).wait_for()
