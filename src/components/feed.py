import streamlit as st

from components.post_card import render_post_card

PAGE_SIZE = 10


def render_feed(container, user, filters) -> None:
    """RF011 - Consultar feed (mais recentes primeiro, paginado)."""
    page = st.session_state.get("feed_page", 0)
    result = container.posts.get_paginated(page * PAGE_SIZE, PAGE_SIZE, filters)
    if not result.status:
        st.error(result.message)
        return

    items, total = result.data["items"], result.data["total"]
    if not items and page > 0:  # página ficou vazia após exclusões
        st.session_state["feed_page"] = max(0, (total - 1) // PAGE_SIZE)
        st.rerun()
    if not items:
        st.info("Nenhuma publicação encontrada. Que tal publicar a primeira?")
        return

    st.caption(f"{total} publicação(ões)")
    for post in items:
        render_post_card(container, post, user)

    last_page = (total - 1) // PAGE_SIZE
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    if col_prev.button("← Anterior", disabled=page == 0):
        st.session_state["feed_page"] = page - 1
        st.rerun()
    col_info.markdown(f"<div style='text-align:center' class='muted'>Página {page + 1} de {last_page + 1}</div>", unsafe_allow_html=True)
    if col_next.button("Próxima →", disabled=page >= last_page):
        st.session_state["feed_page"] = page + 1
        st.rerun()
