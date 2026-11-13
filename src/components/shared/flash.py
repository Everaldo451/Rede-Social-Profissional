import streamlit as st

_KEY = "flash_message"


def set_flash(kind: str, message: str) -> None:
    """Guarda uma mensagem para ser exibida após o próximo rerun."""
    st.session_state[_KEY] = (kind, message)


def show_flash() -> None:
    flash = st.session_state.pop(_KEY, None)
    if flash:
        kind, message = flash
        {"success": st.success, "error": st.error}.get(kind, st.info)(message)
