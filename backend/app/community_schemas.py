from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, model_validator

from .post_images import PostImage

PostType = Literal["discussion", "achievement"]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


CommunityTime = Annotated[datetime, AfterValidator(as_utc)]


class PublicProfile(BaseModel):
    username: str
    display_name: str


class ProfileInput(BaseModel):
    display_name: Name | None


class PostInput(BaseModel):
    request_id: UUID
    post_type: PostType
    content: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1500)] = ""
    image: PostImage | None = None

    @model_validator(mode="after")
    def require_content(self):
        if not self.content and not self.image:
            raise ValueError("Add text or an image.")
        return self


class CommentInput(BaseModel):
    request_id: UUID
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class LikeInput(BaseModel):
    liked: bool = Field(strict=True)


class LikeState(LikeInput):
    like_count: int


class PostView(LikeState):
    id: int
    author: PublicProfile
    post_type: PostType
    content: str
    image: str | None
    created_at: CommunityTime
    comment_count: int


class CommentView(BaseModel):
    id: int
    author: PublicProfile
    content: str
    created_at: CommunityTime


class PostsPage(BaseModel):
    items: list[PostView]
    before_id: int | None


class CommentsPage(BaseModel):
    items: list[CommentView]
    before_id: int | None


class CommentCreated(BaseModel):
    comment: CommentView
    comment_count: int
