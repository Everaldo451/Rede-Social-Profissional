import streamlit as st

from components.shared.sidebar import render_sidebar

st.set_page_config(page_title="Home", layout="wide")
render_sidebar()
st.title("Rede Social Profissional")
st.write("Aplicação inicial pronta para desenvolvimento.")
