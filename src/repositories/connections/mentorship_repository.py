from datetime import datetime, timezone

from bson import ObjectId
from neo4j.exceptions import DriverError, Neo4jError

from database import get_mongo_database


class MentorshipRepository:
    COLLECTION = "mentorias"

    def __init__(self, session_factory, database=None):
        self.session_factory = session_factory
        if database is None:
            database = get_mongo_database()
        self.collection = database[self.COLLECTION]

    def create(self, data):
        mentor_id = self._object_id(data["mentor_id"])
        mentee_id = self._object_id(data["mentorado_id"])
        skill_id = self._object_id(data["habilidade_id"])
        if self.collection.find_one(
            {
                "mentor_id": mentor_id,
                "mentorado_id": mentee_id,
                "habilidade_id": skill_id,
                "status": {"$in": ["solicitado", "ativa"]},
            }
        ):
            raise ValueError(
                "Já existe uma mentoria ativa ou pendente para essa habilidade."
            )

        mentorship_id = ObjectId()
        created_at = datetime.now(timezone.utc)
        document = {
            "_id": mentorship_id,
            "mentor_id": mentor_id,
            "mentorado_id": mentee_id,
            "habilidade_id": skill_id,
            "status": "solicitado",
            "criada_em": created_at,
            "iniciada_em": None,
            "encerrada_em": None,
        }
        self.collection.insert_one(document)
        try:
            with self.session_factory() as session:
                created = session.execute_write(
                    lambda tx: tx.run(
                        """
                        MATCH (mentor:Pessoa {id: $mentor_id}),
                              (mentee:Pessoa {id: $mentee_id}),
                              (skill:Habilidade {id: $skill_id})
                        CREATE (mentor)-[:MENTORA {
                            mentoria_id: $mentorship_id,
                            habilidade_id: $skill_id,
                            status: 'solicitado',
                            criada_em: $created_at,
                            atualizada_em: $created_at
                        }]->(mentee)
                        MERGE (mentee)-[desired:DESEJA_DESENVOLVER {
                            mentoria_id: $mentorship_id
                        }]->(skill)
                        ON CREATE SET desired.desde = $created_at,
                                      desired.nivel = 'iniciante'
                        RETURN $mentorship_id AS id
                        """,
                        mentor_id=str(mentor_id),
                        mentee_id=str(mentee_id),
                        skill_id=str(skill_id),
                        mentorship_id=str(mentorship_id),
                        created_at=created_at,
                    ).single()
                )
            if created is None:
                raise ValueError(
                    "Mentor, mentorado ou habilidade não encontrado no grafo."
                )
        except (DriverError, Neo4jError, ValueError):
            self.collection.delete_one({"_id": mentorship_id})
            raise
        return self._serialize(document)

    def get_by_id(self, mentorship_id):
        object_id = self._object_id(mentorship_id, allow_none=True)
        if object_id is None:
            return None
        return self._serialize(self.collection.find_one({"_id": object_id}))

    def filter_mentors(self, user_id, nome, habilidade_id, offset=0, limit=20):
        with self.session_factory() as session:
            return session.execute_read(
                lambda tx: tx.run(
                    """
                    MATCH (mentor:Pessoa)-[:POSSUI_HABILIDADE]->(skill:Habilidade)
                    WHERE mentor.id <> $user_id AND mentor.aceita_mentoria = true
                      AND ($skill_id IS NULL OR skill.id = $skill_id)
                      AND ($name = '' OR toLower(mentor.nome) CONTAINS toLower($name))
                    RETURN mentor.id AS id, mentor.nome AS nome,
                           collect(DISTINCT skill.id) AS habilidade_ids
                    ORDER BY nome, id
                    SKIP $offset LIMIT $limit
                    """,
                    user_id=user_id,
                    name=nome,
                    skill_id=habilidade_id,
                    offset=offset,
                    limit=limit,
                ).data()
            )

    def get_by_user_id(self, user_id):
        pass

    def list_all(self):
        pass

    def update(self, mentorship_id, data):
        object_id = self._object_id(mentorship_id, allow_none=True)
        if object_id is None:
            return None
        current = self.collection.find_one(
            {"_id": object_id, "status": "solicitado"}
        )
        if current is None:
            return None

        updated_at = datetime.now(timezone.utc)
        updates = dict(data)
        updates["atualizada_em"] = updated_at
        result = self.collection.update_one(
            {"_id": object_id, "status": "solicitado"},
            {"$set": updates},
        )
        if result.modified_count == 0:
            return None

        status = updates["status"]
        try:
            with self.session_factory() as session:
                graph_update = session.execute_write(
                    lambda tx: tx.run(
                        """
                        MATCH (mentor:Pessoa {id: $mentor_id}),
                              (mentee:Pessoa {id: $mentee_id})
                        OPTIONAL MATCH (mentor)-[existing:MENTORA]->(mentee)
                        WHERE existing.mentoria_id = $mentorship_id
                           OR (existing.status = 'solicitado'
                               AND existing.criada_em = $created_at)
                        WITH mentor, mentee, collect(existing) AS relationships
                        FOREACH (relationship IN relationships |
                            SET relationship.status = $status,
                                relationship.atualizada_em = $updated_at,
                                relationship.mentoria_id = $mentorship_id,
                                relationship.habilidade_id = $skill_id
                        )
                        FOREACH (_ IN CASE WHEN size(relationships) = 0
                                           THEN [1] ELSE [] END |
                            CREATE (mentor)-[:MENTORA {
                                mentoria_id: $mentorship_id,
                                habilidade_id: $skill_id,
                                status: $status,
                                criada_em: $created_at,
                                atualizada_em: $updated_at
                            }]->(mentee)
                        )
                        RETURN size(relationships) AS matched
                        """,
                        mentor_id=str(current["mentor_id"]),
                        mentee_id=str(current["mentorado_id"]),
                        skill_id=str(current["habilidade_id"]),
                        mentorship_id=str(object_id),
                        created_at=current["criada_em"],
                        updated_at=updated_at,
                        status=status,
                    ).single()
                )
            if graph_update is None:
                raise ValueError("Mentor ou mentorado não encontrado no grafo.")
        except (DriverError, Neo4jError, ValueError):
            self.collection.update_one(
                {"_id": object_id},
                {
                    "$set": {
                        "status": "solicitado",
                        "iniciada_em": None,
                        "encerrada_em": None,
                    },
                    "$unset": {"atualizada_em": ""},
                },
            )
            raise
        return self.get_by_id(object_id)

    def delete(self, mentorship_id):
        pass

    def list_requests(self, user_id):
        object_id = self._object_id(user_id, allow_none=True)
        if object_id is None:
            return []
        cursor = self.collection.find(
            {"$or": [{"mentor_id": object_id}, {"mentorado_id": object_id}]}
        ).sort("criada_em", -1)
        return [self._serialize(document) for document in cursor]

    def mentor_has_skill(self, mentor_id, skill_id):
        with self.session_factory() as session:
            return session.execute_read(
                lambda tx: tx.run(
                    """
                    MATCH (mentor:Pessoa {id: $mentor_id})-[:POSSUI_HABILIDADE|ENSINA]->
                          (skill:Habilidade {id: $skill_id})
                    RETURN count(skill) > 0 AS has_skill
                    """,
                    mentor_id=str(mentor_id),
                    skill_id=str(skill_id),
                ).single(strict=True)["has_skill"]
            )

    def recommend(self, user_id, offset=0, limit=20):
        with self.session_factory() as session:
            return session.execute_read(
                lambda tx: tx.run(
                    """
                    MATCH (user:Pessoa {id: $user_id})-[:DESEJA_DESENVOLVER]->(skill:Habilidade)
                          <-[:POSSUI_HABILIDADE]-(mentor:Pessoa)
                    WHERE mentor <> user AND mentor.aceita_mentoria = true
                    WITH DISTINCT mentor, skill ORDER BY skill.nome
                    RETURN mentor.id AS id, mentor.nome AS nome,
                           collect(skill.nome) AS habilidades,
                           collect(skill.id) AS habilidade_ids,
                           count(skill) AS afinidade
                    ORDER BY afinidade DESC, nome, id
                    SKIP $offset LIMIT $limit
                    """,
                    user_id=user_id,
                    offset=offset,
                    limit=limit,
                ).data()
            )

    def desired_skills(self, user_id):
        with self.session_factory() as session:
            return session.execute_read(
                lambda tx: tx.run(
                    """
                    MATCH (:Pessoa {id: $user_id})-[:DESEJA_DESENVOLVER]->(skill:Habilidade)
                    RETURN DISTINCT skill.nome AS nome ORDER BY nome
                    """,
                    user_id=user_id,
                ).value("nome")
            )

    @staticmethod
    def _object_id(value, allow_none=False):
        if isinstance(value, ObjectId):
            return value
        if ObjectId.is_valid(str(value)):
            return ObjectId(str(value))
        if allow_none:
            return None
        raise ValueError("Identificador de mentoria inválido.")

    @staticmethod
    def _serialize(document):
        if document is None:
            return None
        result = dict(document)
        for field in ("_id", "mentor_id", "mentorado_id", "habilidade_id"):
            if result.get(field) is not None:
                result[field] = str(result[field])
        return result
