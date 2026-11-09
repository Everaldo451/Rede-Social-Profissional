import streamlit as st
from bson import ObjectId
from neo4j.exceptions import DriverError, Neo4jError
from pymongo.errors import PyMongoError

from src.controllers.connections.connection_controller import ConnectionController
from src.controllers.connections.mentorship_controller import MentorshipController
from src.repositories.connections.connection_repository import ConnectionRepository
from src.repositories.connections.mentorship_repository import MentorshipRepository
from src.repositories.connections.professional_repository import ProfessionalRepository
from src.services.connections.connection_service import ConnectionService
from src.services.connections.mentorship_service import MentorshipService

from .views import render_mentors, render_network


def connection_pages(current_user_id, mongo_database, neo4j_session_factory):
    """Retorna páginas para registrar depois que o app autenticar o usuário."""
    if not ObjectId.is_valid(current_user_id):
        raise ValueError("A sessão precisa fornecer o ID MongoDB do profissional.")
    user_id = str(ObjectId(current_user_id))
    directory = ProfessionalRepository(mongo_database)
    network = ConnectionController(
        ConnectionService(ConnectionRepository(neo4j_session_factory), directory)
    )
    mentorship = MentorshipController(
        MentorshipService(MentorshipRepository(neo4j_session_factory), directory)
    )

    def show(view, controller):
        try:
            view(controller, user_id, directory)
        except (PyMongoError, Neo4jError, DriverError):
            st.error("Não foi possível acessar os dados da rede. Tente novamente.")

    return [
        st.Page(
            lambda: show(render_network, network),
            title="Rede de conexões",
            url_path="rede-de-conexoes",
        ),
        st.Page(
            lambda: show(render_mentors, mentorship),
            title="Mentoria",
            url_path="mentoria",
        ),
    ]
