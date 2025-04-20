from typing import Optional
from sqlalchemy.orm import Session
from app.core.schemas import PaginatedResponse
from app.models.card import Card
from app.schemas.card_schema import CardUpdate, CardResponse
from app.core.responses import success_response
from app.core.exceptions import CustomHTTPException
from app.core.auth import pwd_context


def list_all_cards(
    db: Session, page: int = 1, per_page: int = 10, user_id: Optional[int] = None
):
    query = db.query(Card)

    # Apply user_id filter if provided
    if user_id is not None:
        query = query.filter(Card.UserID == user_id)

    # Get total count for pagination
    total_items = query.count()

    # Calculate total pages
    total_pages = (total_items + per_page - 1) // per_page  # Ceiling division

    # Apply pagination
    cards = query.offset((page - 1) * per_page).limit(per_page).all()

    # Prepare response message
    message = (
        "No cards found"
        if not cards
        else (
            f"Cards retrieved successfully for user {user_id}"
            if user_id is not None
            else "All cards retrieved successfully"
        )
    )

    return PaginatedResponse(
        success=True,
        message="All cards retrieved successfully",
        data={"items": [CardResponse.model_validate(c).model_dump() for c in cards]},
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
    ).model_dump()


def block_card(card_id: int, db: Session):
    card = db.query(Card).filter(Card.CardID == card_id).first()
    if not card:
        raise CustomHTTPException(status_code=404, message="Card not found")
    if card.Status == "Blocked":
        raise CustomHTTPException(status_code=400, message="Card is already blocked")

    card.Status = "Blocked"
    try:
        db.commit()
        db.refresh(card)
        return success_response(
            message="Card blocked successfully",
            data=CardResponse.model_validate(card).model_dump(),
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=500, message="Failed to block card", details={"error": str(e)}
        )


def update_card_admin(card_id: int, card_update: CardUpdate, db: Session):
    card = db.query(Card).filter(Card.CardID == card_id).first()
    if not card:
        raise CustomHTTPException(status_code=404, message="Card not found")

    update_data = card_update.model_dump(exclude_unset=True)
    if "Pin" in update_data:
        update_data["Pin"] = pwd_context.hash(update_data["Pin"])

    for key, value in update_data.items():
        setattr(card, key, value)

    try:
        db.commit()
        db.refresh(card)
        return success_response(
            message="Card updated successfully by admin",
            data=CardResponse.model_validate(card).model_dump(),
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=500, message="Failed to update card", details={"error": str(e)}
        )
