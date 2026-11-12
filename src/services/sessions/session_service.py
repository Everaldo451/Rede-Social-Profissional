from secrets import token_urlsafe


class SessionService:
    def __init__(self, session_repository, user_service, online_presence_service):
        self.sessions = session_repository
        self.users = user_service
        self.presence = online_presence_service

    def login(self, email, password):
        user_id = self.users.authenticate(email, password)
        if user_id is None:
            return None
        session_id = token_urlsafe(32)
        self.sessions.create(session_id, user_id)
        self.presence.update_last_seen(session_id, activity=True)
        return session_id

    def get_current_user(self, session_id):
        return self.sessions.get_by_id(session_id)

    def get_all_sessions_for_current_user(self, session_id):
        return self.sessions.get_all_session_for_user(session_id)

    def revoke_other_session(self, session_id, reference):
        return self.sessions.revoke_other(session_id, reference)

    def logout(self, session_id):
        return self.sessions.delete(session_id)
