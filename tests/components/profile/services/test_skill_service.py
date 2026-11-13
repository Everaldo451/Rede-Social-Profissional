# Testes de normalização, duplicidade e limites nas operações com habilidades.
from unittest.mock import MagicMock

import pytest

from common.errors import ConflictError, NotFoundError
from services.profile.skill_service import SkillService


# Confere o nome normalizado e os campos enviados ao repositório.
def test_create_normalizes_name_and_maps_portuguese_repository_fields():
    repository = MagicMock()
    repository.get_one.return_value = None
    repository.create.return_value = {
        "_id": "671a2b3c4d5e6f7890124601",
        "nome": "Python",
        "nome_normalizado": "python",
        "categoria": "Linguagem de Programação",
    }
    service = SkillService(repository)

    created = service.create(
        {
            "nome": "Python",
            "categoria": "Linguagem de Programação",
            "descricao": "Web, automação e dados.",
        }
    )

    repository.get_one.assert_called_once_with({"nome_normalizado": "python"})
    repository.create.assert_called_once_with(
        {
            "nome": "Python",
            "nome_normalizado": "python",
            "categoria": "Linguagem de Programação",
            "descricao": "Web, automação e dados.",
        }
    )
    assert created["nome"] == "Python"


# Verifica a rejeição de uma habilidade cujo nome já existe.
def test_create_rejects_duplicate_skill_name():
    repository = MagicMock()
    repository.get_one.return_value = {"_id": "existing-skill"}
    service = SkillService(repository)

    with pytest.raises(ConflictError):
        service.create({"nome": "Python"})
    repository.create.assert_not_called()


# Confere os erros de consulta e remoção de uma habilidade inexistente.
def test_get_by_id_and_delete_raise_not_found_for_missing_skill():
    repository = MagicMock()
    repository.get_by_id.return_value = None
    repository.delete.return_value = False
    service = SkillService(repository)

    with pytest.raises(NotFoundError):
        service.get_by_id("671a2b3c4d5e6f7890124601")
    with pytest.raises(NotFoundError):
        service.delete("671a2b3c4d5e6f7890124601")


# Verifica a normalização após a edição e a aplicação dos limites de página.
def test_update_renormalizes_name_and_clamps_pagination():
    repository = MagicMock()
    repository.get_one.return_value = None
    repository.update.return_value = {
        "_id": "671a2b3c4d5e6f7890124601",
        "nome": "FastAPI",
        "nome_normalizado": "fastapi",
    }
    repository.get_paginated.return_value = [{"nome": "Python"}]
    service = SkillService(repository)

    service.update("671a2b3c4d5e6f7890124601", {"nome": "FastAPI"})
    repository.update.assert_called_once_with(
        "671a2b3c4d5e6f7890124601",
        {"nome": "FastAPI", "nome_normalizado": "fastapi"},
    )

    assert service.get_paginated(0, 1000, {"categoria": "Linguagem"}) == [
        {"nome": "Python"}
    ]
    repository.get_paginated.assert_called_once_with(
        0, 100, {"categoria": "Linguagem"}
    )
