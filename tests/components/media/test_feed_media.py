from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from pages.Feed import render_media


SVG_CONTENT = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'


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
