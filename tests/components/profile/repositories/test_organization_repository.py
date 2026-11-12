from bson import ObjectId

from repositories.profile.organization_repository import OrganizationRepository


def _create_test_organization(repository, resources):
    unique = str(ObjectId())
    name = f"Tech Solutions {unique}"
    resources.track_filter(
        "organizacoes", {"nome_normalizado": name.casefold()}
    )
    organization = repository.create(
        {
            "nome": name,
            "tipos": "empresa",
            "setor": "Tecnologia",
            "site": "https://example.com",
            "cidade": "João Pessoa",
            "estado": "PB",
            "status_verificacao": "pendente",
            "criado_por_usuario_id": resources.ids["user"],
        }
    )
    resources.track_document("organizacoes", organization["_id"])
    return organization


def test_create_normalizes_and_converts_creator_reference(repository_resources):
    repository = OrganizationRepository(repository_resources.mongo)
    organization = _create_test_organization(repository, repository_resources)
    stored = repository_resources.mongo["organizacoes"].find_one(
        {"_id": ObjectId(organization["_id"])}
    )

    assert stored["nome_normalizado"] == organization["nome"].casefold()
    assert stored["tipos"] == ["empresa"]
    assert stored["criado_por_usuario_id"] == ObjectId(
        repository_resources.ids["user"]
    )
    assert organization["_id"] == str(stored["_id"])
    assert stored["criado_em"]


def test_get_paginated_and_update_use_real_documents(repository_resources):
    repository = OrganizationRepository(repository_resources.mongo)
    organization = _create_test_organization(repository, repository_resources)

    result = repository.get_paginated(
        0, 10, {"nome_normalizado": organization["nome_normalizado"]}
    )
    assert [item["_id"] for item in result] == [organization["_id"]]

    updated = repository.update(organization["_id"], {"nome": "Tech JP"})
    assert updated["nome"] == "Tech JP"
    assert updated["nome_normalizado"] == "tech jp"


def test_delete_and_invalid_id_affect_only_target_organization(repository_resources):
    repository = OrganizationRepository(repository_resources.mongo)
    organization = _create_test_organization(repository, repository_resources)

    assert repository.get_by_id("bad-id") is None
    assert repository.delete("bad-id") is False
    assert repository.delete(organization["_id"]) is True
    assert repository.get_by_id(organization["_id"]) is None
