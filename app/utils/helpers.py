import random
import string

from sqlalchemy.orm import Session


def generate_referral_code(db: Session, max_retries: int = 3) -> str:
    """
    Generate a unique 8-character referral code.
    Format: AC + 6 random uppercase alphanumeric characters.
    """
    from app.models.user import User

    chars = string.ascii_uppercase + string.digits
    for _ in range(max_retries):
        code = "AC" + "".join(random.choices(chars, k=6))
        exists = db.query(User).filter(User.referral_code == code).first()
        if not exists:
            return code
    # Fallback: longer random suffix
    return "AC" + "".join(random.choices(chars, k=8))


def format_currency(amount) -> str:
    """Format amount as Russian rubles."""
    return f"{float(amount):,.0f} RUB".replace(",", " ")
