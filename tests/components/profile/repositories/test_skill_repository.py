from bson import ObjectId

from repositories.profile.skill_repository import SkillRepository


def _create_test_skill(repository, resources):
    unique = str(ObjectId())
    name = f"Python {unique}"
    normalized_name = name.casefold()
    resources.track_filter(
        "habilidades", {"nome_normalizado": normalized_name}
    )
    skill = repository.create(
        {
            "nome": name,
            "categoria": f"Teste de integração {unique}",
            "descricao": "Automação, web e ciência de dados.",
        }
    )
    resources.track_document("habilidades", skill["_id"])
    return skill


def test_create_normalizes_skill_and_persists_dates(repository_resources):
    repository = SkillRepository(repository_resources.mongo)
    skill = _create_test_skill(repository, repository_resources)
    stored = repository_resources.mongo["habilidades"].find_one(
        {"_id": ObjectId(skill["_id"])}
    )

    assert stored["nome"] == skill["nome"]
    assert stored["nome_normalizado"] == skill["nome"].casefold()
    assert stored["categoria"].startswith("Teste de integração ")
    assert stored["criado_em"] == stored["atualizado_em"]
    assert skill["_id"] == str(stored["_id"])


def test_get_paginated_returns_only_matching_real_skill(repository_resources):
    repository = SkillRepository(repository_resources.mongo)
    skill = _create_test_skill(repository, repository_resources)

    result = repository.get_paginated(
        0, 5, {"categoria": skill["categoria"]}
    )

    assert [item["_id"] for item in result] == [skill["_id"]]


def test_update_delete_and_invalid_id_use_real_collection(repository_resources):
    repository = SkillRepository(repository_resources.mongo)
    skill = _create_test_skill(repository, repository_resources)

    updated = repository.update(skill["_id"], {"nome": "FastAPI"})
    assert updated["nome"] == "FastAPI"
    assert updated["nome_normalizado"] == "fastapi"
    assert updated["atualizado_em"] is not None
    assert repository.delete(skill["_id"]) is True
    assert repository.get_by_id(skill["_id"]) is None
    assert repository.get_by_id("not-an-object-id") is None
