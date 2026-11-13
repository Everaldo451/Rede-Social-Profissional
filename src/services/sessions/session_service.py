# Coordena autenticação, criação de tokens, consulta de sessões e encerramento de acessos.
from secrets import token_urlsafe


class SessionService:
    def __init__(self, session_repository, user_service, online_presence_service):
        self.sessions = session_repository
        self.users = user_service
        self.presence = online_presence_service

    # Autentica o usuário, gera um token aleatório e registra a sessão e a presença.
    def login(self, email, password):
        user_id = self.users.authenticate(email, password)
        if user_id is None:
            return None
        # O token é gerado com uma fonte de aleatoriedade apropriada para identificadores de autenticação.
        session_id = token_urlsafe(32)
        self.sessions.create(session_id, user_id)
        self.presence.update_last_seen(session_id, activity=True)
        return session_id

    # Obtém o usuário associado ao token de sessão.
    def get_current_user(self, session_id):
        return self.sessions.get_by_id(session_id)

    # Consulta as sessões pertencentes ao usuário do token apresentado.
    def get_all_sessions_for_current_user(self, session_id):
        return self.sessions.get_all_session_for_user(session_id)

    # Solicita a revogação de outra sessão pela sua referência.
    def revoke_other_session(self, session_id, reference):
        return self.sessions.revoke_other(session_id, reference)

    # Solicita a remoção da sessão atual.
    def logout(self, session_id):
        return self.sessions.delete(session_id)
