# Tela de busca e recomendação de mentores, consulta de perfis e resposta de solicitações.
import logging
from pathlib import Path

import streamlit as st
from neo4j.exceptions import DriverError, Neo4jError
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from components.shared.sidebar import render_sidebar
from components.shared.profile_identity import render_profile_identity
from controllers.connections.mentorship_controller import MentorshipController
from repositories.connections.mentorship_repository import MentorshipRepository
from repositories.connections.professional_repository import ProfessionalRepository
from repositories.notifications.notification_repository import NotificationRepository
from services.connections.mentorship_service import MentorshipService

logger = logging.getLogger(__name__)
THEME = Path(__file__).resolve().parents[1] / "assets" / "shared" / "page_theme.css"
PAGE_SIZE = 6


# Apresenta os filtros de nome e habilidade para a busca de mentores.
def _search_fields(skills, key, label="Nome do mentor"):
    skill_names = {str(skill["_id"]): skill["nome"] for skill in skills}
    name = st.text_input(label, max_chars=100, key=f"{key}_name")
    skill_id = st.selectbox(
        "Habilidade",
        list(skill_names),
        index=None,
        placeholder="Todas as habilidades",
        format_func=skill_names.__getitem__,
        key=f"{key}_skill",
    )
    return {"nome": name, "habilidade_id": skill_id}


# Inicializa ou recupera a listagem e busca a primeira página quando necessário.
def _load_mentor_page(controller, user_id, key, filters=None, *, reset=False):
    listing_key = f"mentor_listing_{key}"
    # Mantém no estado da sessão os resultados, a paginação e os erros de cada listagem.
    if reset or listing_key not in st.session_state:
        st.session_state[listing_key] = {
            "filters": filters or {"nome": "", "habilidade_id": None},
            "results": None,
            "has_more": False,
            "error": None,
        }

    listing = st.session_state[listing_key]
    if listing["results"] is None:
        if key == "recommendations":
            response = controller.recommend(user_id, 0, PAGE_SIZE + 1)
        else:
            response = controller.filter_mentors(
                user_id, listing["filters"], 0, PAGE_SIZE + 1
            )
        if not response.status:
            listing["results"] = []
            listing["error"] = response.message
        else:
            listing["results"] = response.data[:PAGE_SIZE]
            listing["has_more"] = len(response.data) > PAGE_SIZE
    return listing


# Busca a próxima página e acrescenta seus resultados ao estado da listagem.
def _load_more_mentors(controller, user_id, key):
    listing = st.session_state[f"mentor_listing_{key}"]
    offset = len(listing["results"])
    if key == "recommendations":
        response = controller.recommend(user_id, offset, PAGE_SIZE + 1)
    else:
        response = controller.filter_mentors(
            user_id, listing["filters"], offset, PAGE_SIZE + 1
        )
    if not response.status:
        st.error(response.message)
        return
    listing["results"].extend(response.data[:PAGE_SIZE])
    listing["has_more"] = len(response.data) > PAGE_SIZE
    st.rerun()


# Apresenta os dados profissionais, as habilidades e o histórico do mentor selecionado.
def _render_profile(profile, user_id):
    st.subheader("Perfil profissional")
    render_profile_identity(
        user_id,
        profile["nome"],
        f"mentor_details_{user_id}",
        " · ".join(
            profile[field]
            for field in ("headline", "localizacao", "nivel_carreira")
            if profile.get(field)
        )
        or None,
    )
    if profile.get("aceita_mentoria"):
        st.success("Disponível para mentoria")

    with st.expander("Habilidades", expanded=True):
        if not profile.get("habilidades"):
            st.caption("Nenhuma habilidade cadastrada.")
        for skill in profile.get("habilidades") or []:
            experience = skill.get("anos_experiencia")
            details = [skill["nome"], skill.get("nivel")]
            if experience is not None:
                details.append(f"{experience} ano(s) de experiência")
            st.text(" · ".join(detail for detail in details if detail))

    sections = (
        ("Experiência profissional", "experiencias", "cargo", "descricao"),
        ("Formação acadêmica", "formacao", "curso", "grau"),
        ("Certificações", "certificacoes", "nome", "url"),
    )
    for label, field, title_field, detail_field in sections:
        with st.expander(label):
            entries = profile.get(field) or []
            if not entries:
                st.caption("Nenhum registro cadastrado.")
            for entry in entries:
                st.text(
                    " · ".join(
                        value
                        for value in (
                            entry.get(title_field),
                            entry.get("organizacao"),
                        )
                        if value
                    )
                )
                if entry.get(detail_field):
                    st.caption(entry[detail_field])


# Organiza busca, recomendações, pedidos recebidos e criação de novas solicitações.
def _render_mentors(controller, user_id, users):
    section = st.radio(
        "Seção de mentoria",
        ("Buscar mentores", "Recomendações", "Solicitações"),
        horizontal=True,
        key="mentorship_section",
    )
    # A seção de solicitações reúne os pedidos que o mentor pode responder.
    if section == "Solicitações":
        response = controller.list_requests(user_id)
        if not response.status:
            st.warning(response.message)
            return
        incoming = [
            item
            for item in response.data
            if item["recebida"] and item["status"] == "solicitado"
        ]
        if not incoming:
            st.info("Você não tem solicitações de mentoria pendentes.")
        for item in incoming:
            with st.container(border=True):
                render_profile_identity(
                    item["mentorado_id"],
                    item["nome"],
                    f"mentorship_request_{item['_id']}",
                    f"Habilidade: {item['habilidade_nome']}",
                )
                accept, decline = st.columns(2)
                action = None
                if accept.button("Aceitar", key=f"accept_mentorship_{item['_id']}"):
                    action = "aceitar"
                if decline.button("Recusar", key=f"decline_mentorship_{item['_id']}"):
                    action = "recusar"
                if action:
                    result = controller.update(user_id, item["_id"], {"acao": action})
                    if result.status:
                        st.session_state["mentorship_feedback"] = (
                            "Solicitação de mentoria "
                            f"{'aceita' if action == 'aceitar' else 'recusada'}."
                        )
                        st.rerun()
                    st.warning(result.message)
        return

    if section == "Buscar mentores":
        with st.form("mentor_search_form", border=False):
            filters = _search_fields(users.list_skills(), "mentors")
            submitted = st.form_submit_button("Pesquisar mentores", type="primary")
        listing = _load_mentor_page(
            controller,
            user_id,
            "search",
            filters,
            reset=submitted,
        )
        listing_key = "search"
    else:
        desired = controller.desired_skills(user_id).data
        # As recomendações dependem das habilidades que o usuário indicou que deseja desenvolver.
        if not desired:
            st.info(
                "O perfil ainda não tem habilidades desejadas para gerar recomendações."
            )
            return
        st.text("Habilidades desejadas: " + ", ".join(desired))
        listing = _load_mentor_page(controller, user_id, "recommendations")
        listing_key = "recommendations"

    if listing["error"]:
        st.warning(listing["error"])
        return
    if not listing["results"]:
        st.info("Nenhum mentor disponível para esses critérios.")
        return

    mentors = {row["id"]: row for row in listing["results"]}
    skill_names = {
        str(skill["_id"]): skill["nome"]
        for skill in users.list_skills()
    }
    st.caption(f"Exibindo {len(listing['results'])} mentores")
    for row in listing["results"]:
        with st.container(border=True):
            render_profile_identity(
                row["id"],
                row["perfil"]["nome"],
                f"mentor_result_{row['id']}",
                row["perfil"].get("headline") or "Perfil profissional",
            )
            skills = row.get("habilidades") or []
            if skills:
                st.caption("Habilidades compatíveis: " + ", ".join(skills))
    if listing["has_more"] and st.button(
        "Carregar mais mentores", key=f"load_more_{listing_key}"
    ):
        _load_more_mentors(controller, user_id, listing_key)

    mentor_id = st.selectbox(
        "Consultar perfil de mentor",
        list(mentors),
        index=None,
        placeholder="Selecione um mentor",
        format_func=lambda item: mentors[item]["perfil"]["nome"],
        key=f"mentor_profile_{section}",
    )
    if mentor_id:
        response = controller.get_by_user_id(mentor_id)
        if response.status:
            _render_profile(response.data, mentor_id)
        else:
            st.warning(response.message)
        mentor_skills = {
            skill_id: skill_names[skill_id]
            for skill_id in mentors[mentor_id].get("habilidade_ids", [])
            if skill_id in skill_names
        }
        # A solicitação precisa indicar uma das habilidades ensinadas pelo mentor selecionado.
        if mentor_skills:
            skill_id = st.selectbox(
                "Habilidade para a mentoria",
                list(mentor_skills),
                format_func=mentor_skills.__getitem__,
                key=f"mentorship_skill_{mentor_id}",
            )
            if st.button(
                "Solicitar mentoria", key=f"request_mentorship_{mentor_id}"
            ):
                result = controller.create(
                    user_id,
                    {"mentor_id": mentor_id, "habilidade_id": skill_id},
                )
                if result.status:
                    st.session_state["mentorship_feedback"] = (
                        "Solicitação de mentoria enviada."
                    )
                    st.rerun()
                st.warning(result.message)
        else:
            st.info("Este mentor não tem habilidades disponíveis para solicitação.")


# Exige autenticação para utilizar as funcionalidades de mentoria.
def _current_user_id():
    from pages.Sessoes import get_authenticated_user_id

    user_id = get_authenticated_user_id()
    if not user_id:
        st.info("Entre na sua conta para acessar a mentoria.")
        st.page_link("pages/Login.py", label="Ir para o login")
        st.stop()
    return user_id


# Prepara o tema, a sessão e as dependências da página de mentoria.
def main():
    st.set_page_config(page_title="Mentoria", layout="wide")
    render_sidebar()
    st.html(THEME)
    user_id = _current_user_id()

    from database import get_mongo_database, get_neo4j_session

    database = get_mongo_database()
    users = ProfessionalRepository(database)
    controller = MentorshipController(
        MentorshipService(
            MentorshipRepository(get_neo4j_session, database),
            users,
            NotificationRepository(),
        )
    )
    with st.container(key="mentorship_shell"):
        st.title("Mentoria")
        st.caption(
            "Encontre profissionais experientes para apoiar seu desenvolvimento."
        )
        feedback = st.session_state.pop("mentorship_feedback", None)
        if feedback:
            st.success(feedback)
        try:
            _render_mentors(controller, user_id, users)
        except (PyMongoError, Neo4jError, DriverError, RedisError):
            logger.exception("Falha ao carregar a página de mentoria.")
            st.error("Não foi possível acessar os dados de mentoria. Tente novamente.")


if __name__ == "__main__":
    main()
