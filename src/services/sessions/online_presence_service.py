class OnlinePresenceService:
    def __init__(self, online_presence_repository, inactivity_ttl):
        self.repository = online_presence_repository
        self.inactivity_ttl = inactivity_ttl

    def get_by_user_id(self, session_id, user_id, *, activity=True):
        if not self.update_last_seen(session_id, activity=activity):
            return None
        return self.repository.get_by_user_id(user_id)

    def update_last_seen(self, session_id, *, activity=False):
        return self.repository.update_last_seen(
            session_id, self.inactivity_ttl, activity=activity
        )

    def get_online_users(self, session_id, user_ids, *, activity=False):
        if not self.update_last_seen(session_id, activity=activity):
            return None
        return self.repository.get_online_users(user_ids)
