# Testes da validação e das respostas do controller de habilidades.
from unittest.mock import MagicMock

from controllers.profile.skill_controller import SkillController


# Confere os campos validados e a propagação do resultado do serviço.
def test_create_validates_skill_fields_and_returns_service_result(skill_record):
    service = MagicMock()
    service.create.return_value = skill_record
    controller = SkillController(service)

    response = controller.create(
        {
            "nome": " Python ",
            "categoria": " Linguagem de Programação ",
            "descricao": " Web, automação e dados. ",
        }
    )

    assert response.status is True
    assert response.data == skill_record
    service.create.assert_called_once_with(
        {
            "nome": "Python",
            "categoria": "Linguagem de Programação",
            "descricao": "Web, automação e dados.",
        }
    )


# Verifica se um identificador inválido é recusado antes da consulta.
def test_invalid_skill_id_is_rejected_before_service_call():
    service = MagicMock()
    controller = SkillController(service)

    response = controller.delete("not-a-mongo-id")

    assert response.status is False
    assert response.message
    service.delete.assert_not_called()


# Confere o registro da falha e a mensagem genérica devolvida à interface.
def test_unexpected_service_failure_is_logged_and_returns_generic_error(
    caplog,
):
    service = MagicMock()
    service.get_by_id.side_effect = RuntimeError("mongo unavailable")
    controller = SkillController(service)

    response = controller.get_by_id("671a2b3c4d5e6f7890124601")

    assert response.status is False
    assert response.message == "Ocorreu um erro interno."
    assert "Falha inesperada ao executar uma operação de habilidade." in caplog.text
