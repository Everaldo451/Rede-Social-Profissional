class NotificationController:
    def __init__(self, notification_service):
        pass

    def create(self, data):
        pass

    def get_by_id(self, notification_id):
        pass

    def get_paginated(self, offset, limit, filters=None):
        pass

    def count_unread_by_user_id(self, user_id):
        pass

    def mark_all_as_read(self, user_id):
        pass

    def update(self, notification_id, data):
        pass

    def delete(self, notification_id):
        pass
