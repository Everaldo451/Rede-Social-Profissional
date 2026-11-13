import streamlit as st

st.set_page_config(page_title="Home", layout="wide")

from pages.Feed import render_page

render_page()
