# Persiste curtidas garantindo a unicidade do par usuário e publicação.
from datetime import datetime, timezone

from common.errors import InvalidDataError
from repositories.shared.mongo_utils import serialize, to_object_id


class LikeRepository:
    def __init__(self, database):
        self._items = database["curtidas"]
        # O índice composto único impede que o mesmo usuário curta a mesma publicação duas vezes.
        self._items.create_index(
            [("usuario_id", 1), ("post_id", 1)], unique=True
        )

    # Valida e converte os identificadores do usuário e da publicação.
    @staticmethod
    def _ids(user_id, post_id):
        user_object_id = to_object_id(user_id)
        post_object_id = to_object_id(post_id)
        if user_object_id is None or post_object_id is None:
            raise InvalidDataError("Identificador de usuário ou publicação inválido.")
        return user_object_id, post_object_id

    # Adapta os nomes dos campos do documento ao formato esperado pelos serviços.
    @staticmethod
    def _canonical(document):
        like = serialize(document)
        if like is None:
            return None
        like["user_id"] = str(like.pop("usuario_id"))
        like["post_id"] = str(like["post_id"])
        return like

    # Usa upsert e $setOnInsert para criar a curtida apenas quando o par ainda não existe.
    def create(self, user_id, post_id):
        user_id, post_id = self._ids(user_id, post_id)
        query = {"usuario_id": user_id, "post_id": post_id}
        self._items.update_one(
            query,
            {
                "$setOnInsert": {
                    **query,
                    "criada_em": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )
        return self._canonical(self._items.find_one(query))

    # Consulta uma curtida pelo identificador.
    def get_by_id(self, like_id):
        object_id = to_object_id(like_id)
        return self._canonical(self._items.find_one({"_id": object_id})) if object_id else None

    # Lista as curtidas de uma publicação com identificadores serializados.
    def get_by_post_id(self, post_id):
        object_id = to_object_id(post_id)
        if object_id is None:
            return []
        return [
            self._canonical(item)
            for item in self._items.find({"post_id": object_id})
        ]

    # Remove a curtida específica de um usuário em uma publicação.
    def delete_user_like(self, user_id, post_id):
        user_id, post_id = self._ids(user_id, post_id)
        return self._items.delete_one(
            {"usuario_id": user_id, "post_id": post_id}
        ).deleted_count > 0

    # Remove uma curtida pelo identificador e informa se a exclusão ocorreu.
    def delete(self, like_id):
        object_id = to_object_id(like_id)
        return bool(
            object_id
            and self._items.delete_one({"_id": object_id}).deleted_count
        )
