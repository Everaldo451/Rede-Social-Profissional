from datetime import date, datetime, time, timezone

from bson import ObjectId
from bson.errors import InvalidId

from common.errors import InvalidDataError, NotFoundError
from common.validation import normalize_key
from database import get_mongo_database, get_neo4j_session


class UserOrganizationsRepository:
    def __init__(self, database=None, session_factory=None):
        if database is None:
            database = get_mongo_database()
        self.users = database["usuarios"]
        self.organizations = database["organizacoes"]
        self.session_factory = session_factory or get_neo4j_session

    @staticmethod
    def _object_id(value):
        try:
            return ObjectId(str(value))
        except (InvalidId, TypeError):
            return None

    @staticmethod
    def _as_datetime(value, label, *, required=False):
        if value is None:
            if required:
                raise InvalidDataError(f"O campo {label} é obrigatório.")
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, date):
            return datetime.combine(value, time.min, tzinfo=timezone.utc)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                raise InvalidDataError(f"Data inválida no campo {label}.") from None
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        raise InvalidDataError(f"Data inválida no campo {label}.")

    @staticmethod
    def _serialize(value):
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, list):
            return [UserOrganizationsRepository._serialize(item) for item in value]
        if isinstance(value, dict):
            return {
                key: UserOrganizationsRepository._serialize(item)
                for key, item in value.items()
            }
        return value

    def _resolve_organization_id(self, organization_id=None, organization_name=None):
        if organization_id:
            object_id = self._object_id(organization_id)
            if object_id is None:
                raise InvalidDataError("Identificador de organização inválido.")
            organization = self.organizations.find_one({"_id": object_id})
        elif organization_name:
            organization = self.organizations.find_one(
                {"nome_normalizado": normalize_key(organization_name)}
            )
        else:
            raise InvalidDataError("Informe a organização ou instituição.")
        if organization is None:
            raise NotFoundError("Organização ou instituição não encontrada.")
        return organization["_id"]

    def add_experience(self, user_id, data):
        user_object_id = self._object_id(user_id)
        if user_object_id is None:
            raise InvalidDataError("Identificador de usuário inválido.")
        organization_object_id = self._resolve_organization_id(
            data.get("organizacao_id"), data.get("organizacao_nome")
        )
        start = self._as_datetime(data.get("data_inicio"), "data de início", required=True)
        end = self._as_datetime(data.get("data_fim"), "data de término")
        experience = {
            "organizacao_id": organization_object_id,
            "cargo": data["cargo"],
            "data_inicio": start,
            "data_fim": end,
            "atual": bool(data.get("atual", end is None)),
            "descricao": data.get("descricao", ""),
        }
        result = self.users.update_one(
            {"_id": user_object_id},
            {
                "$addToSet": {"experiencias": experience},
                "$set": {"atualizado_em": datetime.now(timezone.utc)},
            },
        )
        if result.matched_count == 0:
            raise NotFoundError("Usuário não encontrado.")

        with self.session_factory() as session:
            session.run(
                """
                MERGE (p:Pessoa {id: $usuario_id})
                MERGE (o:Organizacao {id: $organizacao_id})
                MERGE (p)-[r:TRABALHOU_EM {
                    cargo: $cargo, data_inicio: $data_inicio
                }]->(o)
                SET r.data_fim = $data_fim, r.atual = $atual
                """,
                usuario_id=str(user_object_id),
                organizacao_id=str(organization_object_id),
                cargo=experience["cargo"],
                data_inicio=start.date(),
                data_fim=end.date() if end else None,
                atual=experience["atual"],
            ).consume()
        return self._serialize(experience)

    def remove_experience(self, user_id, organization_id, cargo, data_inicio):
        user_object_id = self._object_id(user_id)
        organization_object_id = self._object_id(organization_id)
        if user_object_id is None or organization_object_id is None:
            return False
        start = self._as_datetime(data_inicio, "data de início", required=True)
        result = self.users.update_one(
            {"_id": user_object_id},
            {
                "$pull": {
                    "experiencias": {
                        "organizacao_id": organization_object_id,
                        "cargo": cargo,
                        "data_inicio": start,
                    }
                },
                "$set": {"atualizado_em": datetime.now(timezone.utc)},
            },
        )
        with self.session_factory() as session:
            session.run(
                """
                MATCH (p:Pessoa {id: $usuario_id})
                      -[r:TRABALHOU_EM {
                          cargo: $cargo, data_inicio: $data_inicio
                      }]->
                      (o:Organizacao {id: $organizacao_id})
                DELETE r
                """,
                usuario_id=str(user_object_id),
                organizacao_id=str(organization_object_id),
                cargo=cargo,
                data_inicio=start.date(),
            ).consume()
        return result.modified_count > 0

    def add_education(self, user_id, data):
        user_object_id = self._object_id(user_id)
        if user_object_id is None:
            raise InvalidDataError("Identificador de usuário inválido.")
        institution_object_id = self._resolve_organization_id(
            data.get("instituicao_id"), data.get("instituicao_nome")
        )
        start_date = self._as_datetime(data.get("data_inicio"), "data de início")
        end_date = self._as_datetime(data.get("data_fim"), "data de conclusão")
        start_year = data.get("ano_inicio") or (start_date.year if start_date else None)
        end_year = data.get("ano_conclusao") or (end_date.year if end_date else None)
        education = {
            "instituicao_id": institution_object_id,
            "curso": data["curso"],
            "grau": data["grau"],
            "ano_inicio": start_year,
            "ano_conclusao": end_year,
        }
        result = self.users.update_one(
            {"_id": user_object_id},
            {
                "$addToSet": {"formacao": education},
                "$set": {"atualizado_em": datetime.now(timezone.utc)},
            },
        )
        if result.matched_count == 0:
            raise NotFoundError("Usuário não encontrado.")

        with self.session_factory() as session:
            session.run(
                """
                MERGE (p:Pessoa {id: $usuario_id})
                MERGE (o:Organizacao {id: $organizacao_id})
                MERGE (p)-[r:ESTUDOU_EM {
                    curso: $curso, grau: $grau
                }]->(o)
                SET r.ano_inicio = $ano_inicio, r.ano_conclusao = $ano_conclusao
                """,
                usuario_id=str(user_object_id),
                organizacao_id=str(institution_object_id),
                curso=education["curso"],
                grau=education["grau"],
                ano_inicio=start_year,
                ano_conclusao=end_year,
            ).consume()
        return self._serialize(education)

    def remove_education(self, user_id, institution_id, course, degree):
        user_object_id = self._object_id(user_id)
        institution_object_id = self._object_id(institution_id)
        if user_object_id is None or institution_object_id is None:
            return False
        result = self.users.update_one(
            {"_id": user_object_id},
            {
                "$pull": {
                    "formacao": {
                        "instituicao_id": institution_object_id,
                        "curso": course,
                        "grau": degree,
                    }
                },
                "$set": {"atualizado_em": datetime.now(timezone.utc)},
            },
        )
        with self.session_factory() as session:
            session.run(
                """
                MATCH (p:Pessoa {id: $usuario_id})
                      -[r:ESTUDOU_EM {curso: $curso, grau: $grau}]->
                      (o:Organizacao {id: $organizacao_id})
                DELETE r
                """,
                usuario_id=str(user_object_id),
                organizacao_id=str(institution_object_id),
                curso=course,
                grau=degree,
            ).consume()
        return result.modified_count > 0

    def add_membership(self, user_id, organization_id, papel, status, desde=None):
        user_object_id = self._object_id(user_id)
        organization_object_id = self._object_id(organization_id)
        if user_object_id is None or organization_object_id is None:
            raise InvalidDataError("Identificador inválido.")
        if self.users.find_one({"_id": user_object_id}) is None:
            raise NotFoundError("Usuário não encontrado.")
        if self.organizations.find_one({"_id": organization_object_id}) is None:
            raise NotFoundError("Organização não encontrada.")
        membership_start = self._as_datetime(desde, "data de início")

        with self.session_factory() as session:
            record = session.run(
                """
                MERGE (p:Pessoa {id: $usuario_id})
                MERGE (o:Organizacao {id: $organizacao_id})
                MERGE (p)-[r:MEMBRO_DE {papel: $papel}]->(o)
                SET r.status = $status, r.desde = $desde
                RETURN p.id AS usuario_id, o.id AS organizacao_id
                """,
                usuario_id=str(user_object_id),
                organizacao_id=str(organization_object_id),
                papel=papel,
                status=status,
                desde=membership_start.date() if membership_start else None,
            ).single()
        return record is not None

    def remove_membership(self, user_id, organization_id, papel):
        user_object_id = self._object_id(user_id)
        organization_object_id = self._object_id(organization_id)
        if user_object_id is None or organization_object_id is None:
            return False
        with self.session_factory() as session:
            record = session.run(
                """
                MATCH (p:Pessoa {id: $usuario_id})
                      -[r:MEMBRO_DE {papel: $papel}]->
                      (o:Organizacao {id: $organizacao_id})
                DELETE r
                RETURN count(r) AS removidas
                """,
                usuario_id=str(user_object_id),
                organizacao_id=str(organization_object_id),
                papel=papel,
            ).single()
        return record is not None and record["removidas"] > 0

    def get_by_user_id(self, user_id):
        user_object_id = self._object_id(user_id)
        if user_object_id is None:
            return []
        with self.session_factory() as session:
            records = session.run(
                """
                MATCH (p:Pessoa {id: $usuario_id})
                      -[r:TRABALHOU_EM|ESTUDOU_EM|MEMBRO_DE]->
                      (o:Organizacao)
                RETURN type(r) AS tipo, o.id AS organizacao_id,
                       r.cargo AS cargo, toString(r.data_inicio) AS data_inicio,
                       toString(r.data_fim) AS data_fim, r.atual AS atual,
                       r.curso AS curso, r.grau AS grau,
                       r.ano_inicio AS ano_inicio, r.ano_conclusao AS ano_conclusao,
                       r.papel AS papel, r.status AS status,
                       toString(r.desde) AS desde
                """,
                usuario_id=str(user_object_id),
            ).data()
        properties = (
            "cargo", "data_inicio", "data_fim", "atual", "curso", "grau",
            "ano_inicio", "ano_conclusao", "papel", "status", "desde",
        )
        relationships = []
        for record in records:
            relationship = {
                "tipo": record["tipo"],
                "organizacao_id": record["organizacao_id"],
            }
            relationship.update(
                {key: record[key] for key in properties if record.get(key) is not None}
            )
            relationships.append(relationship)
        return relationships

    def delete_by_user_id(self, user_id):
        user_object_id = self._object_id(user_id)
        if user_object_id is None:
            return False
        with self.session_factory() as session:
            record = session.run(
                """
                MATCH (p:Pessoa {id: $usuario_id})
                DETACH DELETE p
                RETURN count(p) AS removidas
                """,
                usuario_id=str(user_object_id),
            ).single()
        return record is not None and record["removidas"] > 0
