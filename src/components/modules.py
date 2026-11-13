import streamlit as st
from components.shared.flash import set_flash


def render_profile(container, user):
    st.subheader("Meu perfil profissional")
    with st.form("profile_update_form"):
        name=st.text_input("Nome",value=user.get("name",""))
        headline=st.text_input("Cargo ou área",value=user.get("headline",""))
        location=st.text_input("Localização",value=user.get("location",""))
        bio=st.text_area("Sobre mim",value=user.get("bio",""),max_chars=1000)
        submitted=st.form_submit_button("Salvar perfil",type="primary")
    if submitted:
        result=container.users.update_profile(user["id"],{"name":name,"headline":headline,"location":location,"bio":bio})
        if result.status:
            set_flash("success","Perfil atualizado."); st.rerun()
        st.error(result.message)
    st.divider()
    st.markdown("**Habilidades cadastradas**")
    with st.expander("Cadastrar uma nova habilidade"):
        with st.form("create_skill_form"):
            skill_name=st.text_input("Nome da habilidade",placeholder="Ex.: Python")
            skill_category=st.text_input("Categoria",value="Tecnologia")
            create_skill=st.form_submit_button("Cadastrar habilidade")
        if create_skill:
            created=container.skills.create({"name":skill_name,"category":skill_category})
            if created.status: set_flash("success","Habilidade cadastrada."); st.rerun()
            st.error(created.message)
    skills=container.skills.get_paginated(0,100)
    if skills.status and skills.data:
        options={f"{item['name']} · {item.get('category','Tecnologia')}":item["id"] for item in skills.data}
        if options:
            chosen=st.selectbox("Adicionar habilidade ao seu perfil",list(options),key="profile_skill_choice")
            if st.button("Adicionar habilidade"):
                result=container.user_skills.add_skill(user["id"],options[chosen],"skill")
                if result.status: set_flash("success","Habilidade adicionada ao perfil."); st.rerun()
                st.error(result.message)
    current=container.user_skills.get_skills({"user_id":user["id"]})
    if current.status and current.data:
        skill_names={item["id"]:item["name"] for item in (skills.data or [])} if skills.status else {}
        for item in current.data:
            st.caption(f"• {skill_names.get(item['skill_id'], item['skill_id'])}")
    st.divider()
    st.markdown("**Organizações**")
    with st.form("organization_create_form"):
        org_name=st.text_input("Nome da organização")
        org_description=st.text_area("Descrição",max_chars=1000)
        org_website=st.text_input("Site (opcional)")
        org_submit=st.form_submit_button("Cadastrar organização")
    if org_submit:
        created=container.organizations.create({"name":org_name,"description":org_description,"website":org_website})
        if created.status: set_flash("success","Organização cadastrada."); st.rerun()
        st.error(created.message)
    orgs=container.organizations.get_paginated(0,30)
    if orgs.status:
        for org in orgs.data:
            st.markdown(f"**{org['name']}**")
            if org.get("description"): st.caption(org["description"])


def render_network(container,user):
    st.subheader("Rede de conexões profissionais")
    with st.form("connection_request_form"):
        email=st.text_input("E-mail do profissional que deseja adicionar")
        sent=st.form_submit_button("Enviar solicitação",type="primary")
    if sent:
        lookup=container.users.get_by_email(email.strip().lower())
        target=lookup.data if lookup.status else None
        if not target:
            st.error("Não foi possível localizar esse usuário pelo e-mail.")
        elif target.get("id")==user["id"]:
            st.warning("Você não pode enviar uma solicitação para si mesmo.")
        else:
            result=container.connections.request_connection(user["id"],target["id"])
            if result.status: set_flash("success","Solicitação enviada."); st.rerun()
            st.error(result.message)
    result=container.connections.get_paginated_for_user(user["id"],0,100)
    if result.status:
        st.markdown("**Conexões e solicitações**")
        if not result.data: st.caption("Você ainda não possui conexões.")
        for connection in result.data:
            col1,col2=st.columns([3,1])
            col1.write(f"Usuário: {connection.get('user_id','—')} · {connection.get('status','pendente')}")
            if connection.get("status")=="pending" and connection.get("target_id")==user["id"] and col2.button("Aceitar",key=f"accept_{connection.get('user_id')}"):
                accepted=container.connections.update_connection_request(user["id"],connection["user_id"],{"status":"accepted"})
                if accepted.status: set_flash("success","Conexão aceita."); st.rerun()
                st.error(accepted.message)
    count=container.connections.count_connections(user["id"])
    if count.status: st.metric("Conexões aceitas",count.data)
    st.divider()
    st.markdown("**Mentoria profissional**")
    with st.form("mentorship_create_form"):
        mentor_title=st.text_input("Título",placeholder="Ex.: Mentoria em desenvolvimento Python")
        mentor_description=st.text_area("Descrição",max_chars=1000)
        mentor_skills=st.text_input("Habilidades (separadas por vírgula)",placeholder="python, backend, carreira")
        mentor_submit=st.form_submit_button("Publicar perfil de mentoria")
    if mentor_submit:
        result=container.mentorships.create({"user_id":user["id"],"title":mentor_title,"description":mentor_description,"skills":[v.strip().lower() for v in mentor_skills.split(",") if v.strip()]})
        if result.status: set_flash("success","Perfil de mentoria publicado."); st.rerun()
        st.error(result.message)
    mentors=container.mentorships.filter_mentors()
    if mentors.status:
        for mentor in mentors.data:
            st.markdown(f"**{mentor['title']}**")
            if mentor.get("description"): st.write(mentor["description"])
            if mentor.get("skills"): st.caption("Habilidades: " + ", ".join(mentor["skills"]))
            st.divider()


def render_notifications(container,user):
    st.subheader("Notificações")
    unread=container.notifications.count_unread_by_user_id(user["id"])
    if unread.status: st.metric("Não lidas",unread.data)
    if st.button("Marcar todas como lidas"):
        result=container.notifications.mark_all_as_read(user["id"])
        if result.status: set_flash("success","Notificações marcadas como lidas."); st.rerun()
        st.error(result.message)
    result=container.notifications.get_paginated(0,50,{"user_id":user["id"]})
    if result.status:
        if not result.data: st.caption("Você ainda não tem notificações.")
        for item in result.data:
            marker="🔵" if not item.get("read") else "⚪"
            st.markdown(f"{marker} **{item.get('title','Notificação')}** · {item.get('kind','info')}")
            st.write(item.get("message",""))
            st.divider()
