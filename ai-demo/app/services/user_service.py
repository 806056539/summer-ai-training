from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import UserCreate, UserUpdate, UserResponse


class UserService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def get_user(self, user_id: int) -> UserResponse:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )
        return UserResponse.model_validate(user)

    def get_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        users = self.repo.get_all(skip=skip, limit=limit)
        return [UserResponse.model_validate(u) for u in users]

    def create_user(self, payload: UserCreate) -> UserResponse:
        if self.repo.get_by_email(payload.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        if self.repo.get_by_username(payload.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )
        user = User(**payload.model_dump())
        created = self.repo.create(user)
        return UserResponse.model_validate(created)

    def update_user(self, user_id: int, payload: UserUpdate) -> UserResponse:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )
        update_data = payload.model_dump(exclude_unset=True)
        if "email" in update_data and update_data["email"] != user.email:
            if self.repo.get_by_email(update_data["email"]):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered",
                )
        if "username" in update_data and update_data["username"] != user.username:
            if self.repo.get_by_username(update_data["username"]):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already taken",
                )
        for field, value in update_data.items():
            setattr(user, field, value)
        updated = self.repo.update(user)
        return UserResponse.model_validate(updated)

    def delete_user(self, user_id: int) -> None:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )
        self.repo.delete(user)
