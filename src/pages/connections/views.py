import streamlit as st


def _search_fields(skills, key, label="Nome do profissional"):
    skill_names = {str(skill["_id"]): skill["nome"] for skill in skills}
    name = st.text_input(label, max_chars=100, key=f"{key}_name")
    skill_id = st.selectbox(
        "Habilidade", list(skill_names), index=None, placeholder="Todas as habilidades",
        format_func=skill_names.__getitem__, key=f"{key}_skill",
    )
    return {"nome": name, "habilidade_id": skill_id}


def _professionals(controller, user_id, skills):
    filters = _search_fields(skills, "professionals")
    response = controller.search_professionals(user_id, filters)
    if not response.status:
        st.warning(response.message)
        return
    if not response.data:
        st.info("Nenhum profissional encontrado com esses filtros.")
        return
    for profile in response.data:
        other_id = str(profile["_id"])
        with st.container(border=True):
            st.text(profile["nome"])
            st.caption(profile.get("headline", ""))
            if st.button("Enviar solicitação", key=f"request_{other_id}"):
                sent = controller.request_connection(user_id, other_id)
                if sent.status:
                    st.success("Solicitação enviada.")
                else:
                    st.warning(sent.message)


def _requests(controller, user_id):
    response = controller.list_requests(user_id)
    if not response.status:
        st.warning(response.message)
        return
    for label, received in (("Recebidas", True), ("Enviadas", False)):
        st.subheader(label)
        requests = [row for row in response.data if row["recebida"] == received]
        if not requests:
            st.caption("Nenhuma solicitação.")
        for row in requests:
            with st.container(border=True):
                st.text(row["nome"])
                st.caption(f"Status: {row['status'].capitalize()}")
                if not received or row["status"] != "pendente":
                    continue
                accept, decline = st.columns(2)
                action = None
                if accept.button("Aceitar", key=f"accept_{row['id']}"):
                    action = "aceitar"
                if decline.button("Recusar", key=f"decline_{row['id']}"):
                    action = "recusar"
                if action:
                    decision = controller.update_connection_request(
                        user_id, row["remetente_id"],
                        {"solicitacao_id": row["id"], "acao": action},
                    )
                    if decision.status:
                        st.session_state["network_feedback"] = f"Solicitação {decision.data}."
                        st.rerun()
                    st.warning(decision.message)


def _connections(controller, user_id):
    total = controller.count_connections(user_id).data
    st.metric("Conexões diretas", total)
    if not total:
        st.info("Sua rede ainda não tem conexões.")
        return
    page_size = 10
    pages = (total + page_size - 1) // page_size
    page = st.number_input("Página", 1, pages, 1) if pages > 1 else 1
    response = controller.get_paginated_for_user(user_id, (page - 1) * page_size, page_size)
    for profile in response.data:
        with st.container(border=True):
            st.text(profile["nome"])
            st.caption(profile.get("headline", ""))


def _degrees(controller, user_id):
    st.subheader("Menor caminho entre profissionais")
    st.caption("O cálculo considera somente conexões aceitas.")
    name = st.text_input("Filtrar por nome", max_chars=100, key="path_name")
    response = controller.search_professionals(user_id, {"nome": name})
    people = {str(item["_id"]): item["nome"] for item in response.data}
    if not people:
        st.info("Nenhum profissional encontrado.")
        return
    target = st.selectbox(
        "Profissional de destino", list(people), index=None,
        placeholder="Selecione um profissional", format_func=people.__getitem__,
    )
    if st.button("Calcular menor caminho", disabled=target is None):
        path = controller.get_shortest_path(user_id, target)
        if not path.status:
            st.warning(path.message)
        elif path.data is None:
            st.info("Não há um caminho de conexões entre vocês.")
        else:
            st.metric("Graus de separação", path.data["graus"])
            st.text(" → ".join(path.data["nomes"]))


def render_network(controller, user_id, users):
    st.title("Rede de Conexões Profissionais")
    feedback = st.session_state.pop("network_feedback", None)
    if feedback:
        st.success(feedback)
    section = st.radio(
        "Seção da rede",
        ("Buscar profissionais", "Solicitações", "Minhas conexões", "Graus de separação"),
        horizontal=True,
    )
    if section == "Buscar profissionais":
        _professionals(controller, user_id, users.list_skills())
    elif section == "Solicitações":
        _requests(controller, user_id)
    elif section == "Minhas conexões":
        _connections(controller, user_id)
    else:
        _degrees(controller, user_id)


def render_profile(profile):
    st.subheader("Perfil profissional")
    st.text(profile["nome"])
    st.caption(" · ".join(
        profile[field] for field in ("headline", "localizacao", "nivel_carreira")
        if profile.get(field)
    ))
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
                st.text(" · ".join(
                    value for value in (entry.get(title_field), entry.get("organizacao"))
                    if value
                ))
                if entry.get(detail_field):
                    st.caption(entry[detail_field])


def render_mentors(controller, user_id, users):
    st.title("Mentoria")
    section = st.radio("Seção de mentoria", ("Buscar mentores", "Recomendações"), horizontal=True)
    if section == "Buscar mentores":
        response = controller.filter_mentors(
            user_id, _search_fields(users.list_skills(), "mentors", "Nome do mentor")
        )
    else:
        desired = controller.desired_skills(user_id).data
        if not desired:
            st.info("O perfil ainda não tem habilidades desejadas para gerar recomendações.")
            return
        st.text("Habilidades desejadas: " + ", ".join(desired))
        response = controller.recommend(user_id)

    if not response.status:
        st.warning(response.message)
        return
    if not response.data:
        st.info("Nenhum mentor disponível para esses critérios.")
        return

    mentors = {row["id"]: row for row in response.data}
    for row in response.data:
        with st.container(border=True):
            st.text(row["perfil"]["nome"])
            st.caption(row["perfil"].get("headline", ""))
            if row.get("habilidades"):
                st.text("Habilidades compatíveis: " + ", ".join(row["habilidades"]))
    mentor_id = st.selectbox(
        "Consultar perfil de mentor", list(mentors), index=None,
        placeholder="Selecione um mentor",
        format_func=lambda item: mentors[item]["perfil"]["nome"],
        key=f"mentor_profile_{section}",
    )
    if mentor_id:
        response = controller.get_by_user_id(mentor_id)
        if response.status:
            render_profile(response.data)
        else:
            st.warning(response.message)
