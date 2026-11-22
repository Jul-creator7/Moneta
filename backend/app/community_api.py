from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from . import community_service as community
from .banking_api import CurrentUser, Database
from .community_schemas import (
    CommentCreated, CommentInput, CommentsPage, LikeInput, LikeState, PostInput, PostsPage, PostView,
    ProfileInput, PublicProfile,
)

router = APIRouter(prefix="/community", tags=["community"])
Cursor = Annotated[int, Query(gt=0)]
PageSize = Annotated[int, Query(ge=1, le=50)]
Username = Annotated[str, Query(pattern=r"^[a-zA-Z0-9_]{3,32}$")]


@router.get("/profiles/{username}", response_model=PublicProfile)
def profile(username: str, _viewer: CurrentUser, db: Database):
    try:
        return community.profile(community.member(db, username))
    except community.CommunityNotFound as error:
        raise HTTPException(404, str(error)) from error


@router.put("/profile", response_model=PublicProfile)
def update_profile(data: ProfileInput, user: CurrentUser, db: Database):
    return community.update_profile(db, user, data.display_name)


@router.get("/posts", response_model=PostsPage)
def posts(
    user: CurrentUser, db: Database, author: Username | None = None,
    before_id: Cursor | None = None, limit: PageSize = 15,
):
    return community.posts(db, user.id, author, before_id, limit)


@router.post("/posts", response_model=PostView, status_code=201)
def create_post(data: PostInput, user: CurrentUser, db: Database):
    try:
        return community.create_post(db, user.id, data)
    except community.RequestConflict as error:
        raise HTTPException(409, str(error)) from error


@router.put("/posts/{post_id}/like", response_model=LikeState)
def set_like(post_id: int, data: LikeInput, user: CurrentUser, db: Database):
    try:
        return community.set_like(db, user.id, post_id, data.liked)
    except community.CommunityNotFound as error:
        raise HTTPException(404, str(error)) from error


@router.get("/posts/{post_id}/comments", response_model=CommentsPage)
def comments(
    post_id: int, _viewer: CurrentUser, db: Database, before_id: Cursor | None = None,
    limit: PageSize = 15,
):
    try:
        return community.comments(db, post_id, before_id, limit)
    except community.CommunityNotFound as error:
        raise HTTPException(404, str(error)) from error


@router.post("/posts/{post_id}/comments", response_model=CommentCreated, status_code=201)
def add_comment(post_id: int, data: CommentInput, user: CurrentUser, db: Database):
    try:
        return community.add_comment(db, user.id, post_id, data)
    except community.CommunityNotFound as error:
        raise HTTPException(404, str(error)) from error
    except community.RequestConflict as error:
        raise HTTPException(409, str(error)) from error
