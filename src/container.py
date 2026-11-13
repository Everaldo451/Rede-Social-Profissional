"""Monta Controllers -> Services -> Repositories (injeção de dependência manual)."""
from dataclasses import dataclass
from controllers.connections.connection_controller import ConnectionController
from controllers.connections.mentorship_controller import MentorshipController
from controllers.notifications.notification_controller import NotificationController
from controllers.posts.comment_controller import CommentController
from controllers.posts.like_controller import LikeController
from controllers.posts.post_controller import PostController
from controllers.profile.organization_controller import OrganizationController
from controllers.profile.skill_controller import SkillController
from controllers.profile.user_controller import UserController
from controllers.profile.user_skill_controller import UserSkillController
from controllers.sessions.online_presence_controller import OnlinePresenceController
from controllers.sessions.session_controller import SessionController
from controllers.shared.media_controller import MediaController
from database.mongo import get_mongo_database
from database.redis import get_redis_client
from database.neo4j import neo4j_driver, neo4j_database
from repositories.connections.connection_repository import ConnectionRepository
from repositories.connections.mentorship_repository import MentorshipRepository
from repositories.notifications.notification_repository import NotificationRepository
from repositories.posts.comment_repository import CommentRepository
from repositories.posts.like_repository import LikeRepository
from repositories.posts.post_repository import PostRepository
from repositories.profile.organization_repository import OrganizationRepository
from repositories.profile.skill_repository import SkillRepository
from repositories.profile.user_repository import UserRepository
from repositories.profile.user_skill_repository import UserSkillRepository
from repositories.sessions.online_presence_repository import OnlinePresenceRepository
from repositories.sessions.session_repository import SessionRepository
from repositories.shared.media_repository import MediaRepository
from services.connections.connection_service import ConnectionService
from services.connections.mentorship_service import MentorshipService
from services.notifications.notification_service import NotificationService
from services.posts.comment_service import CommentService
from services.posts.like_service import LikeService
from services.posts.post_service import PostService
from services.profile.organization_service import OrganizationService
from services.profile.skill_service import SkillService
from services.profile.user_service import UserService
from services.profile.user_skill_service import UserSkillService
from services.sessions.online_presence_service import OnlinePresenceService
from services.sessions.session_service import SessionService
from services.shared.media_service import MediaService

@dataclass(frozen=True)
class Container:
    users: UserController
    sessions: SessionController
    posts: PostController
    comments: CommentController
    media: MediaController
    likes: LikeController
    organizations: OrganizationController
    skills: SkillController
    user_skills: UserSkillController
    connections: ConnectionController
    mentorships: MentorshipController
    notifications: NotificationController
    presence: OnlinePresenceController

def build_container() -> Container:
    db=get_mongo_database(); redis=get_redis_client()
    user_repo=UserRepository(db); post_repo=PostRepository(db); comment_repo=CommentRepository(db)
    user_service=UserService(user_repo)
    session_service=SessionService(SessionRepository(redis),user_service)
    media_service=MediaService(MediaRepository(db))
    post_service=PostService(post_repo,user_repo,comment_repo,media_service)
    notification_service=NotificationService(NotificationRepository(db),redis)
    comment_service=CommentService(comment_repo,post_repo,user_repo,notification_service=notification_service)
    like_service=LikeService(LikeRepository(db),post_repo,user_repo,notification_service)
    skill_repo=SkillRepository(db)
    return Container(
        users=UserController(user_service), sessions=SessionController(session_service),
        posts=PostController(post_service), comments=CommentController(comment_service),
        media=MediaController(media_service), likes=LikeController(like_service),
        organizations=OrganizationController(OrganizationService(OrganizationRepository(db))),
        skills=SkillController(SkillService(skill_repo)),
        user_skills=UserSkillController(UserSkillService(UserSkillRepository(db),skill_repo,user_repo)),
        connections=ConnectionController(ConnectionService(ConnectionRepository(neo4j_driver,neo4j_database),user_repo)),
        mentorships=MentorshipController(MentorshipService(MentorshipRepository(db),user_repo)),
        notifications=NotificationController(notification_service),
        presence=OnlinePresenceController(OnlinePresenceService(OnlinePresenceRepository(redis))),
    )
