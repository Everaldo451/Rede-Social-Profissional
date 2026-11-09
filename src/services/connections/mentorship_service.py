class MentorshipService:
    def __init__(self, mentorship_repository, professional_repository):
        self.mentors = mentorship_repository
        self.professionals = professional_repository

    def create(self, data):
        pass

    def get_by_id(self, mentorship_id):
        pass

    def filter_mentors(self, user_id, filters):
        return self._available_profiles(
            self.mentors.filter_mentors(user_id, filters.nome.strip(), filters.habilidade_id)
        )

    def get_by_user_id(self, user_id):
        user = self.professionals.get_by_id(user_id)
        if not user or not user.get("aceita_mentoria"):
            raise ValueError("Perfil de mentor indisponível.")
        return user

    def list_all(self):
        pass

    def update(self, mentorship_id, data):
        pass

    def delete(self, mentorship_id):
        pass

    def _available_profiles(self, rows):
        profiles = self.professionals.get_by_ids(row["id"] for row in rows)
        return [
            {**row, "perfil": profiles[row["id"]]}
            for row in rows
            if profiles.get(row["id"], {}).get("aceita_mentoria")
        ]

    def recommend(self, user_id):
        return self._available_profiles(self.mentors.recommend(user_id))

    def desired_skills(self, user_id):
        return self.mentors.desired_skills(user_id)
