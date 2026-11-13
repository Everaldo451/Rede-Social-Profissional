import streamlit as st

from components.shared.flash import set_flash
from components.shared.uploads import UPLOAD_HELP, UPLOAD_TYPES, to_media_files
from dto.posts.request.post_requests import CATEGORIES, CODE_LANGUAGES, MAX_TEXT


def render_post_form(container, user) -> None:
    """RF009 - Criar publicação (texto e, opcionalmente, mídia)."""
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
        result = container.posts.create(
            user["id"],
            {"text": text, "category": category, "tags": tags, "code": code, "code_language": code_language},
            to_media_files(files),
        )
        if result.status:
            st.session_state["feed_page"] = 0
            set_flash("success", "Publicação criada!")
            st.rerun()
        st.error(result.message)
