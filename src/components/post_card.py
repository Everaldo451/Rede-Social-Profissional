import html

import streamlit as st

from components.comments import render_comments
from components.media_view import render_media
from components.shared.flash import set_flash
from components.shared.formatting import format_datetime
from components.shared.uploads import UPLOAD_HELP, UPLOAD_TYPES, to_media_files
from dto.posts.request.post_requests import CATEGORIES, CODE_LANGUAGES, MAX_TEXT


def render_post_card(container, post, user) -> None:
    """RF011 - Card de uma publicação do feed (conteúdo, autor e data)."""
    editing_key = f"editing_{post['id']}"
    is_owner = post["author"]["id"] == user["id"]

    with st.container(border=True):
        _render_header(post)
        if is_owner and st.session_state.get(editing_key):
            _render_edit_form(container, post, user, editing_key)
        else:
            _render_body(container, post)
            if is_owner:
                _render_owner_actions(container, post, user, editing_key)
        render_comments(container, post, user)


def _render_header(post) -> None:
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


def _render_body(container, post) -> None:
    st.markdown(post["text"])
    if post["code"]:
        st.code(post["code"], language=post["code_language"])
    if post["tags"]:
        st.caption(" ".join(f"`#{tag}`" for tag in post["tags"]))
    render_media(container, post)


def _render_owner_actions(container, post, user, editing_key) -> None:
    """RF010 - Editar e excluir (somente o proprietário)."""
    col_edit, col_delete, _ = st.columns([1, 1, 4])
    if col_edit.button("✏️ Editar", key=f"edit_{post['id']}"):
        st.session_state[editing_key] = True
        st.rerun()
    with col_delete.popover("🗑️ Excluir"):
        st.write("Excluir esta publicação e seus comentários?")
        if st.button("Confirmar exclusão", type="primary", key=f"confirm_delete_{post['id']}"):
            result = container.posts.delete(user["id"], post["id"])
            set_flash("success" if result.status else "error", "Publicação excluída." if result.status else result.message)
            st.rerun()


def _render_edit_form(container, post, user, editing_key) -> None:
    with st.form(f"edit_form_{post['id']}"):
        text = st.text_area("Texto", value=post["text"], max_chars=MAX_TEXT)
        col_category, col_tags = st.columns([1, 2])
        category = col_category.selectbox(
            "Categoria", CATEGORIES, index=CATEGORIES.index(post["category"]) if post["category"] in CATEGORIES else 0
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
            "Adicionar mídia", type=UPLOAD_TYPES, accept_multiple_files=True,
            help=UPLOAD_HELP, key=f"up_{post['id']}",
        )
        col_save, col_cancel, _ = st.columns([1, 1, 4])
        save = col_save.form_submit_button("Salvar", type="primary")
        cancel = col_cancel.form_submit_button("Cancelar")

    if cancel:
        st.session_state.pop(editing_key, None)
        st.rerun()
    if save:
        result = container.posts.update(
            user["id"],
            post["id"],
            {
                "text": text, "category": category, "tags": tags, "code": code,
                "code_language": language, "remove_media_ids": remove_ids,
            },
            to_media_files(new_files),
        )
        if result.status:
            st.session_state.pop(editing_key, None)
            set_flash("success", "Publicação atualizada.")
            st.rerun()
        st.error(result.message)
