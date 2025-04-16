from datetime import date
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session
from app.core.schemas import PaginatedResponse
from app.models.card import Card
from app.schemas.card_schema import CardCreate, CardUpdate, CardResponse
from app.core.responses import success_response
from app.core.exceptions import CustomHTTPException
from app.core.auth import pwd_context
from fastapi import status


def create_card(user_id: int, card: CardCreate, db: Session):
    if card.ExpirationDate <= date.today():
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid ExpirationDate. The card expiration date must be in the future.",
        )

    existing_active_card = (
        db.query(Card).filter(Card.UserID == user_id, Card.Status == "Active").first()
    )
    if existing_active_card:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User already has an active card",
        )

    new_card = Card(
        UserID=user_id,
        CardNumber=card.CardNumber,
        Pin=pwd_context.hash(card.Pin),
        ExpirationDate=card.ExpirationDate,
        Status="Active",
    )

    try:
        db.add(new_card)
        db.commit()
        db.refresh(new_card)
        return success_response(
            message="Card created successfully",
            data=CardResponse.model_validate(new_card).model_dump(),
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to create card",
            details={"error": str(e)},
        )


def list_cards(
    user_id: int,
    db: Session,
    page: int = 1,
    per_page: int = 10,
    sort_by: str = "CardID",
    order: str = "asc",
):
    query = db.query(Card).filter(Card.UserID == user_id)

    # Get total count for pagination
    total_items = query.count()

    # Calculate total pages
    total_pages = (total_items + per_page - 1) // per_page

    # Define sortable columns
    sort_columns = {
        "CardID": Card.CardID,
        "ExpirationDate": Card.ExpirationDate,
        "Status": Card.Status,
        "CardNumber": Card.CardNumber,
    }
    sort_column = sort_columns.get(sort_by, Card.CardID)  # Default to CardID
    order_func = desc if order.lower() == "desc" else asc

    # Apply ordering
    query = query.order_by(order_func(sort_column))

    # Apply pagination
    cards = query.offset((page - 1) * per_page).limit(per_page).all()

    # Return PaginatedResponse
    return PaginatedResponse(
        success=True,
        message="No cards found" if not cards else "Cards retrieved successfully",
        data={[CardResponse.model_validate(card).model_dump() for card in cards]},
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
    )


def update_card(user_id: int, card_id: int, card_update: CardUpdate, db: Session):
    card = db.query(Card).filter(Card.CardID == card_id, Card.UserID == user_id).first()
    if not card:
        raise CustomHTTPException(
            status_code=404, message="Card not found or not owned by user"
        )

    if card.Status == "Blocked":
        raise CustomHTTPException(
            status_code=403, message="Blocked cards cannot be updated by users"
        )

    update_data = card_update.model_dump(exclude_unset=True)
    if "Pin" in update_data:
        update_data["Pin"] = pwd_context.hash(update_data["Pin"])
    if "Status" in update_data and update_data["Status"] == "Blocked":
        raise CustomHTTPException(
            status_code=403, message="Users cannot block their own cards"
        )

    for key, value in update_data.items():
        setattr(card, key, value)

    try:
        db.commit()
        db.refresh(card)
        return success_response(
            message="Card updated successfully",
            data=CardResponse.model_validate(card).model_dump(),
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=500, message="Failed to update card", details={"error": str(e)}
        )


def delete_card(user_id: int, card_id: int, db: Session):
    card = db.query(Card).filter(Card.CardID == card_id, Card.UserID == user_id).first()
    if not card:
        raise CustomHTTPException(
            status_code=404, message="Card not found or not owned by user"
        )
    if card.Status == "Blocked":
        raise CustomHTTPException(
            status_code=403, message="Blocked cards cannot be deleted by users"
        )

    try:
        db.delete(card)
        db.commit()
        return success_response(
            message="Card deleted successfully", data={"CardID": card_id}
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=500, message="Failed to delete card", details={"error": str(e)}
        )
