# Componente de título reutilizável nas telas da aplicação.
import streamlit as st


# Exibe o nome da rede social no topo da área principal.
def render_header() -> None:
    st.title("Rede Social Profissional")
