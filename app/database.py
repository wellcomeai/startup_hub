import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


INITIAL_PLANS = [
    {
        "code": "explorer",
        "name": "Explorer",
        "price_monthly": 3000,
        "price_yearly": 28800,
        "max_voicyfy_agents": 1,
        "max_chatforyou_access": "limited",
        "max_ai_admin_bots": 1,
        "commission_direct": 30,
        "commission_level2": 15,
        "commission_retention": 10,
        "commission_leader_pool": 5,
        "owner_margin": 40,
        "description": "Базовый тариф для знакомства с экосистемой",
        "features": [
            "1 агент Voicyfy",
            "Курс «Разработчик ИИ-агентов»",
            "Комьюнити-чат",
            "Записи мастер-классов",
            "Реферальная программа",
        ],
        "sort_order": 1,
    },
    {
        "code": "builder",
        "name": "Builder",
        "price_monthly": 5000,
        "price_yearly": 48000,
        "max_voicyfy_agents": 3,
        "max_chatforyou_access": "full",
        "max_ai_admin_bots": 1,
        "commission_direct": 30,
        "commission_level2": 15,
        "commission_retention": 10,
        "commission_leader_pool": 5,
        "owner_margin": 40,
        "description": "Полный доступ к платформам и обучению",
        "features": [
            "3 агента Voicyfy",
            "Все платформы: Voicyfy + ChatForYou + AI Admin",
            "Живые воркшопы",
            "Участие в хабах",
            "Менторство",
            "Реферальная программа",
        ],
        "sort_order": 2,
    },
    {
        "code": "leader",
        "name": "Leader",
        "price_monthly": 7000,
        "price_yearly": 67200,
        "max_voicyfy_agents": 10,
        "max_chatforyou_access": "full",
        "max_ai_admin_bots": 5,
        "commission_direct": 30,
        "commission_level2": 15,
        "commission_retention": 10,
        "commission_leader_pool": 5,
        "owner_margin": 40,
        "description": "Максимальные возможности + создание хабов",
        "features": [
            "10 агентов Voicyfy",
            "Все платформы: полный доступ",
            "Личный ментор",
            "Создание и лидерство в хабах",
            "Приоритетная поддержка",
            "Выступления на мероприятиях",
            "Реферальная программа",
        ],
        "sort_order": 3,
    },
]


def init_db():
    """
    Initialize the database.
    Called at application startup (in lifespan).
    """
    # Import all models so SQLAlchemy sees them
    from app.models import user, subscription, referral, hub  # noqa

    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("All tables created")

    db = SessionLocal()
    try:
        _seed_subscription_plans(db)
        _seed_admin_user(db)
        db.commit()
        logger.info("Seed data inserted")
    except Exception as e:
        db.rollback()
        logger.error(f"Seed error: {e}")
    finally:
        db.close()


def _seed_subscription_plans(db):
    """Insert subscription plans if table is empty."""
    from app.models.subscription import SubscriptionPlan

    existing = db.query(SubscriptionPlan).count()
    if existing > 0:
        return

    for plan_data in INITIAL_PLANS:
        plan = SubscriptionPlan(**plan_data)
        db.add(plan)

    logger.info(f"Inserted {len(INITIAL_PLANS)} subscription plans")


def _seed_admin_user(db):
    """Create admin user if none exists."""
    from app.models.user import User
    from app.utils.security import hash_password

    existing = db.query(User).filter(User.is_admin.is_(True)).count()
    if existing > 0:
        return

    admin = User(
        email="admin@aiclub.ru",
        password_hash=hash_password("CHANGE_ME_IMMEDIATELY"),
        first_name="Admin",
        referral_code="ACADMIN1",
        is_admin=True,
        email_verified=True,
    )
    db.add(admin)
    logger.info("Created admin user (admin@aiclub.ru)")
