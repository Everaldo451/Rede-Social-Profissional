from services.shared.errors import NotFound, ValidationFailed


class UserSkillService:
    TYPES = {"skill", "interest"}

    def __init__(self, repo, skill_repository, user_repository):
        self._repo = repo
        self._skills = skill_repository
        self._users = user_repository

    def add_skill(self, user_id, skill_id, skill_type):
        if skill_type not in self.TYPES:
            raise ValidationFailed("Tipo deve ser 'skill' ou 'interest'.")
        if not self._users.get_by_id(user_id):
            raise NotFound("Usuário não encontrado.")
        if not self._skills.get_by_id(skill_id):
            raise NotFound("Habilidade não encontrada.")
        return self._repo.add_skill(user_id, skill_id, skill_type)

    def remove_skill(self, user_id, skill_id, skill_type):
        return self._repo.remove_skill(user_id, skill_id, skill_type)

    def get_skills(self, filters=None):
        return self._repo.get_skills(filters)
