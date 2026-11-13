# Implementações em memória das dependências usadas pelos testes de regras de negócio.
"""Repositórios em memória para testar as regras de negócio sem bancos."""
from collections import defaultdict
from itertools import count
from types import SimpleNamespace

from bson import ObjectId

_ids = count(1)


# Gera um identificador textual no formato ObjectId para os registros simulados.
def new_id() -> str:
    return str(ObjectId())


# Simula o cadastro e as consultas de usuários sem acessar o MongoDB.
class FakeUserRepository:
    def __init__(self):
        self.users = {}

    # Inclui um usuário no conjunto de dados do teste e devolve seu identificador.
    def add(self, name, headline=""):
        uid = new_id()
        self.users[uid] = {"id": uid, "name": name, "headline": headline, "email": f"{uid}@x.com"}
        return uid

    # Consulta um registro na estrutura em memória usada pelo teste.
    def get_by_id(self, user_id):
        return self.users.get(user_id)

    # Obtém os usuários solicitados sem consultar um banco externo.
    def get_many_by_ids(self, ids):
        return {i: self.users[i] for i in ids if i in self.users}


# Simula persistência, filtros e ordenação de publicações em memória.
class FakePostRepository:
    def __init__(self):
        self.posts = {}
        self._order = count()

    # Inclui um registro na estrutura em memória e devolve os dados simulados.
    def create(self, data):
        post = {**data, "id": str(ObjectId()), "_n": next(self._order)}
        self.posts[post["id"]] = post
        return dict(post)

    # Consulta um registro na estrutura em memória usada pelo teste.
    def get_by_id(self, post_id):
        post = self.posts.get(post_id)
        return dict(post) if post else None

    # Aplica categoria e tag e ordena as publicações simuladas da mais recente para a mais antiga.
    def _filtered(self, filters):
        posts = list(self.posts.values())
        if filters and filters.get("category"):
            posts = [p for p in posts if p["category"] == filters["category"]]
        if filters and filters.get("tag"):
            posts = [p for p in posts if filters["tag"] in p["tags"]]
        return sorted(posts, key=lambda p: (p["created_at"], p["_n"]), reverse=True)

    # Recorta os resultados filtrados conforme a posição e o limite da página.
    def get_paginated(self, offset, limit, filters=None):
        return [dict(p) for p in self._filtered(filters)[offset:offset + limit]]

    # Conta as publicações simuladas que atendem aos filtros.
    def count(self, filters=None):
        return len(self._filtered(filters))

    # Retorna todas as publicações simuladas na ordem usada pelo feed.
    def list_all(self):
        return [dict(p) for p in self._filtered(None)]

    # Altera os campos da publicação em memória.
    def update(self, post_id, data):
        self.posts[post_id].update(data)
        return True

    # Remove o registro da estrutura em memória e informa se ele existia.
    def delete(self, post_id):
        return self.posts.pop(post_id, None) is not None


# Simula o armazenamento e o agrupamento de comentários por publicação.
class FakeCommentRepository:
    def __init__(self):
        self.comments = []

    # Inclui um registro na estrutura em memória e devolve os dados simulados.
    def create(self, data):
        comment = {**data, "id": new_id()}
        self.comments.append(comment)
        return dict(comment)

    # Agrupa os comentários simulados pelos identificadores das publicações.
    def list_by_post_ids(self, post_ids):
        grouped = defaultdict(list)
        for c in self.comments:
            if c["post_id"] in post_ids:
                grouped[c["post_id"]].append(dict(c))
        return grouped

    # Remove da lista todos os comentários da publicação escolhida.
    def delete_by_post(self, post_id):
        self.comments = [c for c in self.comments if c["post_id"] != post_id]


# Simula arquivos e metadados de mídia em um dicionário.
class FakeMediaRepository:
    def __init__(self):
        self.files = {}

    # Inclui um registro na estrutura em memória e devolve os dados simulados.
    def create(self, data):
        media_id = new_id()
        media = {
            "media_id": media_id,
            "filename": data["filename"],
            "content": data["content"],
            "length": len(data["content"]),
            "metadata": data["metadata"],
        }
        self.files[media_id] = media
        return media

    # Consulta um registro na estrutura em memória usada pelo teste.
    def get_by_id(self, file_id):
        return self.files.get(file_id)

    # Filtra os arquivos simulados pelos metadados informados.
    def list(self, filters=None):
        filters = filters or {}
        return [
            media
            for media in self.files.values()
            if all(media["metadata"].get(key) == value for key, value in filters.items())
        ]

    # Remove o registro da estrutura em memória e informa se ele existia.
    def delete(self, file_id):
        return self.files.pop(file_id, None) is not None


def post_data(text="Olá, TI!", **extra):
    """Imita um DTO já validado (os services só leem atributos)."""
    fields = {"text": text, "category": "Dica", "tags": [], "code": None,
              "code_language": "python", "remove_media_ids": [], **extra}
    return SimpleNamespace(**fields)


# Monta um objeto com o atributo de texto esperado pelo serviço de comentários.
def comment_data(text="Boa!"):
    return SimpleNamespace(text=text)
