from unittest.mock import MagicMock

import pytest

from common.errors import NotFoundError
from services.profile.organization_service import OrganizationService


def test_create_maps_organization_fields_and_parses_location(ids):
    repository = MagicMock()
    repository.create.return_value = {
        "_id": ids["organization"],
        "nome": "Tech Solutions",
        "cidade": "João Pessoa",
        "estado": "PB",
    }
    service = OrganizationService(repository)

    created = service.create(
        {
            "nome": "Tech Solutions",
            "tipo": "empresa",
            "setor": "Tecnologia",
            "site": "https://example.com",
            "localizacao": "João Pessoa, PB",
        },
        ids["user"],
    )

    repository.create.assert_called_once_with(
        {
            "nome": "Tech Solutions",
            "nome_normalizado": "tech solutions",
            "tipos": ["empresa"],
            "setor": "Tecnologia",
            "sigla": None,
            "site": "https://example.com",
            "status_verificacao": "pendente",
            "cidade": "João Pessoa",
            "estado": "PB",
            "criado_por_usuario_id": ids["user"],
        }
    )
    assert created["cidade"] == "João Pessoa"


def test_create_uses_explicit_city_and_state_over_location():
    repository = MagicMock()
    repository.create.return_value = {"_id": "new-organization"}
    service = OrganizationService(repository)

    service.create(
        {
            "nome": "Universidade Federal da Paraíba",
            "tipo": "instituicao_ensino",
            "cidade": "João Pessoa",
            "estado": "PB",
            "localizacao": "Outro município, XX",
        }
    )

    payload = repository.create.call_args.args[0]
    assert payload["cidade"] == "João Pessoa"
    assert payload["estado"] == "PB"


def test_get_update_delete_and_pagination_delegate_or_raise_not_found(
    ids,
):
    repository = MagicMock()
    repository.get_by_id.return_value = None
    repository.delete.return_value = False
    repository.get_paginated.return_value = [{"_id": ids["organization"]}]
    service = OrganizationService(repository)

    with pytest.raises(NotFoundError):
        service.get_by_id(ids["organization"])
    with pytest.raises(NotFoundError):
        service.delete(ids["organization"])

    assert service.get_paginated(0, 500, {"estado": "PB"}) == [
        {"_id": ids["organization"]}
    ]
    repository.get_paginated.assert_called_once_with(
        0, 100, {"estado": "PB"}
    )
