"""Create in-app notifications for users."""

from extensions import db
from models.notification import Notification


def notify(
    user_id: int,
    title: str,
    message: str,
    category: str = Notification.CATEGORY_SYSTEM,
    link: str | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title[:120],
        message=message[:255],
        category=category,
        link=link,
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def mark_all_read(user_id: int) -> None:
    Notification.query.filter_by(user_id=user_id, is_read=False).update(
        {"is_read": True}
    )
    db.session.commit()
