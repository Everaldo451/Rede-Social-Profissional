# Monta os dados de autores e comentários usados pela apresentação do feed.
# Resolve o autor e fornece uma identificação alternativa quando o usuário foi removido.
def author_view(users: dict, user_id: str) -> dict:
    """Build the public author shape used by posts and comments."""
    user = users.get(str(user_id))
    if not user:
        return {"id": str(user_id), "name": "Usuário removido", "headline": ""}

    return {
        "id": str(user.get("id") or user.get("usuario_id") or user.get("_id") or user_id),
        "name": user.get("name") or user.get("nome") or "Usuário",
        "headline": user.get("headline") or "",
    }


# Acrescenta a identificação pública do autor aos dados de um comentário.
def comment_view(users: dict, comment: dict) -> dict:
    return {
        "id": str(comment.get("id") or comment.get("_id")),
        "post_id": str(comment.get("post_id")),
        "text": comment["text"],
        "created_at": comment["created_at"],
        "author": author_view(users, comment["author_id"]),
    }
