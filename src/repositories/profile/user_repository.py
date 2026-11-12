import bcrypt

from database import get_mongo_database


class UserRepository:
    def create(self, data):
        pass

    def get_by_id(self, user_id):
        pass

    def authenticate(self, email, password):
        user = get_mongo_database().usuarios.find_one({"email": email}, {"senha": 1})
        stored_hash = user.get("senha") if user else None
        if not isinstance(stored_hash, str):
            return None

        try:
            if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
                return str(user["_id"])
        except ValueError:
            return None
        return None

    def list_all(self):
        pass

    def list_presence_profiles(self, current_user_id):
        users = get_mongo_database().usuarios.find({}, {"nome": 1}).sort("nome", 1)
        return [
            {"user_id": str(user["_id"]), "name": user.get("nome") or str(user["_id"])}
            for user in users
            if str(user["_id"]) != current_user_id
        ]

    def update(self, user_id, data):
        pass

    def delete(self, user_id):
        pass
