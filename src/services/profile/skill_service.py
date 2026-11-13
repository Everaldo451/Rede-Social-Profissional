# Regras de habilidades, incluindo normalização do nome e prevenção de cadastros duplicados.
from common.errors import ConflictError, NotFoundError
from common.validation import normalize_key

MAX_PAGE_SIZE = 100


class SkillService:
    def __init__(self, skill_repository):
        self.skill_repository = skill_repository

    # Verifica a existência do nome normalizado antes de cadastrar uma nova habilidade.
    def create(self, data):
        name = data["nome"]
        name_key = normalize_key(name)
        if self.skill_repository.get_one({"nome_normalizado": name_key}):
            raise ConflictError("Esta habilidade já está cadastrada.")
        return self.skill_repository.create(
            {
                "nome": name,
                "nome_normalizado": name_key,
                "categoria": data.get("categoria") or "",
                "descricao": data.get("descricao") or "",
            }
        )

    # Retorna a habilidade ou sinaliza que ela não foi encontrada.
    def get_by_id(self, habilidade_id):
        skill = self.skill_repository.get_by_id(habilidade_id)
        if skill is None:
            raise NotFoundError("Habilidade não encontrada.")
        return skill

    # Consulta uma habilidade que corresponda aos filtros recebidos.
    def get_one(self, filters=None):
        return self.skill_repository.get_one(filters)

    # Ajusta posição inicial e tamanho de página antes de consultar as habilidades.
    def get_paginated(self, offset, limit, filters=None):
        offset = max(int(offset or 0), 0)
        limit = min(max(int(limit or 20), 1), MAX_PAGE_SIZE)
        return self.skill_repository.get_paginated(offset, limit, filters)

    # Prepara as mudanças e impede que a renomeação duplique outra habilidade.
    def update(self, habilidade_id, data):
        changes = {}
        if "nome" in data and data["nome"] is not None:
            name_key = normalize_key(data["nome"])
            duplicate = self.skill_repository.get_one({"nome_normalizado": name_key})
            if duplicate and duplicate.get("_id") != str(habilidade_id):
                raise ConflictError("Esta habilidade já está cadastrada.")
            changes["nome"] = data["nome"]
            changes["nome_normalizado"] = name_key
        if "categoria" in data:
            changes["categoria"] = data["categoria"] or ""
        if "descricao" in data:
            changes["descricao"] = data["descricao"] or ""
        if not changes:
            return self.get_by_id(habilidade_id)
        skill = self.skill_repository.update(habilidade_id, changes)
        if skill is None:
            raise NotFoundError("Habilidade não encontrada.")
        return skill

    # Remove a habilidade ou sinaliza que o registro não existe.
    def delete(self, habilidade_id):
        if not self.skill_repository.delete(habilidade_id):
            raise NotFoundError("Habilidade não encontrada.")
        return True
