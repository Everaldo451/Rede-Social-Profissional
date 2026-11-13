from unittest.mock import Mock

from components.shared.profile_identity import render_profile_image


def test_svg_profile_image_is_rendered_by_streamlit_as_an_svg_string():
    container = Mock()

    render_profile_image(container, b"<svg></svg>", "image/svg+xml", size=48)

    container.image.assert_called_once_with("<svg></svg>", width=48)
