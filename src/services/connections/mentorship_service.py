from datetime import datetime, timezone

MAX_PAGE_SIZE = 100


class MentorshipService:
    def __init__(
        self, mentorship_repository, professional_repository, notification_repository
    ):
        self.mentors = mentorship_repository
        self.professionals = professional_repository
        self.notifications = notification_repository

    def create(self, mentee_id, data):
        if mentee_id == data["mentor_id"]:
            raise ValueError("Não é possível solicitar mentoria para si mesmo.")
        mentee = self.professionals.get_by_id(mentee_id)
        if mentee is None:
            raise ValueError("O mentorado não está cadastrado.")
        self.get_by_user_id(data["mentor_id"])
        if not self.mentors.mentor_has_skill(
            data["mentor_id"], data["habilidade_id"]
        ):
            raise ValueError("O mentor não possui essa habilidade.")

        mentorship = self.mentors.create(
            {
                "mentor_id": data["mentor_id"],
                "mentorado_id": mentee_id,
                "habilidade_id": data["habilidade_id"],
            }
        )
        self.notifications.create(
            {
                "destinatario_id": data["mentor_id"],
                "tipo": "mentoria",
                "titulo": (
                    "Nova solicitação de mentoria de "
                    f"{mentee.get('nome', 'um profissional')}"
                ),
                "referencia_tipo": "mentoria",
                "referencia_id": mentorship["_id"],
            }
        )
        return mentorship

    def get_by_id(self, mentorship_id):
        return self.mentors.get_by_id(mentorship_id)

    def filter_mentors(self, user_id, filters, offset=0, limit=20):
        offset = max(int(offset or 0), 0)
        limit = min(max(int(limit or 20), 1), MAX_PAGE_SIZE)
        profiles = self._available_profiles(
            self.mentors.filter_mentors(user_id, filters.habilidade_id),
            filters.nome.strip(),
        )
        profiles.sort(
            key=lambda row: (
                row["perfil"].get("nome", "").casefold(),
                row["id"],
            )
        )
        return profiles[offset : offset + limit]

    def get_by_user_id(self, user_id):
        user = self.professionals.get_by_id(user_id)
        if not user or not user.get("aceita_mentoria"):
            raise ValueError("Perfil de mentor indisponível.")
        return user

    def list_all(self):
        pass

    def list_requests(self, user_id):
        requests = self.mentors.list_requests(user_id)
        other_ids = {
            item["mentorado_id"]
            if item["mentor_id"] == user_id
            else item["mentor_id"]
            for item in requests
        }
        profiles = self.professionals.get_by_ids(other_ids)
        skills = {
            str(skill["_id"]): skill["nome"]
            for skill in self.professionals.list_skills()
        }
        for item in requests:
            item["recebida"] = item["mentor_id"] == user_id
            other_id = (
                item["mentorado_id"] if item["recebida"] else item["mentor_id"]
            )
            item["nome"] = profiles.get(other_id, {}).get(
                "nome", "Profissional indisponível"
            )
            item["habilidade_nome"] = skills.get(
                item["habilidade_id"], "Habilidade indisponível"
            )
        return requests

    def update(self, user_id, mentorship_id, data):
        mentorship = self.mentors.get_by_id(mentorship_id)
        if mentorship is None:
            raise ValueError("Solicitação de mentoria não encontrada.")
        if mentorship["mentor_id"] != user_id:
            raise ValueError("Somente o mentor pode responder à solicitação.")
        if mentorship["status"] != "solicitado":
            raise ValueError("A solicitação de mentoria não está pendente.")

        now = datetime.now(timezone.utc)
        if data.acao == "aceitar":
            updates = {"status": "ativa", "iniciada_em": now, "encerrada_em": None}
            title = "Sua solicitação de mentoria foi aceita"
        else:
            updates = {"status": "cancelada", "iniciada_em": None, "encerrada_em": now}
            title = "Sua solicitação de mentoria foi recusada"
        updated = self.mentors.update(mentorship_id, updates)
        if updated is None:
            raise ValueError("A solicitação de mentoria já foi respondida.")
        self.notifications.create(
            {
                "destinatario_id": mentorship["mentorado_id"],
                "tipo": "mentoria",
                "titulo": title,
                "referencia_tipo": "mentoria",
                "referencia_id": mentorship_id,
            }
        )
        return updated

    def delete(self, mentorship_id):
        pass

    def _available_profiles(self, rows, name=""):
        profiles = self.professionals.get_by_ids(row["id"] for row in rows)
        name = name.casefold()
        skill_names = {
            str(skill["_id"]): skill["nome"]
            for skill in self.professionals.list_skills()
        }
        available = []
        for row in rows:
            profile = profiles.get(row["id"])
            if not profile or not profile.get("aceita_mentoria"):
                continue
            if name and name not in profile.get("nome", "").casefold():
                continue
            skill_ids = sorted(
                set(row.get("habilidade_ids", [])),
                key=lambda skill_id: skill_names.get(skill_id, "").casefold(),
            )
            available.append(
                {
                    **row,
                    "habilidade_ids": skill_ids,
                    "habilidades": [
                        skill_names[skill_id]
                        for skill_id in skill_ids
                        if skill_id in skill_names
                    ],
                    "perfil": profile,
                }
            )
        return available

    def recommend(self, user_id, offset=0, limit=20):
        offset = max(int(offset or 0), 0)
        limit = min(max(int(limit or 20), 1), MAX_PAGE_SIZE)
        profiles = self._available_profiles(self.mentors.recommend(user_id))
        return profiles[offset : offset + limit]

    def desired_skills(self, user_id):
        desired_ids = set(self.mentors.desired_skills(user_id))
        return [
            skill["nome"]
            for skill in self.professionals.list_skills()
            if str(skill["_id"]) in desired_ids
        ]
