from unittest.mock import Mock

from controllers.sessions.session_controller import SessionController


def test_login_passes_validated_login_request_to_service():
    service = Mock()
    service.login.return_value = "session-token"

    response = SessionController(service).login(
        {"email": "ana@example.com", "senha": "secret"}
    )

    assert response.status is True
    assert response.data == "session-token"
    service.login.assert_called_once_with("ana@example.com", "secret")
