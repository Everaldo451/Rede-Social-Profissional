import html
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import streamlit as st

from common.errors import NotFoundError
from components.shared.profile_identity import render_profile_identity
from components.shared.sidebar import render_sidebar
from controllers.connections.connection_controller import ConnectionController
from controllers.posts.comment_controller import CommentController
from controllers.posts.like_controller import LikeController
from controllers.posts.post_controller import PostController
from controllers.shared.media_controller import MediaController
from database import get_mongo_database, get_neo4j_session, get_redis_client
from dto.posts.request.post_requests import (
    CATEGORIES,
    CODE_LANGUAGES,
    MAX_COMMENT,
    MAX_TEXT,
)
from pages.Sessoes import COOKIE_NAME, build_runtime, get_cookie_controller
from repositories.connections.connection_repository import ConnectionRepository
from repositories.connections.professional_repository import ProfessionalRepository
from repositories.notifications.notification_repository import NotificationRepository
from repositories.posts.like_repository import LikeRepository
from repositories.posts.comment_repository import CommentRepository
from repositories.posts.post_repository import PostRepository
from repositories.profile.user_repository import UserRepository
from repositories.shared.media_repository import MediaRepository
from services.connections.connection_service import ConnectionService
from services.notifications.notification_service import NotificationService
from services.posts.like_service import LikeService
from services.posts.comment_service import CommentService
from services.posts.post_service import PostService
from services.shared.media_service import MediaFile, MediaService

_FLASH_KEY = "flash_message"
BRT = timezone(timedelta(hours=-3))
PAGE_SIZE = 10
UPLOAD_TYPES = ["png", "jpg", "jpeg", "gif", "webp"]
UPLOAD_HELP = "Imagens PNG, JPG, GIF ou WEBP — até 4 arquivos de 10 MB."


def set_flash(kind: str, message: str) -> None:
    st.session_state[_FLASH_KEY] = (kind, message)


def show_flash() -> None:
    flash = st.session_state.pop(_FLASH_KEY, None)
    if flash:
        kind, message = flash
        {"success": st.success, "error": st.error}.get(kind, st.info)(message)


def format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BRT).strftime("%d/%m/%Y %H:%M")


def to_media_files(uploaded_files) -> list[MediaFile]:
    return [
        MediaFile(file.name, file.type or "application/octet-stream", file.getvalue())
        for file in (uploaded_files or [])
    ]


def render_comments(services, post, user) -> None:
    comments = post["comments"]
    with st.expander(f"💬 Comentários ({len(comments)})"):
        for comment in comments:
            st.markdown(
                f"**{comment['author']['name']}** · :gray[{format_datetime(comment['created_at'])}]"
            )
            st.write(comment["text"])
        if not comments:
            st.caption("Ainda não há comentários.")

        if user is None:
            return
        if post["author"]["id"] == user["usuario_id"]:
            st.caption("Você é o autor desta publicação; apenas outros usuários podem comentá-la.")
            return

        with st.form(f"comment_form_{post['id']}", clear_on_submit=True):
            text = st.text_input("Escreva um comentário", max_chars=MAX_COMMENT)
            submitted = st.form_submit_button("Comentar")
        if submitted:
            result = services.comments.create(
                user["usuario_id"], post["id"], {"text": text}
            )
            if result.status:
                set_flash("success", "Comentário publicado.")
                st.rerun()
            st.error(result.message)


def _connection_state(controller, user_id):
    connected_ids = set()
    pending = {}
    count = controller.count_connections(user_id)
    if count.status and count.data:
        connections = controller.get_paginated_for_user(
            user_id, 0, count.data
        )
        if connections.status:
            connected_ids = {
                str(profile["_id"]) for profile in connections.data
            }
        else:
            st.warning(connections.message)
    elif not count.status:
        st.warning(count.message)

    requests = controller.list_requests(user_id)
    if requests.status:
        for request in requests.data:
            other_id = (
                request["remetente_id"]
                if request["recebida"]
                else request["destinatario_id"]
            )
            pending[str(other_id)] = request
    else:
        st.warning(requests.message)
    return connected_ids, pending


def _render_connection_action(controller, post, user, connected_ids, pending):
    if user is None:
        return
    user_id = str(user["usuario_id"])
    author_id = str(post["author"]["id"])
    if author_id == user_id:
        return
    if author_id in connected_ids:
        st.caption("Conectado")
        return

    request = pending.get(author_id)
    if request:
        if not request["recebida"]:
            st.caption("Solicitação enviada")
            return
        if st.button("Aceitar conexão", key=f"accept_post_author_{post['id']}"):
            result = controller.update_connection_request(
                user_id,
                request["remetente_id"],
                {"solicitacao_id": request["id"], "acao": "aceitar"},
            )
            if result.status:
                st.rerun()
            st.error(result.message)
        return

    if st.button("Conectar", key=f"connect_post_author_{post['id']}"):
        result = controller.request_connection(user_id, author_id)
        if result.status:
            st.session_state["feed_feedback"] = "Solicitação de conexão enviada."
            st.rerun()
        st.error(result.message)


def render_feed(services, user, connection_controller=None) -> None:
    page = st.session_state.get("feed_page", 0)
    result = services.posts.get_paginated(page * PAGE_SIZE, PAGE_SIZE)
    if not result.status:
        st.error(result.message)
        return

    items, total = result.data["items"], result.data["total"]
    if not items and page > 0:
        st.session_state["feed_page"] = max(0, (total - 1) // PAGE_SIZE)
        st.rerun()
    if not items:
        st.info("Nenhuma publicação encontrada. Que tal publicar a primeira?")
        return

    connected_ids, pending = (set(), {})
    if user is not None and connection_controller is not None:
        connected_ids, pending = _connection_state(
            connection_controller, user["usuario_id"]
        )

    st.caption(f"{total} publicação(ões)")
    feedback = st.session_state.pop("feed_feedback", None)
    if feedback:
        st.success(feedback)
    for post in items:
        render_post_card(
            services,
            post,
            user,
            connection_controller,
            connected_ids,
            pending,
        )

    last_page = (total - 1) // PAGE_SIZE
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    if col_prev.button("← Anterior", disabled=page == 0):
        st.session_state["feed_page"] = page - 1
        st.rerun()
    col_info.markdown(
        f"<div style='text-align:center' class='muted'>Página {page + 1} de {last_page + 1}</div>",
        unsafe_allow_html=True,
    )
    if col_next.button("Próxima →", disabled=page >= last_page):
        st.session_state["feed_page"] = page + 1
        st.rerun()


def render_media(services, post) -> None:
    for item in post["media"]:
        content, error = _load_media(services.media, item["id"])
        if error:
            st.error(f"Não foi possível carregar {item['filename']}: {error}")
        elif content is None:
            st.caption(f"Arquivo indisponível: {item['filename']}")
        elif item["content_type"].startswith("image/"):
            if item["content_type"] == "image/svg+xml":
                st.image(content.decode("utf-8"), caption=item["filename"])
            else:
                st.image(content, caption=item["filename"])
        elif item["content_type"].startswith("video/"):
            st.video(content, format=item["content_type"])
        else:
            st.download_button(
                f"📎 {item['filename']}",
                content,
                file_name=item["filename"],
                mime=item["content_type"],
                key=f"dl_{post['id']}_{item['id']}",
            )


@st.cache_data(show_spinner=False, max_entries=32)
def _load_media(_media_controller, media_id):
    result = _media_controller.get_by_id(media_id)
    if result.status:
        return result.data["content"], None
    if result.message == "Mídia não encontrada.":
        return None, None
    return None, result.message or "Erro desconhecido."


def render_post_form(services, user) -> None:
    with st.form("new_post_form", clear_on_submit=True):
        text = st.text_area(
            "Compartilhe algo com a comunidade de TI",
            max_chars=MAX_TEXT,
            placeholder="Uma dica, dúvida, projeto, vaga ou artigo... (Markdown permitido)",
        )
        col_category, col_tags = st.columns([1, 2])
        category = col_category.selectbox("Categoria", CATEGORIES)
        tags = col_tags.text_input("Tags (até 5, separadas por vírgula)", placeholder="python, docker, c#")
        with st.expander("Adicionar trecho de código"):
            code_language = st.selectbox("Linguagem", CODE_LANGUAGES)
            code = st.text_area("Código", height=140)
        files = st.file_uploader(
            "Mídia (opcional)", type=UPLOAD_TYPES, accept_multiple_files=True, help=UPLOAD_HELP
        )
        submitted = st.form_submit_button("Publicar", type="primary")

    if submitted:
        result = services.posts.create(
            user["usuario_id"],
            {"text": text, "category": category, "tags": tags, "code": code, "code_language": code_language},
            to_media_files(files),
        )
        if result.status:
            st.session_state["feed_page"] = 0
            set_flash("success", "Publicação criada!")
            st.rerun()
        st.error(result.message)


def render_post_card(
    services,
    post,
    user,
    connection_controller,
    connected_ids,
    pending,
) -> None:
    editing_key = f"editing_{post['id']}"
    is_owner = user is not None and post["author"]["id"] == user["usuario_id"]

    with st.container(border=True, key=f"post_card_{post['id']}"):
        _render_post_header(post)
        if is_owner and st.session_state.get(editing_key):
            _render_edit_form(services, post, user, editing_key)
        else:
            _render_post_body(services, post)
            if is_owner:
                _render_owner_actions(services, post, user, editing_key)
        _render_social_actions(
            services,
            post,
            user,
            connection_controller,
            connected_ids,
            pending,
        )
        render_comments(services, post, user)


def _render_social_actions(
    services,
    post,
    user,
    connection_controller,
    connected_ids,
    pending,
):
    response = services.likes.get_by_post_id(post["id"])
    likes = response.data if response.status else []
    if not response.status:
        st.warning(response.message)

    if user is None:
        st.caption(f"💖 {len(likes)} curtidas")
        return

    user_id = str(user["usuario_id"])
    liked = any(str(item["user_id"]) == user_id for item in likes)
    like_col, connection_col = st.columns([1, 2])
    label = "💖 Curtido" if liked else "🤍 Curtir"
    if like_col.button(label, key=f"like_{post['id']}"):
        result = (
            services.likes.delete_user_like(user_id, post["id"])
            if liked
            else services.likes.create(user_id, post["id"])
        )
        if result.status:
            st.rerun()
        st.error(result.message)

    with connection_col:
        _render_connection_action(
            connection_controller,
            post,
            user,
            connected_ids,
            pending,
        )
    st.caption(f"{len(likes)} curtidas")


def _render_post_header(post) -> None:
    author = post["author"]
    edited = " · editado" if post["updated_at"] else ""
    render_profile_identity(
        author["id"],
        author["name"],
        key=f"post_author_{post['id']}",
        caption=author["headline"] or None,
    )
    st.markdown(
        f"<span class='pill'>{html.escape(post['category'])}</span> "
        f"<span class='muted'>{format_datetime(post['created_at'])}{edited}</span>",
        unsafe_allow_html=True,
    )


def _render_post_body(services, post) -> None:
    st.markdown(post["text"])
    if post["code"]:
        st.code(post["code"], language=post["code_language"])
    if post["tags"]:
        st.caption(" ".join(f"`#{tag}`" for tag in post["tags"]))
    render_media(services, post)


def _render_owner_actions(services, post, user, editing_key) -> None:
    col_edit, col_delete, _ = st.columns([1, 1, 4])
    if col_edit.button("✏️ Editar", key=f"edit_{post['id']}"):
        st.session_state[editing_key] = True
        st.rerun()
    with col_delete.popover("🗑️ Excluir"):
        st.write("Excluir esta publicação e seus comentários?")
        if st.button("Confirmar exclusão", type="primary", key=f"confirm_delete_{post['id']}"):
            result = services.posts.delete(user["usuario_id"], post["id"])
            set_flash(
                "success" if result.status else "error",
                "Publicação excluída." if result.status else result.message,
            )
            st.rerun()


def _render_edit_form(services, post, user, editing_key) -> None:
    with st.form(f"edit_form_{post['id']}"):
        text = st.text_area("Texto", value=post["text"], max_chars=MAX_TEXT)
        col_category, col_tags = st.columns([1, 2])
        category = col_category.selectbox(
            "Categoria",
            CATEGORIES,
            index=CATEGORIES.index(post["category"]) if post["category"] in CATEGORIES else 0,
        )
        tags = col_tags.text_input("Tags", value=", ".join(post["tags"]))
        language = st.selectbox(
            "Linguagem do código",
            CODE_LANGUAGES,
            index=CODE_LANGUAGES.index(post["code_language"]) if post["code_language"] in CODE_LANGUAGES else 0,
        )
        code = st.text_area("Código", value=post["code"] or "", height=140)
        remove_ids = [
            item["id"]
            for item in post["media"]
            if st.checkbox(f"Remover {item['filename']}", key=f"rm_{post['id']}_{item['id']}")
        ]
        new_files = st.file_uploader(
            "Adicionar mídia",
            type=UPLOAD_TYPES,
            accept_multiple_files=True,
            help=UPLOAD_HELP,
            key=f"up_{post['id']}",
        )
        col_save, col_cancel, _ = st.columns([1, 1, 4])
        save = col_save.form_submit_button("Salvar", type="primary")
        cancel = col_cancel.form_submit_button("Cancelar")

    if cancel:
        st.session_state.pop(editing_key, None)
        st.rerun()
    if save:
        result = services.posts.update(
            user["usuario_id"],
            post["id"],
            {
                "text": text,
                "category": category,
                "tags": tags,
                "code": code,
                "code_language": language,
                "remove_media_ids": remove_ids,
            },
            to_media_files(new_files),
        )
        if result.status:
            st.session_state.pop(editing_key, None)
            set_flash("success", "Publicação atualizada.")
            st.rerun()
        st.error(result.message)


@st.cache_resource
def get_feed_services():
    database = get_mongo_database()
    redis = get_redis_client()
    user_repository = UserRepository(database)
    post_repository = PostRepository(database)
    comment_repository = CommentRepository(database)
    notification_repository = NotificationRepository(database, redis)
    notification_service = NotificationService(notification_repository)
    media_service = MediaService(MediaRepository(database))
    return SimpleNamespace(
        users=user_repository,
        posts=PostController(
            PostService(post_repository, user_repository, comment_repository, media_service)
        ),
        comments=CommentController(
            CommentService(
                comment_repository,
                post_repository,
                user_repository,
                notification_service=notification_service,
            )
        ),
        likes=LikeController(
            LikeService(
                LikeRepository(database),
                post_repository,
                user_repository,
                notification_service=notification_service,
            )
        ),
        media=MediaController(media_service),
    )


@st.cache_resource
def get_connection_controller():
    database = get_mongo_database()
    return ConnectionController(
        ConnectionService(
            ConnectionRepository(get_neo4j_session),
            ProfessionalRepository(database),
            NotificationRepository(database, get_redis_client()),
        )
    )


def current_user():
    session_id = get_cookie_controller().get(COOKIE_NAME)
    if not session_id:
        return None
    sessions, users, _ = build_runtime()
    result = sessions.get_current_user({"session_id": session_id})
    if not result.status:
        return None
    try:
        return users.get_by_id(result.data, result.data)
    except NotFoundError:
        return None


def render_page():
    render_sidebar()
    assets = Path(__file__).parents[1] / "assets"
    st.html(assets / "shared" / "page_theme.css")
    st.html(assets / "style.css")

    with st.container(key="feed_shell"):
        show_flash()
        user = current_user()
        services = get_feed_services()
        connection_controller = get_connection_controller() if user else None
        if user:
            with st.container(key="feed_composer"):
                render_post_form(services, user)
        render_feed(services, user, connection_controller)


if __name__ == "__main__":
    st.set_page_config(page_title="Home", page_icon="💻", layout="wide")
    render_page()
