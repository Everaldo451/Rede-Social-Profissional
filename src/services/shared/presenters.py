def author_view(users: dict, user_id: str) -> dict:
    """Dados públicos do autor; tolera usuários removidos."""
    user = users.get(user_id)
    if not user:
        return {"id": user_id, "name": "Usuário removido", "headline": ""}
    return {"id": user["id"], "name": user["name"], "headline": user.get("headline", "")}


def comment_view(users: dict, comment: dict) -> dict:
    return {
        "id": comment["id"],
        "post_id": comment["post_id"],
        "text": comment["text"],
        "created_at": comment["created_at"],
        "author": author_view(users, comment["author_id"]),
    }
