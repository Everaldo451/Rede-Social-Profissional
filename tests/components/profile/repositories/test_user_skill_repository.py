# Testes da consistência dos vínculos de habilidade entre MongoDB e Neo4j.
from bson import ObjectId
import pytest

from common.errors import InvalidDataError
from repositories.profile.user_skill_repository import UserSkillRepository


# Cria os registros de usuário e habilidade necessários ao cenário.
def _seed_user_and_skill(resources):
    user_id = ObjectId(resources.ids["user"])
    skill_id = ObjectId(resources.ids["skill"])
    resources.insert_document(
        "usuarios",
        {
            "_id": user_id,
            "nome": "Ana Silva",
            "email": f"ana+{user_id}@example.com",
            "senha": "$2b$12$test-hash-value",
            "habilidades": [],
        },
    )
    resources.insert_document(
        "habilidades",
        {
            "_id": skill_id,
            "nome": "Python",
            "nome_normalizado": "python",
            "categoria": "Linguagem de Programação",
        },
    )
    resources.track_graph_nodes(resources.ids["user"], resources.ids["skill"])
    return user_id, skill_id


# Confere a habilidade possuída no documento do usuário e no grafo.
def test_add_has_updates_embedded_skill_and_creates_graph_relation(
    repository_resources,
):
    user_id, skill_id = _seed_user_and_skill(repository_resources)
    repository = UserSkillRepository(
        session_factory=repository_resources.neo4j_session_factory,
        database=repository_resources.mongo,
    )

    assert repository.add_skill(
        str(user_id),
        str(skill_id),
        "has",
        nivel="intermediario",
        experiencia_anos=2,
    )

    user = repository_resources.mongo["usuarios"].find_one({"_id": user_id})
    assert user["habilidades"] == [
        {
            "habilidade_id": skill_id,
            "nivel": "intermediario",
            "anos_experiencia": 2,
        }
    ]
    relations = repository.get_skills(
        {"usuario_id": str(user_id), "tipo": "has"}
    )
    assert len(relations) == 1
    assert relations[0]["habilidade_id"] == str(skill_id)
    assert relations[0]["nivel"] == "intermediario"

    assert repository.add_skill(
        str(user_id),
        str(skill_id),
        "has",
        nivel="avancado",
        experiencia_anos=4,
    )
    updated_user = repository_resources.mongo["usuarios"].find_one(
        {"_id": user_id}
    )
    assert len(updated_user["habilidades"]) == 1
    assert updated_user["habilidades"][0]["nivel"] == "avancado"
    assert updated_user["habilidades"][0]["anos_experiencia"] == 4


# Verifica as propriedades dos vínculos de aprendizagem e ensino.
def test_add_wants_and_teaches_persists_relationship_properties(
    repository_resources,
):
    user_id, skill_id = _seed_user_and_skill(repository_resources)
    repository = UserSkillRepository(
        session_factory=repository_resources.neo4j_session_factory,
        database=repository_resources.mongo,
    )

    assert repository.add_skill(
        str(user_id), str(skill_id), "wants", nivel="intermediario"
    )
    assert repository.add_skill(
        str(user_id),
        str(skill_id),
        "teaches",
        nivel="avancado",
        experiencia_anos=4,
        modalidade="online",
        disponibilidade="noite",
    )

    relations = repository.get_skills({"usuario_id": str(user_id)})
    by_type = {relation["tipo"]: relation for relation in relations}
    assert set(by_type) == {"wants", "teaches"}
    assert by_type["teaches"]["experiencia_anos"] == 4
    assert by_type["teaches"]["modalidade"] == "online"
    assert by_type["teaches"]["disponibilidade"] == "noite"
    assert by_type["wants"]["nivel"] == "intermediario"


# Confere a remoção do vínculo no grafo e da habilidade embutida no perfil.
def test_remove_has_deletes_graph_edge_and_mongo_skill_entry(
    repository_resources,
):
    user_id, skill_id = _seed_user_and_skill(repository_resources)
    repository = UserSkillRepository(
        session_factory=repository_resources.neo4j_session_factory,
        database=repository_resources.mongo,
    )
    repository.add_skill(
        str(user_id),
        str(skill_id),
        "has",
        nivel="intermediario",
        experiencia_anos=2,
    )

    assert repository.remove_skill(str(user_id), str(skill_id), "has") is True
    assert repository.get_skills(
        {"usuario_id": str(user_id), "tipo": "has"}
    ) == []
    user = repository_resources.mongo["usuarios"].find_one({"_id": user_id})
    assert user["habilidades"] == []


# Verifica a rejeição de tipos de relação e filtros não aceitos.
def test_invalid_type_and_unknown_filters_are_rejected(repository_resources):
    repository = UserSkillRepository(
        session_factory=repository_resources.neo4j_session_factory,
        database=repository_resources.mongo,
    )

    with pytest.raises(InvalidDataError):
        repository.add_skill(
            repository_resources.ids["user"],
            repository_resources.ids["skill"],
            "invalid",
        )
    with pytest.raises(InvalidDataError):
        repository.get_skills({"unexpected": "value"})
