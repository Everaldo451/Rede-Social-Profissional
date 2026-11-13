# Testes de persistência, autenticação, índices e consultas de presença de usuários.
from bson import ObjectId
import pytest

from common.errors import ConflictError, InvalidDataError
from repositories.profile.user_repository import UserRepository


# Monta os dados de um usuário com a referência de habilidade recebida.
def _new_user_data(email, skill_id):
    return {
        "nome": "Ana Silva",
        "email": email,
        "senha": "$2b$12$test-hash-value",
        "headline": "Desenvolvedora Backend",
        "localizacao": "João Pessoa, PB",
        "nivel_carreira": "Pleno",
        "aceita_mentoria": True,
        "habilidades": [
            {
                "habilidade_id": skill_id,
                "nivel": "intermediario",
                "anos_experiencia": 2,
            }
        ],
    }


# Confere os campos persistidos e a serialização das referências ObjectId.
def test_create_persists_portuguese_profile_and_serializes_object_ids(
    repository_resources,
):
    email = f"ana+{ObjectId()}@example.com"
    skill_id = repository_resources.ids["skill"]
    repository_resources.track_filter("usuarios", {"email": email})
    repository = UserRepository(repository_resources.mongo)

    created = repository.create(_new_user_data(email, skill_id))
    repository_resources.track_document("usuarios", created["_id"])
    stored = repository_resources.mongo["usuarios"].find_one(
        {"_id": ObjectId(created["_id"])}
    )

    assert stored["nome_normalizado"] == "ana silva"
    assert stored["habilidades"][0]["habilidade_id"] == ObjectId(skill_id)
    assert stored["aceita_mentoria"] is True
    assert stored["experiencias"] == []
    assert stored["formacao"] == []
    assert stored["certificacoes"] == []
    assert stored["criado_em"] == stored["atualizado_em"]
    assert created["_id"] == str(stored["_id"])
    assert created["habilidades"][0]["habilidade_id"] == skill_id
    index = repository_resources.mongo["usuarios"].index_information()
    assert index["email_1"]["unique"] is True


# Verifica a compatibilidade com o índice de e-mail criado pela carga de exemplo.
def test_repository_reuses_seed_created_email_index(repository_resources):
    collection = repository_resources.mongo["usuarios"]
    collection.create_index("email", unique=True)

    UserRepository(repository_resources.mongo)

    assert collection.index_information()["email_1"]["unique"] is True


# Confere a paginação e a contagem dos perfis usados no painel de presença.
def test_presence_profiles_are_paged_and_counted(repository_resources):
    repository = UserRepository(repository_resources.mongo)
    email = f"presence+{ObjectId()}@example.com"
    repository_resources.track_filter("usuarios", {"email": email})
    created = repository.create(
        _new_user_data(email, repository_resources.ids["skill"])
    )
    repository_resources.track_document("usuarios", created["_id"])
    all_profiles = repository.list_presence_profiles(limit=None)
    current_user_id = created["_id"]
    other_profiles = repository.list_presence_profiles(
        current_user_id=current_user_id,
        limit=None,
    )

    assert repository.count_presence_profiles() == len(all_profiles)
    assert repository.list_presence_profiles(offset=0, limit=1) == all_profiles[:1]
    assert repository.list_presence_profiles(offset=1, limit=2) == all_profiles[1:3]
    assert current_user_id not in {profile["user_id"] for profile in other_profiles}
    assert repository.count_presence_profiles(current_user_id) == len(other_profiles)


# Verifica a rejeição de senha em texto simples e o tratamento de e-mail duplicado.
def test_create_rejects_plaintext_password_and_maps_duplicate_email(
    repository_resources,
):
    email = f"ana+{ObjectId()}@example.com"
    repository_resources.track_filter("usuarios", {"email": email})
    repository = UserRepository(repository_resources.mongo)

    with pytest.raises(InvalidDataError):
        repository.create({"email": email, "password": "plaintext"})

    repository.create(
        {
            "nome": "Ana Silva",
            "email": email,
            "senha": "$2b$12$test-hash-value",
        }
    )
    with pytest.raises(ConflictError, match="e-mail"):
        repository.create(
            {
                "nome": "Ana Silva",
                "email": email,
                "senha": "$2b$12$another-test-hash",
            }
        )


# Exercita consulta, atualização e exclusão pelos identificadores persistidos.
def test_lookup_update_and_delete_use_object_id_and_return_real_documents(
    repository_resources,
):
    email = f"ana+{ObjectId()}@example.com"
    repository_resources.track_filter("usuarios", {"email": email})
    repository = UserRepository(repository_resources.mongo)
    created = repository.create(
        _new_user_data(email, repository_resources.ids["skill"])
    )
    repository_resources.track_document("usuarios", created["_id"])

    assert repository.get_by_id(created["_id"])["nome"] == "Ana Silva"
    updated = repository.update(
        created["_id"], {"headline": "Staff Backend Engineer"}
    )
    assert updated["headline"] == "Staff Backend Engineer"
    assert updated["atualizado_em"] is not None
    assert repository.delete(created["_id"]) is True
    assert repository.get_by_id(created["_id"]) is None
    assert repository.get_by_id("not-an-object-id") is None


# Confere a verificação bcrypt e a execução fictícia quando o usuário não existe.
def test_authenticate_verifies_hash_and_uses_dummy_for_unknown_user(
    repository_resources, monkeypatch
):
    email = f"ana+{ObjectId()}@example.com"
    repository_resources.track_filter("usuarios", {"email": email})
    repository = UserRepository(repository_resources.mongo)
    repository.create(
        {
            "nome": "Ana Silva",
            "email": email,
            "senha": "$2b$12$test-hash-value",
        }
    )
    verified = lambda password, password_hash: password == "correct-horse"
    dummy_calls = []
    monkeypatch.setattr(
        "repositories.profile.user_repository.verify_password", verified
    )
    monkeypatch.setattr(
        "repositories.profile.user_repository.verify_dummy",
        lambda password: dummy_calls.append(password),
    )

    assert repository.authenticate(email, "correct-horse")["email"] == email
    assert repository.authenticate(email, "wrong-password") is None
    assert repository.authenticate("missing@example.com", "wrong-password") is None
    assert dummy_calls == ["wrong-password"]
