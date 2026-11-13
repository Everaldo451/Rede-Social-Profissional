# Reúne a foto e o nome clicável que identificam um profissional nas telas.
from pathlib import Path

import streamlit as st

from controllers.shared.media_controller import MediaController
from repositories.shared.media_repository import MediaRepository
from services.shared.media_service import MediaService

DEFAULT_PROFILE_IMAGE = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "profile"
    / "default_profile.svg"
)


# Reutiliza a cadeia de controller, serviço e repositório de mídias.
@st.cache_resource
def _media_controller():
    return MediaController(MediaService(MediaRepository()))


# Consulta a foto pública e mantém o resultado em cache por cinco minutos.
@st.cache_data(ttl=300, show_spinner=False)
def _profile_media(user_id):
    response = _media_controller().get_one(
        {
            "proprietario_id": user_id,
            "proprietario_tipo": "usuario",
            "tipo": "imagem_perfil",
            "visibilidade": "publica",
        }
    )
    if response.status:
        return (
            response.data["content"],
            response.data["metadata"].get("tipo_mime"),
            None,
        )
    if response.message == "Mídia não encontrada.":
        return None, None, None
    return None, None, response.message


# Invalida o cache das fotos para que a próxima leitura busque os dados atuais.
def clear_profile_media_cache():
    _profile_media.clear()


# Decodifica SVG como texto e entrega a imagem ao componente do Streamlit.
def render_profile_image(container, content, mime_type, size=150):
    if mime_type == "image/svg+xml":
        content = content.decode("utf-8")
    container.image(content, width=size)


# Exibe foto, nome e legenda, permitindo abrir o perfil pelo botão do nome.
def render_profile_identity(user_id, name, key, caption=None):
    user_id = str(user_id)
    photo, details = st.columns([1, 5], vertical_alignment="center")
    content, mime_type, media_error = _profile_media(user_id)
    # Usa o avatar padrão quando não há foto disponível para esse usuário.
    if content is None:
        render_profile_image(
            photo,
            DEFAULT_PROFILE_IMAGE.read_bytes(),
            "image/svg+xml",
            size=48,
        )
        if media_error:
            photo.caption("Foto indisponível.")
    else:
        render_profile_image(photo, content, mime_type, size=48)

    if name == "Profissional indisponível":
        details.markdown(f"**{name}**")
    elif details.button(
        name,
        key=f"profile_link_{key}",
        type="tertiary",
        width="content",
    ):
        st.switch_page(
            "pages/Profile.py",
            query_params={"user_id": user_id},
        )
    if caption:
        details.caption(caption)
