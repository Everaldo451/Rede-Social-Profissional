# Mantém as relações de habilidades no Neo4j e as habilidades possuídas no documento do usuário.
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from common.choices import SKILL_TYPES
from common.errors import InvalidDataError
from database import get_mongo_database, get_neo4j_session


class UserSkillRepository:
    # Traduz os tipos usados pelos formulários para os nomes das relações do Neo4j.
    _RELATIONSHIPS = {
        "has": "POSSUI_HABILIDADE",
        "wants": "DESEJA_DESENVOLVER",
        "teaches": "ENSINA",
    }

    def __init__(self, session_factory=None, database=None):
        if database is None:
            database = get_mongo_database()
        self.users = database["usuarios"]
        self.skills = database["habilidades"]
        self.session_factory = session_factory or get_neo4j_session

    # Valida o ObjectId e retorna sua representação textual, usada nos nós do grafo.
    @staticmethod
    def _object_id(value):
        try:
            return str(ObjectId(str(value)))
        except (InvalidId, TypeError):
            return None

    # Verifica usuário e habilidade e grava o vínculo com as propriedades correspondentes ao tipo.
    def add_skill(
        self,
        user_id,
        skill_id,
        skill_type,
        nivel=None,
        experiencia_anos=None,
        modalidade=None,
        disponibilidade=None,
    ):
        if skill_type not in SKILL_TYPES:
            raise InvalidDataError("Tipo de competência inválido.")
        user_object_id = self._object_id(user_id)
        skill_object_id = self._object_id(skill_id)
        if user_object_id is None or skill_object_id is None:
            return False
        user_mongo_id = ObjectId(user_object_id)
        if self.users.find_one({"_id": user_mongo_id}) is None:
            return False
        if self.skills.find_one({"_id": ObjectId(skill_object_id)}) is None:
            return False

        # Habilidades possuídas também ficam embutidas no documento do usuário.
        if skill_type == "has":
            skill_entry = {
                "habilidade_id": ObjectId(skill_object_id),
                "nivel": nivel,
                "anos_experiencia": experiencia_anos,
            }
            update = self.users.update_one(
                {
                    "_id": user_mongo_id,
                    "habilidades.habilidade_id": skill_entry["habilidade_id"],
                },
                {
                    "$set": {
                        "habilidades.$.nivel": nivel,
                        "habilidades.$.anos_experiencia": experiencia_anos,
                        "atualizado_em": datetime.now(timezone.utc),
                    }
                },
            )
            if update.matched_count == 0:
                update = self.users.update_one(
                    {"_id": user_mongo_id},
                    {
                        "$addToSet": {"habilidades": skill_entry},
                        "$set": {"atualizado_em": datetime.now(timezone.utc)},
                    },
                )
            if update.matched_count == 0:
                return False

        # O tipo validado escolhe a relação do grafo e as propriedades específicas que serão gravadas.
        relationship = self._RELATIONSHIPS[skill_type]
        now = datetime.now(timezone.utc)
        if skill_type == "has":
            query = f"""
                MERGE (person:Pessoa {{id: $usuario_id}})
                MERGE (skill:Habilidade {{id: $habilidade_id}})
                MERGE (person)-[relation:{relationship}]->(skill)
                SET relation.nivel = $nivel
                RETURN person.id AS usuario_id, skill.id AS habilidade_id
            """
        elif skill_type == "wants":
            query = f"""
                MERGE (person:Pessoa {{id: $usuario_id}})
                MERGE (skill:Habilidade {{id: $habilidade_id}})
                MERGE (person)-[relation:{relationship}]->(skill)
                ON CREATE SET relation.desde = $desde
                SET relation.nivel = $nivel
                RETURN person.id AS usuario_id, skill.id AS habilidade_id
            """
        else:
            query = f"""
                MERGE (person:Pessoa {{id: $usuario_id}})
                MERGE (skill:Habilidade {{id: $habilidade_id}})
                MERGE (person)-[relation:{relationship}]->(skill)
                SET relation.nivel = $nivel,
                    relation.experiencia_anos = $experiencia_anos,
                    relation.modalidade = $modalidade,
                    relation.disponibilidade = $disponibilidade
                RETURN person.id AS usuario_id, skill.id AS habilidade_id
            """

        with self.session_factory() as session:
            record = session.run(
                query,
                usuario_id=user_object_id,
                habilidade_id=skill_object_id,
                desde=now,
                nivel=nivel,
                experiencia_anos=experiencia_anos,
                modalidade=modalidade,
                disponibilidade=disponibilidade,
            ).single()
        return record is not None

    # Remove o vínculo no grafo e, para habilidades possuídas, a entrada no perfil MongoDB.
    def remove_skill(self, user_id, skill_id, skill_type):
        if skill_type not in SKILL_TYPES:
            raise InvalidDataError("Tipo de competência inválido.")
        user_object_id = self._object_id(user_id)
        skill_object_id = self._object_id(skill_id)
        if user_object_id is None or skill_object_id is None:
            return False

        relationship = self._RELATIONSHIPS[skill_type]
        query = f"""
            MATCH (person:Pessoa {{id: $usuario_id}})
                  -[relation:{relationship}]->
                  (skill:Habilidade {{id: $habilidade_id}})
            DELETE relation
            RETURN count(relation) AS removidas
        """
        with self.session_factory() as session:
            record = session.run(
                query,
                usuario_id=user_object_id,
                habilidade_id=skill_object_id,
            ).single()
        graph_removed = record is not None and record["removidas"] > 0
        if skill_type == "has":
            mongo_result = self.users.update_one(
                {"_id": ObjectId(user_object_id)},
                {
                    "$pull": {"habilidades": {"habilidade_id": ObjectId(skill_object_id)}},
                    "$set": {"atualizado_em": datetime.now(timezone.utc)},
                },
            )
            return graph_removed or mongo_result.modified_count > 0
        return graph_removed

    # Monta a consulta de relações usando somente os filtros de usuário, habilidade, tipo e nível.
    def get_skills(self, filters=None):
        filters = filters or {}
        supported_filters = {"usuario_id", "habilidade_id", "tipo", "nivel"}
        unsupported_filters = set(filters) - supported_filters
        if unsupported_filters:
            raise InvalidDataError("Filtro de competência inválido.")

        where = []
        parameters = {}
        for field in ("usuario_id", "habilidade_id"):
            if filters.get(field) is not None:
                object_id = self._object_id(filters[field])
                if object_id is None:
                    return []
                node = "person" if field == "usuario_id" else "skill"
                where.append(f"{node}.id = ${field}")
                parameters[field] = object_id

        skill_type = filters.get("tipo")
        if skill_type is not None:
            if skill_type not in SKILL_TYPES:
                raise InvalidDataError("Tipo de competência inválido.")
            where.append("type(relation) = $tipo_relacionamento")
            parameters["tipo_relacionamento"] = self._RELATIONSHIPS[skill_type]

        nivel = filters.get("nivel")
        if nivel is not None:
            where.append("relation.nivel = $nivel")
            parameters["nivel"] = nivel

        where_clause = f"WHERE {' AND '.join(where)}" if where else ""
        query = f"""
            MATCH (person:Pessoa)-[relation:POSSUI_HABILIDADE|DESEJA_DESENVOLVER|ENSINA]
                  ->(skill:Habilidade)
            {where_clause}
            RETURN person.id AS usuario_id,
                   skill.id AS habilidade_id,
                   type(relation) AS tipo_relacionamento,
                   relation.nivel AS nivel,
                   relation.experiencia_anos AS experiencia_anos,
                   relation.modalidade AS modalidade,
                   relation.disponibilidade AS disponibilidade,
                   toString(relation.desde) AS desde
        """
        with self.session_factory() as session:
            records = session.run(query, **parameters).data()

        # Converte os nomes das relações do grafo de volta para os tipos usados na aplicação.
        relationship_types = {value: key for key, value in self._RELATIONSHIPS.items()}
        return [
            {
                "usuario_id": record["usuario_id"],
                "habilidade_id": record["habilidade_id"],
                "tipo": relationship_types[record["tipo_relacionamento"]],
                "nivel": record.get("nivel"),
                "experiencia_anos": record.get("experiencia_anos"),
                "modalidade": record.get("modalidade"),
                "disponibilidade": record.get("disponibilidade"),
                "desde": record.get("desde"),
            }
            for record in records
        ]
