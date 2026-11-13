from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from bson import ObjectId

from src.services.connections.connection_service import ConnectionService
from src.services.connections.mentorship_service import MentorshipService


class FakeProfessionals:
    def __init__(self, profiles):
        self.profiles = profiles

    def get_by_ids(self, user_ids):
        return {
            user_id: self.profiles[user_id]
            for user_id in user_ids
            if user_id in self.profiles
        }

    def get_by_id(self, user_id):
        return self.profiles.get(user_id)

    def list_skills(self):
        return []


def test_connection_request_notifies_the_recipient():
    sender_id, recipient_id = str(ObjectId()), str(ObjectId())
    connections = Mock()
    connections.request_connection.return_value = "request-uuid"
    notifications = Mock()
    service = ConnectionService(
        connections,
        FakeProfessionals(
            {sender_id: {"nome": "Ana"}, recipient_id: {"nome": "Bruno"}}
        ),
        notifications,
    )

    result = service.request_connection(sender_id, recipient_id)

    assert result == "request-uuid"
    notifications.create.assert_called_once_with(
        {
            "destinatario_id": recipient_id,
            "tipo": "nova_conexao",
            "titulo": "Solicitação de conexão de Ana",
            "referencia_tipo": "usuario",
            "referencia_id": sender_id,
        }
    )


def test_accepting_connection_notifies_only_after_a_new_transition():
    accepter_id, requester_id = str(ObjectId()), str(ObjectId())
    connections = Mock()
    connections.update_connection_request.return_value = True
    notifications = Mock()
    service = ConnectionService(
        connections,
        FakeProfessionals({accepter_id: {"nome": "Bruno"}}),
        notifications,
    )

    result = service.update_connection_request(
        accepter_id,
        requester_id,
        SimpleNamespace(acao="aceitar", solicitacao_id="request-uuid"),
    )

    assert result == "aceita"
    notifications.create.assert_called_once_with(
        {
            "destinatario_id": requester_id,
            "tipo": "conexao_aceita",
            "titulo": "Bruno aceitou sua solicitação de conexão",
            "referencia_tipo": "usuario",
            "referencia_id": accepter_id,
        }
    )

    connections.update_connection_request.return_value = False
    service.update_connection_request(
        accepter_id,
        requester_id,
        SimpleNamespace(acao="aceitar", solicitacao_id="request-uuid"),
    )
    notifications.create.assert_called_once()


def _mentorship_service():
    mentee_id, mentor_id, skill_id = (str(ObjectId()) for _ in range(3))
    mentorship_id = str(ObjectId())
    request = {
        "_id": mentorship_id,
        "mentor_id": mentor_id,
        "mentorado_id": mentee_id,
        "habilidade_id": skill_id,
        "status": "solicitado",
    }
    mentors = Mock()
    mentors.mentor_has_skill.return_value = True
    mentors.create.return_value = request
    mentors.get_by_id.return_value = request
    mentors.update.return_value = {**request, "status": "ativa"}
    professionals = FakeProfessionals(
        {
            mentee_id: {"nome": "Ana"},
            mentor_id: {"nome": "Bruno", "aceita_mentoria": True},
        }
    )
    notifications = Mock()
    return (
        MentorshipService(mentors, professionals, notifications),
        mentors,
        notifications,
        mentee_id,
        mentor_id,
        skill_id,
        mentorship_id,
    )


def test_mentorship_request_notifies_the_mentor_with_the_request_id():
    service, mentors, notifications, mentee_id, mentor_id, skill_id, mentorship_id = (
        _mentorship_service()
    )

    result = service.create(
        mentee_id, {"mentor_id": mentor_id, "habilidade_id": skill_id}
    )

    assert result["_id"] == mentorship_id
    mentors.create.assert_called_once_with(
        {
            "mentor_id": mentor_id,
            "mentorado_id": mentee_id,
            "habilidade_id": skill_id,
        }
    )
    notifications.create.assert_called_once_with(
        {
            "destinatario_id": mentor_id,
            "tipo": "mentoria",
            "titulo": "Nova solicitação de mentoria de Ana",
            "referencia_tipo": "mentoria",
            "referencia_id": mentorship_id,
        }
    )


def test_only_the_mentor_can_accept_a_pending_mentorship():
    service, mentors, notifications, mentee_id, mentor_id, _, mentorship_id = (
        _mentorship_service()
    )

    with pytest.raises(ValueError, match="Somente o mentor"):
        service.update(
            mentee_id,
            mentorship_id,
            SimpleNamespace(acao="aceitar"),
        )
    mentors.update.assert_not_called()
    notifications.create.assert_not_called()

    result = service.update(
        mentor_id,
        mentorship_id,
        SimpleNamespace(acao="aceitar"),
    )

    assert result["status"] == "ativa"
    mentors.update.assert_called_once()
    notification = notifications.create.call_args.args[0]
    assert notification["destinatario_id"] == mentee_id
    assert notification["titulo"] == "Sua solicitação de mentoria foi aceita"
    assert notification["referencia_id"] == mentorship_id


def test_mentor_search_paginates_with_bounded_offsets():
    (
        service,
        mentors,
        _,
        mentee_id,
        mentor_id,
        skill_id,
        _,
    ) = _mentorship_service()
    mentors.filter_mentors.return_value = [
        {"id": mentor_id, "habilidade_ids": [skill_id]},
    ]

    result = service.filter_mentors(
        mentee_id,
        SimpleNamespace(nome=" Bruno ", habilidade_id=skill_id),
        offset=-4,
        limit=500,
    )

    mentors.filter_mentors.assert_called_once_with(mentee_id, skill_id)
    assert result[0]["perfil"]["nome"] == "Bruno"
    assert result[0]["habilidade_ids"] == [skill_id]


def test_mentor_search_filters_by_profile_name_and_mentorship_availability():
    service, mentors, _, mentee_id, mentor_id, skill_id, _ = _mentorship_service()
    mentors.filter_mentors.return_value = [
        {"id": mentor_id, "habilidade_ids": [skill_id]},
    ]

    result = service.filter_mentors(
        mentee_id,
        SimpleNamespace(nome="Ana", habilidade_id=skill_id),
    )

    mentors.filter_mentors.assert_called_once_with(mentee_id, skill_id)
    assert result == []
