import streamlit as st

from components.shared.flash import set_flash
from components.shared.formatting import format_datetime
from dto.posts.request.post_requests import MAX_COMMENT


def render_comments(container, post, user) -> None:
    """RF012 - Lista e permite comentar publicações de outros usuários."""
    comments = post["comments"]
    with st.expander(f"💬 Comentários ({len(comments)})"):
        for comment in comments:
            st.markdown(f"**{comment['author']['name']}** · :gray[{format_datetime(comment['created_at'])}]")
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
            result = container.comments.create(user["id"], post["id"], {"text": text})
            if result.status:
                set_flash("success", "Comentário publicado.")
                st.rerun()
            st.error(result.message)
