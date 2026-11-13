# Testes da apresentação de imagens e da identificação clicável dos autores no feed.
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from pages.Feed import _render_post_header, render_media


SVG_CONTENT = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'


# Verifica se o SVG de exemplo é enviado ao componente de imagem do Streamlit.
def test_feed_renders_seed_svg_with_streamlit_image() -> None:
    media_controller = Mock()
    media_controller.get_by_id.return_value = SimpleNamespace(
        status=True,
        data={"content": SVG_CONTENT},
    )
    services = SimpleNamespace(media=media_controller)
    media_id = str(uuid4())
    post = {
        "id": str(uuid4()),
        "media": [
            {
                "id": media_id,
                "filename": "post-placeholder.svg",
                "content_type": "image/svg+xml",
            }
        ],
    }

    with patch("pages.Feed.st.image") as image:
        render_media(services, post)

    image.assert_called_once_with(
        SVG_CONTENT.decode("utf-8"),
        caption="post-placeholder.svg",
    )


# Confere o uso do componente que permite abrir o perfil do autor.
def test_feed_author_uses_clickable_profile_identity() -> None:
    post = {
        "id": "post-1",
        "author": {
            "id": "user-1",
            "name": "Ana",
            "headline": "Desenvolvedora",
        },
        "updated_at": None,
        "category": "Projeto",
        "created_at": None,
    }

    with (
        patch("pages.Feed.render_profile_identity") as profile_identity,
        patch("pages.Feed.st.markdown"),
        patch("pages.Feed.format_datetime", return_value="13/11/2026 11:00"),
    ):
        _render_post_header(post)

    profile_identity.assert_called_once_with(
        "user-1",
        "Ana",
        key="post_author_post-1",
        caption="Desenvolvedora",
    )
