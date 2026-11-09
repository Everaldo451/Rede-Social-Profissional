class MentorshipRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def create(self, data):
        pass

    def get_by_id(self, mentorship_id):
        pass

    def filter_mentors(self, user_id, nome, habilidade_id):
        with self.session_factory() as session:
            return session.execute_read(
                lambda tx: tx.run(
                    """
                    MATCH (mentor:Pessoa)-[:POSSUI_HABILIDADE]->(skill:Habilidade)
                    WHERE mentor.id <> $user_id AND mentor.aceita_mentoria = true
                      AND ($skill_id IS NULL OR skill.id = $skill_id)
                      AND ($name = '' OR toLower(mentor.nome) CONTAINS toLower($name))
                    RETURN DISTINCT mentor.id AS id, mentor.nome AS nome
                    ORDER BY nome, id LIMIT 50
                    """,
                    user_id=user_id,
                    name=nome,
                    skill_id=habilidade_id,
                ).data()
            )

    def get_by_user_id(self, user_id):
        pass

    def list_all(self):
        pass

    def update(self, mentorship_id, data):
        pass

    def delete(self, mentorship_id):
        pass

    def recommend(self, user_id):
        with self.session_factory() as session:
            return session.execute_read(
                lambda tx: tx.run(
                    """
                    MATCH (user:Pessoa {id: $user_id})-[:DESEJA_DESENVOLVER]->(skill:Habilidade)
                          <-[:POSSUI_HABILIDADE]-(mentor:Pessoa)
                    WHERE mentor <> user AND mentor.aceita_mentoria = true
                    WITH DISTINCT mentor, skill ORDER BY skill.nome
                    RETURN mentor.id AS id, mentor.nome AS nome,
                           collect(skill.nome) AS habilidades, count(skill) AS afinidade
                    ORDER BY afinidade DESC, nome, id LIMIT 50
                    """,
                    user_id=user_id,
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
