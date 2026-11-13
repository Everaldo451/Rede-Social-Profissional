import streamlit as st


def render_sidebar() -> None:
    st.sidebar.title("Rede Social")
    st.sidebar.page_link("pages/Feed.py", label="Publicações")
