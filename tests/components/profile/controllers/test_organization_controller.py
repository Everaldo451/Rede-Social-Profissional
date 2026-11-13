from unittest.mock import MagicMock

from controllers.profile.organization_controller import OrganizationController


def test_create_validates_payload_and_creator_id(
    organization_record, ids
):
    service = MagicMock()
    service.create.return_value = organization_record
    controller = OrganizationController(service)

    response = controller.create(
        {
            "nome": " Tech Solutions ",
            "tipo": "empresa",
            "setor": "Tecnologia",
            "site": "https://example.com",
            "localizacao": "João Pessoa, PB",
        },
        criado_por_usuario_id=ids["user"],
    )

    assert response.status is True
    assert response.data == organization_record
    service.create.assert_called_once_with(
        {
            "nome": "Tech Solutions",
            "tipo": "empresa",
            "setor": "Tecnologia",
            "site": "https://example.com",
            "localizacao": "João Pessoa, PB",
        },
        ids["user"],
    )


def test_invalid_creator_id_does_not_call_service(organization_record):
    service = MagicMock()
    service.create.return_value = organization_record
    controller = OrganizationController(service)

    response = controller.create(
        {"nome": "Tech Solutions", "tipo": "empresa"},
        criado_por_usuario_id="bad-id",
    )

    assert response.status is False
    assert response.message
    service.create.assert_not_called()


def test_unexpected_service_failure_returns_error_response(caplog):
    service = MagicMock()
    service.delete.side_effect = RuntimeError("mongo unavailable")
    controller = OrganizationController(service)

    response = controller.delete("671a2b3c4d5e6f7890124201")

    assert response.status is False
    assert response.message == "Ocorreu um erro interno."
    assert (
        "Falha inesperada ao executar uma operação de organização."
        in caplog.text
    )
