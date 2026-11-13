import html
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import streamlit as st

st.set_page_config(page_title="Publicações", page_icon="💻", layout="wide")

from streamlit_cookies_controller import CookieController

from components.shared.header import render_header
from controllers.posts.comment_controller import CommentController
from controllers.posts.post_controller import PostController
from controllers.profile.user_controller import UserController
from controllers.shared.media_controller import MediaController
from controllers.sessions.session_controller import SessionController
from database.mongo import get_mongo_database
from database.redis import get_redis_client
from dto.posts.request.post_requests import (
    CATEGORIES,
    CODE_LANGUAGES,
    MAX_COMMENT,
    MAX_TEXT,
)
from repositories.posts.comment_repository import CommentRepository
from repositories.posts.post_repository import PostRepository
from repositories.profile.user_repository import UserRepository
from repositories.sessions.session_repository import SessionRepository
from repositories.shared.media_repository import MediaRepository
from services.posts.comment_service import CommentService
from services.posts.post_service import PostService
from services.profile.user_service import UserService
from services.sessions.session_service import SessionService
from services.shared.media_service import MediaService

_FLASH_KEY = "flash_message"
BRT = timezone(timedelta(hours=-3))
PAGE_SIZE = 10
UPLOAD_TYPES = ["png", "jpg", "jpeg", "gif", "webp", "mp4", "webm", "pdf"]
UPLOAD_HELP = "Imagens, vídeos (MP4/WEBM) ou PDF — até 4 arquivos de 10 MB."


@dataclass(frozen=True)
class MediaFile:
    filename: str
    content_type: str
    data: bytes


st.markdown(
    f"<style>{(Path(__file__).parents[1] / 'assets' / 'style.css').read_text()}</style>",
    unsafe_allow_html=True,
)


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


def render_auth(services, cookies) -> None:
    render_header()
    st.write("")
    show_flash()
    login_tab, register_tab = st.tabs(["Entrar", "Criar conta"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("E-mail")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", type="primary")
        if submitted:
            result = services.sessions.login({"email": email, "password": password})
            if result.status:
                st.session_state["token"] = result.data["token"]
                cookies.set("session_token", result.data["token"])
                st.rerun()
            st.error(result.message)

    with register_tab:
        with st.form("register_form"):
            name = st.text_input("Nome completo")
            headline = st.text_input("Cargo ou área (ex.: Dev Backend Python)")
            email = st.text_input("E-mail", key="register_email")
            password = st.text_input("Senha (mín. 8 caracteres)", type="password", key="register_password")
            submitted = st.form_submit_button("Criar conta", type="primary")
        if submitted:
            result = services.users.create(
                {"name": name, "headline": headline, "email": email, "password": password}
            )
            if result.status:
                set_flash("success", "Conta criada! Entre com seu e-mail e senha.")
                st.rerun()
            st.error(result.message)


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

        if post["author"]["id"] == user["id"]:
            st.caption("Você é o autor desta publicação; apenas outros usuários podem comentá-la.")
            return

        with st.form(f"comment_form_{post['id']}", clear_on_submit=True):
            text = st.text_input("Escreva um comentário", max_chars=MAX_COMMENT)
            submitted = st.form_submit_button("Comentar")
        if submitted:
            result = services.comments.create(user["id"], post["id"], {"text": text})
            if result.status:
                set_flash("success", "Comentário publicado.")
                st.rerun()
            st.error(result.message)


def render_feed(services, user, filters) -> None:
    page = st.session_state.get("feed_page", 0)
    result = services.posts.get_paginated(page * PAGE_SIZE, PAGE_SIZE, filters)
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

    st.caption(f"{total} publicação(ões)")
    for post in items:
        render_post_card(services, post, user)

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
        media = _load_media(services, item["id"])
        if media is None:
            st.caption(f"Arquivo indisponível: {item['filename']}")
        elif item["content_type"].startswith("image/"):
            st.image(media["data"], caption=item["filename"])
        elif item["content_type"].startswith("video/"):
            st.video(media["data"], format=item["content_type"])
        else:
            st.download_button(
                f"📎 {item['filename']}",
                media["data"],
                file_name=item["filename"],
                mime=item["content_type"],
                key=f"dl_{post['id']}_{item['id']}",
            )


@st.cache_data(show_spinner=False, max_entries=32)
def _load_media(_services, file_id):
    result = _services.media.get_by_id(file_id)
    return result.data if result.status else None


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
            user["id"],
            {"text": text, "category": category, "tags": tags, "code": code, "code_language": code_language},
            to_media_files(files),
        )
        if result.status:
            st.session_state["feed_page"] = 0
            set_flash("success", "Publicação criada!")
            st.rerun()
        st.error(result.message)


def render_post_card(services, post, user) -> None:
    editing_key = f"editing_{post['id']}"
    is_owner = post["author"]["id"] == user["id"]

    with st.container(border=True):
        _render_post_header(post)
        if is_owner and st.session_state.get(editing_key):
            _render_edit_form(services, post, user, editing_key)
        else:
            _render_post_body(services, post)
            if is_owner:
                _render_owner_actions(services, post, user, editing_key)
        render_comments(services, post, user)


def _render_post_header(post) -> None:
    author = post["author"]
    edited = " · editado" if post["updated_at"] else ""
    headline = f" · {html.escape(author['headline'])}" if author["headline"] else ""
    st.markdown(
        f"<span class='author'>{html.escape(author['name'])}</span>"
        f"<span class='muted'>{headline}</span> "
        f"<span class='pill'>{html.escape(post['category'])}</span><br>"
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
            result = services.posts.delete(user["id"], post["id"])
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
            user["id"],
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
    user_service = UserService(user_repository)
    session_service = SessionService(SessionRepository(redis), user_service)
    media_service = MediaService(MediaRepository(database))
    return SimpleNamespace(
        users=UserController(user_service),
        sessions=SessionController(session_service),
        posts=PostController(
            PostService(post_repository, user_repository, comment_repository, media_service)
        ),
        comments=CommentController(
            CommentService(comment_repository, post_repository, user_repository)
        ),
        media=MediaController(media_service),
    )


def current_user(services, cookies):
    token = st.session_state.get("token") or cookies.get("session_token")
    if token:
        st.session_state["token"] = token
    result = services.sessions.resolve(token) if token else None
    if result is None or not result.status or not result.data:
        st.session_state.pop("token", None)
        return None
    return result.data


services = get_feed_services()
cookies = CookieController()
user = current_user(services, cookies)
if user is None:
    render_auth(services, cookies)
    st.stop()

render_header()
show_flash()
st.subheader("Publicações")
render_post_form(services, user)
with st.expander("Filtrar publicações"):
    category = st.selectbox("Categoria", ["Todas", *CATEGORIES])
    tag = st.text_input("Tag")
filters = {}
if category != "Todas":
    filters["category"] = category
if tag.strip():
    filters["tag"] = tag.strip().lower()
render_feed(services, user, filters or None)
