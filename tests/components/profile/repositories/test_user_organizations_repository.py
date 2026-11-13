# Teste integrado dos vínculos do usuário com empresas e instituições de ensino.
from datetime import date
from bson import ObjectId

from repositories.profile.user_organizations_repository import (
    UserOrganizationsRepository,
)


# Prepara o usuário e as organizações referenciadas pelos vínculos do teste.
def _seed_user_and_organizations(resources):
    user_id = ObjectId(resources.ids["user"])
    organization_id = ObjectId(resources.ids["organization"])
    institution_id = ObjectId(resources.ids["institution"])
    resources.insert_document(
        "usuarios",
        {
            "_id": user_id,
            "nome": "Ana Silva",
            "email": f"ana+{user_id}@example.com",
            "senha": "$2b$12$test-hash-value",
            "experiencias": [],
            "formacao": [],
        },
    )
    resources.insert_document(
        "organizacoes",
        {
            "_id": organization_id,
            "nome": "Tech Solutions",
            "nome_normalizado": "tech solutions",
            "tipos": ["empresa"],
            "status_verificacao": "pendente",
        },
    )
    resources.insert_document(
        "organizacoes",
        {
            "_id": institution_id,
            "nome": "Universidade Federal da Paraíba",
            "nome_normalizado": "universidade federal da paraiba",
            "tipos": ["instituicao_ensino"],
            "sigla": "UFPB",
            "status_verificacao": "verificada",
        },
    )
    resources.track_graph_nodes(
        resources.ids["user"],
        resources.ids["organization"],
        resources.ids["institution"],
    )
    return user_id, organization_id, institution_id


# Exercita inclusão e remoção de experiência, formação e vínculo organizacional.
def test_experience_education_and_membership_are_persisted_and_removed(
    repository_resources,
):
    user_id, organization_id, institution_id = _seed_user_and_organizations(
        repository_resources
    )
    repository = UserOrganizationsRepository(
        database=repository_resources.mongo,
        session_factory=repository_resources.neo4j_session_factory,
    )

    experience = repository.add_experience(
        str(user_id),
        {
            "organizacao_nome": "Tech Solutions",
            "cargo": "Desenvolvedora Backend",
            "data_inicio": date(2024, 3, 1),
            "data_fim": None,
            "atual": True,
            "descricao": "Desenvolvimento de APIs REST",
        },
    )
    education = repository.add_education(
        str(user_id),
        {
            "instituicao_id": str(institution_id),
            "curso": "Ciência da Computação",
            "grau": "bacharelado",
            "data_inicio": date(2022, 1, 1),
        },
    )
    assert repository.add_membership(
        str(user_id),
        str(organization_id),
        "colaboradora",
        "ativa",
        date(2026, 1, 1),
    )

    user = repository_resources.mongo["usuarios"].find_one({"_id": user_id})
    assert user["experiencias"][0]["organizacao_id"] == organization_id
    assert user["experiencias"][0]["cargo"] == "Desenvolvedora Backend"
    assert user["formacao"][0]["instituicao_id"] == institution_id
    assert user["formacao"][0]["ano_inicio"] == 2022
    assert experience["organizacao_id"] == str(organization_id)
    assert education["instituicao_id"] == str(institution_id)

    relationships = repository.get_by_user_id(str(user_id))
    assert {item["tipo"] for item in relationships} == {
        "TRABALHOU_EM",
        "ESTUDOU_EM",
        "MEMBRO_DE",
    }
    work = next(item for item in relationships if item["tipo"] == "TRABALHOU_EM")
    assert work["cargo"] == "Desenvolvedora Backend"
    assert work["data_inicio"] == "2024-03-01"
    membership = next(item for item in relationships if item["tipo"] == "MEMBRO_DE")
    assert membership["papel"] == "colaboradora"
    assert membership["status"] == "ativa"

    assert repository.remove_experience(
        str(user_id),
        str(organization_id),
        "Desenvolvedora Backend",
        date(2024, 3, 1),
    )
    assert repository.remove_education(
        str(user_id),
        str(institution_id),
        "Ciência da Computação",
        "bacharelado",
    )
    assert repository.remove_membership(
        str(user_id), str(organization_id), "colaboradora"
    )
    assert repository.get_by_user_id(str(user_id)) == []

    updated_user = repository_resources.mongo["usuarios"].find_one(
        {"_id": user_id}
    )
    assert updated_user["experiencias"] == []
    assert updated_user["formacao"] == []
