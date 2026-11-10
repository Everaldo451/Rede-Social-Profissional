class UserService:
    def __init__(self, user_repository):
        self.repository = user_repository

    def create(self, data):
        pass

    def get_by_id(self, user_id):
        pass

    def authenticate(self, email, password):
        return self.repository.authenticate(email, password)

    def list_all(self):
        pass

    def list_presence_profiles(self, current_user_id):
        return self.repository.list_presence_profiles(current_user_id)

    def update(self, user_id, data):
        pass

    def delete(self, user_id):
        pass
