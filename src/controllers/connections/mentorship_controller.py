from src.dto.connections.request.network_requests import ProfessionalSearchRequest

from ._response import run_action


class MentorshipController:
    def __init__(self, mentorship_service):
        self.service = mentorship_service

    def create(self, data):
        pass

    def get_by_id(self, mentorship_id):
        pass

    def filter_mentors(self, user_id, data):
        return run_action(
            lambda: self.service.filter_mentors(
                user_id, ProfessionalSearchRequest.model_validate(data)
            )
        )

    def get_by_user_id(self, user_id):
        return run_action(self.service.get_by_user_id, user_id)

    def list_all(self):
        pass

    def update(self, mentorship_id, data):
        pass

    def delete(self, mentorship_id):
        pass

    def recommend(self, user_id):
        return run_action(self.service.recommend, user_id)

    def desired_skills(self, user_id):
        return run_action(self.service.desired_skills, user_id)
