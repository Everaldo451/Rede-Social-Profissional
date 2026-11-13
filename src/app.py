# Ponto de entrada da aplicação Streamlit: configura a página e apresenta o feed.
import streamlit as st

# Define o título da aba e aproveita a largura disponível da janela.
st.set_page_config(page_title="Home", layout="wide")

from pages.Feed import render_page

# Delega a montagem da tela inicial à função de apresentação do feed.
render_page()
