from datetime import date
from sqlalchemy.orm import Session
from app.models.card import Card
from app.schemas.card_schema import CardCreate, CardResponse
from app.core.responses import success_response
from app.core.exceptions import CustomHTTPException
from app.core.auth import pwd_context
from fastapi import status

def create_card(user_id: int, card: CardCreate, db: Session):
    if card.ExpirationDate <= date.today():
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid ExpirationDate. The card expiration date must be in the future."
        )
        
    existing_active_card = db.query(Card).filter(Card.UserID == user_id, Card.Status == "Active").first()
    if existing_active_card:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User already has an active card"
        )
    
        
    new_card = Card(
        UserID=user_id,
        CardNumber=card.CardNumber,
        Pin=pwd_context.hash(card.Pin),
        ExpirationDate=card.ExpirationDate,
        Status="Active"
    )

    try:
        db.add(new_card)
        db.commit()
        db.refresh(new_card)
        return success_response(
            message="Card created successfully",
            data=CardResponse.model_validate(new_card).model_dump()
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to create card",
            details={"error": str(e)}
        )