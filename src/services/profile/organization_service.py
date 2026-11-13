from common.errors import NotFoundError
from common.validation import normalize_key

MAX_PAGE_SIZE = 100


class OrganizationService:
    def __init__(self, organization_repository):
        self.organization_repository = organization_repository

    @staticmethod
    def _location_fields(data):
        city = data.get("cidade")
        state = data.get("estado")
        location = data.get("localizacao")
        if location and not city:
            city, separator, location_state = location.rpartition(",")
            if separator:
                city = city.strip()
                state = state or location_state.strip()
            else:
                city = location.strip()
        return {"cidade": city, "estado": state}

    def create(self, data, criado_por_usuario_id=None):
        name = data["nome"]
        document = {
            "nome": name,
            "nome_normalizado": normalize_key(name),
            "tipos": [data["tipo"]],
            "setor": data.get("setor"),
            "sigla": data.get("sigla"),
            "site": data.get("site"),
            "status_verificacao": "pendente",
            **self._location_fields(data),
        }
        if data.get("descricao") is not None:
            document["descricao"] = data["descricao"]
        if criado_por_usuario_id is not None:
            document["criado_por_usuario_id"] = criado_por_usuario_id
        return self.organization_repository.create(document)

    def get_by_id(self, organizacao_id):
        organization = self.organization_repository.get_by_id(organizacao_id)
        if organization is None:
            raise NotFoundError("Organização não encontrada.")
        return organization

    def get_paginated(self, offset, limit, filters=None):
        offset = max(int(offset or 0), 0)
        limit = min(max(int(limit or 20), 1), MAX_PAGE_SIZE)
        return self.organization_repository.get_paginated(offset, limit, filters)

    def list_all(self):
        return self.organization_repository.list_all()

    def update(self, organizacao_id, data):
        changes = {}
        if data.get("nome") is not None:
            changes["nome"] = data["nome"]
            changes["nome_normalizado"] = normalize_key(data["nome"])
        if data.get("tipo") is not None:
            changes["tipos"] = [data["tipo"]]
        for field, database_field in (
            ("setor", "setor"),
            ("descricao", "descricao"),
            ("site", "site"),
            ("sigla", "sigla"),
            ("cidade", "cidade"),
            ("estado", "estado"),
        ):
            if field in data:
                changes[database_field] = data[field]
        if "localizacao" in data:
            changes.update(self._location_fields(data))
        if not changes:
            return self.get_by_id(organizacao_id)
        organization = self.organization_repository.update(organizacao_id, changes)
        if organization is None:
            raise NotFoundError("Organização não encontrada.")
        return organization

    def delete(self, organizacao_id):
        if not self.organization_repository.delete(organizacao_id):
            raise NotFoundError("Organização não encontrada.")
        return True
