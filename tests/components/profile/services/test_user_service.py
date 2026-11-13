from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from common.errors import (
    ConflictError,
    ForbiddenError,
    InvalidDataError,
    NotFoundError,
    UnauthorizedError,
)
from services.profile.user_service import UserService


def _service():
    user_repository = MagicMock()
    user_skill_repository = MagicMock()
    user_organization_repository = MagicMock()
    service = UserService(
        user_repository,
        user_skill_repository,
        user_organization_repository,
    )
    return (
        service,
        user_repository,
        user_skill_repository,
        user_organization_repository,
    )


def test_create_hashes_password_maps_fields_and_returns_realistic_user(
    user_record, monkeypatch
):
    service, users, _, _ = _service()
    users.get_by_email.return_value = None
    users.create.return_value = user_record
    monkeypatch.setattr(
        "services.profile.user_service.hash_password",
        lambda password: "$2b$12$hashed-password-for-ana",
    )

    created = service.create(
        {
            "nome": "Ana Silva",
            "email": "ana@example.com",
            "senha": "safe-password-123",
        }
    )

    payload = users.create.call_args.args[0]
    assert payload["nome"] == "Ana Silva"
    assert payload["nome_normalizado"] == "ana silva"
    assert payload["email"] == "ana@example.com"
    assert payload["senha"] == "$2b$12$hashed-password-for-ana"
    assert payload["senha"] != "safe-password-123"
    assert created["usuario_id"] == user_record["_id"]
    assert created["nome"] == "Ana Silva"
    assert created["email"] == "ana@example.com"


def test_create_rejects_duplicate_email_before_repository_insert():
    service, users, _, _ = _service()
    users.get_by_email.return_value = {"_id": "existing-user"}

    with pytest.raises(ConflictError):
        service.create(
            {
                "nome": "Ana Silva",
                "email": "ana@example.com",
                "senha": "safe-password-123",
            }
        )
    users.create.assert_not_called()


def test_authenticate_normalizes_email_and_returns_private_profile(user_record):
    service, users, _, _ = _service()
    users.authenticate.return_value = user_record

    result = service.authenticate(" ANA@EXAMPLE.COM ", "safe-password-123")

    users.authenticate.assert_called_once_with(
        "ana@example.com", "safe-password-123"
    )
    assert result["email"] == "ana@example.com"


def test_authenticate_and_profile_access_raise_typed_errors():
    service, users, _, _ = _service()

    with pytest.raises(UnauthorizedError):
        service.authenticate("", "password")
    users.authenticate.return_value = None
    with pytest.raises(UnauthorizedError):
        service.authenticate("ana@example.com", "wrong-password")

    with pytest.raises(ForbiddenError):
        service.get_by_id("671a2b3c4d5e6f7890123456")
    users.get_by_id.assert_not_called()


def test_get_by_id_includes_relations_and_hides_email_from_other_viewers(
    user_record, ids
):
    service, users, skills, organizations = _service()
    users.get_by_id.return_value = deepcopy(user_record)
    skills.get_skills.return_value = [
        {
            "usuario_id": ids["user"],
            "habilidade_id": ids["skill"],
            "tipo": "has",
            "nivel": "intermediario",
            "experiencia_anos": 2,
        }
    ]
    organizations.get_by_user_id.return_value = [
        {
            "tipo": "TRABALHOU_EM",
            "organizacao_id": ids["organization"],
            "cargo": "Desenvolvedora Backend",
        }
    ]

    result = service.get_by_id(ids["user"], "671a2b3c4d5e6f7890123400")

    assert "email" not in result
    assert result["relacionamentos_habilidades"][0]["nivel"] == "intermediario"
    assert result["relacionamentos_organizacoes"][0]["tipo"] == "TRABALHOU_EM"
    skills.get_skills.assert_called_once_with({"usuario_id": ids["user"]})
    organizations.get_by_user_id.assert_called_once_with(ids["user"])


def test_add_skill_validates_teaching_fields_and_delegates_to_repository(ids):
    service, _, skills, _ = _service()
    skills.add_skill.return_value = True

    result = service.add_skill(
        ids["user"],
        ids["skill"],
        "teaches",
        nivel="avancado",
        experiencia_anos=4,
        modalidade="online",
        disponibilidade="noite",
    )

    skills.add_skill.assert_called_once_with(
        ids["user"],
        ids["skill"],
        "teaches",
        nivel="avancado",
        experiencia_anos=4,
        modalidade="online",
        disponibilidade="noite",
    )
    assert result["tipo"] == "teaches"
    assert result["experiencia_anos"] == 4

    with pytest.raises(InvalidDataError):
        service.add_skill(
            ids["user"], ids["skill"], "teaches", nivel="avancado"
        )


def test_add_experience_and_education_map_input_to_organization_repository(
    ids,
):
    service, _, _, organizations = _service()
    organizations.add_experience.return_value = {
        "cargo": "Desenvolvedora Backend"
    }
    organizations.add_education.return_value = {
        "curso": "Ciência da Computação"
    }

    service.add_experience(
        ids["user"],
        {
            "organizacao_id": ids["organization"],
            "cargo": "Desenvolvedora Backend",
            "data_inicio": "2024-03-01",
            "descricao": "Desenvolvimento de APIs REST",
        },
    )
    organizations.add_experience.assert_called_once_with(
        ids["user"],
        {
            "organizacao_id": ids["organization"],
            "organizacao_nome": None,
            "cargo": "Desenvolvedora Backend",
            "data_inicio": "2024-03-01",
            "data_fim": None,
            "atual": True,
            "descricao": "Desenvolvimento de APIs REST",
        },
    )

    service.add_education(
        ids["user"],
        {
            "instituicao_nome": "Universidade Federal da Paraíba",
            "instituicao_id": ids["institution"],
            "curso": "Ciência da Computação",
            "grau": "bacharelado",
            "data_inicio": "2022-01-01",
        },
    )
    organizations.add_education.assert_called_once_with(
        ids["user"],
        {
            "instituicao_id": ids["institution"],
            "instituicao_nome": "Universidade Federal da Paraíba",
            "curso": "Ciência da Computação",
            "grau": "bacharelado",
            "data_inicio": "2022-01-01",
            "data_fim": None,
        },
    )


def test_delete_removes_graph_relations_before_deleting_user(ids):
    service, users, _, organizations = _service()
    users.get_by_id.return_value = {"_id": ids["user"]}
    users.delete.return_value = True

    assert service.delete(ids["user"]) is True

    organizations.delete_by_user_id.assert_called_once_with(ids["user"])
    users.delete.assert_called_once_with(ids["user"])
    assert organizations.delete_by_user_id.call_count == 1


def test_update_missing_user_raises_not_found(ids):
    service, users, _, _ = _service()
    users.update.return_value = None

    with pytest.raises(NotFoundError):
        service.update(ids["user"], {"headline": "Staff Engineer"})
