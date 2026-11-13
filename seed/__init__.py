<<<<<<< HEAD
"""Database seeding script."""


def main() -> None:
    """Populate the database."""
    print("Seed script is ready for database population.")
=======
"""Popula o banco com usuários e publicações de exemplo (área de TI).

Uso (dentro do container): python seed/__init__.py
Senha de todos os usuários de exemplo: senha1234
"""
from container import build_container

PASSWORD = "senha1234"
USERS = [
    {"name": "Ana Souza", "headline": "Dev Backend Python", "email": "ana@exemplo.com"},
    {"name": "Bruno Lima", "headline": "DevOps / SRE", "email": "bruno@exemplo.com"},
    {"name": "Carla Mendes", "headline": "Tech Recruiter", "email": "carla@exemplo.com"},
]
POSTS = [
    (0, {"text": "Dica rápida: use `with` para garantir que arquivos sejam fechados, mesmo com exceções.",
         "category": "Dica", "tags": "python, boaspraticas",
         "code": "with open('dados.txt') as f:\n    linhas = f.readlines()", "code_language": "python"}),
    (1, {"text": "Qual a diferença prática entre um volume e um bind mount no Docker?",
         "category": "Dúvida", "tags": "docker, devops"}),
    (2, {"text": "Estamos contratando pessoa desenvolvedora Java pleno (remoto). Chame no privado!",
         "category": "Vaga", "tags": "java, vaga, remoto"}),
]
COMMENTS = [
    (1, 0, "Ótima dica! Também vale conhecer o `contextlib` para criar seus próprios gerenciadores de contexto."),
    (0, 1, "Volume é gerenciado pelo Docker; bind mount aponta para um caminho do host. Em dev, bind mount facilita o hot reload."),
]


def main() -> None:
    c = build_container()
    ids = {}
    for index, user in enumerate(USERS):
        c.users.register({**user, "password": PASSWORD})  # ignora se já existir
        login = c.sessions.login({"email": user["email"], "password": PASSWORD})
        ids[index] = login.data["user"]["id"]

    if c.posts.get_paginated(0, 1).data["total"] > 0:
        print("Já existem publicações; nada a fazer.")
        return

    post_ids = []
    for author, data in POSTS:
        post_ids.append(c.posts.create(ids[author], data).data["id"])
    for author, post, text in COMMENTS:
        c.comments.create(ids[author], post_ids[post], {"text": text})
    print(f"Seed concluído. Entre com ana@exemplo.com / {PASSWORD}")
>>>>>>> f6102f7 (feat/publicação)


if __name__ == "__main__":
    main()
