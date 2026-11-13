# Consulta perfis, habilidades e organizações no MongoDB para as telas de rede e mentoria.
import re

from bson import ObjectId

_PROFILE_SUMMARY = {
    "nome": 1,
    "headline": 1,
    "localizacao": 1,
    "nivel_carreira": 1,
    "aceita_mentoria": 1,
}

_ORGANIZATION_FIELDS = (
    ("experiencias", "organizacao_id"),
    ("formacao", "instituicao_id"),
    ("certificacoes", "emissor_id"),
)


class ProfessionalRepository:
    """Consulta perfis e habilidades para as telas de rede e mentoria."""

    def __init__(self, database):
        self.users = database["usuarios"]
        self.skills = database["habilidades"]
        self.organizations = database["organizacoes"]

    # Carrega vários perfis em uma consulta, indexando o resultado pelo identificador textual.
    def get_by_ids(self, user_ids):
        ids = {ObjectId(user_id) for user_id in user_ids if ObjectId.is_valid(user_id)}
        if not ids:
            return {}
        return {
            str(doc["_id"]): doc
            for doc in self.users.find({"_id": {"$in": list(ids)}}, _PROFILE_SUMMARY)
        }

    # Busca o perfil e acrescenta os nomes das habilidades e organizações referenciadas.
    def get_by_id(self, user_id):
        if not ObjectId.is_valid(user_id):
            return None
        user = self.users.find_one(
            {"_id": ObjectId(user_id)},
            {
                **_PROFILE_SUMMARY,
                "habilidades": 1,
                "experiencias": 1,
                "formacao": 1,
                "certificacoes": 1,
            },
        )
        if user is None:
            return None

        skills = user.get("habilidades") or []
        skill_ids = [skill.get("habilidade_id") for skill in skills]
        skill_names = {
            doc["_id"]: doc["nome"]
            for doc in self.skills.find({"_id": {"$in": skill_ids}}, {"nome": 1})
        }
        for skill in skills:
            skill["nome"] = skill_names.get(skill.get("habilidade_id"), "Habilidade")

        organization_ids = {
            item[field]
            for section, field in _ORGANIZATION_FIELDS
            for item in user.get(section) or []
            if item.get(field) is not None
        }
        organization_names = {
            doc["_id"]: doc["nome"]
            for doc in self.organizations.find(
                {"_id": {"$in": list(organization_ids)}}, {"nome": 1}
            )
        }
        for section, field in _ORGANIZATION_FIELDS:
            for item in user.get(section) or []:
                item["organizacao"] = organization_names.get(item.get(field), "")
        return user

    # Lista as habilidades por nome para compor os filtros da interface.
    def list_skills(self):
        return list(self.skills.find({}, {"nome": 1}).sort("nome", 1))

    # Busca outros profissionais por nome e habilidade, com ordenação e limite de resultados.
    def search(self, user_id, nome="", habilidade_id=None):
        filters = {"_id": {"$ne": ObjectId(user_id)}}
        if nome:
            filters["nome"] = {"$regex": re.escape(nome), "$options": "i"}
        if habilidade_id is not None:
            filters["habilidades.habilidade_id"] = ObjectId(habilidade_id)
        return list(
            self.users.find(filters, _PROFILE_SUMMARY)
            .sort([("nome", 1), ("_id", 1)])
            .limit(50)
        )
