from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user_schema import UserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.get_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    service = UserService(db)
    return service.get_user(user_id)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    service = UserService(db)
    return service.create_user(payload)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    service = UserService(db)
    return service.update_user(user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    service = UserService(db)
    service.delete_user(user_id)
