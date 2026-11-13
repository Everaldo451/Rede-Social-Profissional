import streamlit as st


def render_media(container, post) -> None:
    """Exibe as mídias de uma publicação (imagem, vídeo ou arquivo para baixar)."""
    for item in post["media"]:
        media = _load(container, item["id"])
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
def _load(_container, file_id):
    # `_container` (com underscore) não entra no hash do cache; arquivos são imutáveis.
    result = _container.media.get(file_id)
    return result.data if result.status else None
