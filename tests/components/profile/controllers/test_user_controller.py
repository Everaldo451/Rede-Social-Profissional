# Testes dos DTOs de usuário e da comunicação entre controller e serviço de perfil.
from unittest.mock import MagicMock

from common.errors import NotFoundError
from controllers.profile.user_controller import UserController


# Confere a normalização dos dados de cadastro antes da chamada ao serviço.
def test_create_validates_and_normalizes_request_before_calling_service(
    user_record,
):
    service = MagicMock()
    service.create.return_value = user_record
    controller = UserController(service)

    response = controller.create(
        {
            "nome": "  Ana   Silva ",
            "email": " ANA@EXAMPLE.COM ",
            "senha": "safe-password-123",
        }
    )

    assert response.status is True
    assert response.data == user_record
    assert response.message == "Conta criada com sucesso!"
    service.create.assert_called_once_with(
        {
            "nome": "Ana Silva",
            "email": "ana@example.com",
            "senha": "safe-password-123",
        }
    )


# Verifica se a entrada inválida gera erro sem executar o serviço.
def test_invalid_user_request_returns_error_response_without_service_call():
    service = MagicMock()
    controller = UserController(service)

    response = controller.create(
        {
            "nome": "Ana Silva",
            "email": "not-an-email",
            "senha": "safe-password-123",
        }
    )

    assert response.status is False
    assert response.message
    service.create.assert_not_called()


# Confere o repasse dos detalhes da habilidade validados pelo DTO.
def test_add_skill_uses_dto_fields_and_calls_user_service(ids):
    service = MagicMock()
    service.add_skill.return_value = {
        "usuario_id": ids["user"],
        "habilidade_id": ids["skill"],
        "tipo": "has",
        "nivel": "intermediario",
        "experiencia_anos": 2,
        "modalidade": None,
        "disponibilidade": None,
    }
    controller = UserController(service)

    response = controller.add_skill(
        ids["user"],
        ids["skill"],
        "has",
        nivel="intermediario",
        experiencia_anos="2",
    )

    assert response.status is True
    service.add_skill.assert_called_once_with(
        ids["user"],
        ids["skill"],
        "has",
        "intermediario",
        2,
        None,
        None,
    )


# Verifica as respostas para erros de negócio e falhas inesperadas.
def test_service_domain_and_unexpected_errors_return_failure_response(
    caplog,
):
    service = MagicMock()
    service.delete.side_effect = NotFoundError("Usuário não encontrado.")
    controller = UserController(service)

    domain_error = controller.delete("671a2b3c4d5e6f7890123456")
    assert domain_error.status is False
    assert domain_error.message == "Usuário não encontrado."

    service.list_all.side_effect = RuntimeError("database unavailable")
    unexpected_error = controller.list_all()
    assert unexpected_error.status is False
    assert unexpected_error.message == "Ocorreu um erro interno."
    assert "Falha inesperada ao executar uma operação de usuário." in caplog.text
