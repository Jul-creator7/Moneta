from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .banking_service import lock_user
from .community_schemas import (
    CommentCreated, CommentInput, CommentsPage, CommentView, LikeState, PostInput, PostsPage, PostView, PublicProfile,
)
from .models import Comment, Post, PostLike, User


class CommunityNotFound(Exception):
    pass


class RequestConflict(Exception):
    pass


def profile(user: User) -> PublicProfile:
    return PublicProfile(username=user.username, display_name=user.display_name or user.username)


def member(db: Session, username: str) -> User:
    user = db.scalar(select(User).where(User.username == username.lower()))
    if user is None:
        raise CommunityNotFound("Community profile not found.")
    return user


def update_profile(db: Session, user: User, display_name: str | None) -> PublicProfile:
    user.display_name = display_name
    result = profile(user)
    db.commit()
    return result


def post_by_id(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise CommunityNotFound("Community post not found.")
    return post


def post_rows(viewer_id: int):
    like_count = select(func.count()).select_from(PostLike).where(PostLike.post_id == Post.id).scalar_subquery()
    comment_count = select(func.count()).select_from(Comment).where(Comment.post_id == Post.id).scalar_subquery()
    liked = select(PostLike.user_id).where(PostLike.post_id == Post.id, PostLike.user_id == viewer_id).exists()
    return select(Post, User, like_count, comment_count, liked).join(User, User.id == Post.author_id)


def post_view(post: Post, user: User, likes: int, comments: int, liked: bool) -> PostView:
    return PostView(
        id=post.id, author=profile(user), post_type=post.post_type, content=post.content, created_at=post.created_at,
        like_count=likes, comment_count=comments, liked=liked,
    )


def posts(db: Session, viewer_id: int, username: str | None, before_id: int | None, limit: int) -> PostsPage:
    statement = post_rows(viewer_id)
    if username is not None:
        statement = statement.where(User.username == username.lower())
    if before_id is not None:
        statement = statement.where(Post.id < before_id)
    rows = db.execute(statement.order_by(Post.id.desc()).limit(limit + 1)).all()
    items = [post_view(*row) for row in rows[:limit]]
    return PostsPage(items=items, before_id=items[-1].id if len(rows) > limit else None)


def create_post(db: Session, user_id: int, data: PostInput) -> PostView:
    lock_user(db, user_id)
    request_id = str(data.request_id)
    post = db.scalar(select(Post).where(Post.author_id == user_id, Post.request_id == request_id))
    if post is None:
        post = Post(author_id=user_id, request_id=request_id, post_type=data.post_type, content=data.content)
        db.add(post)
        db.flush()
    elif post.content != data.content or post.post_type != data.post_type:
        raise RequestConflict("This request ID was already used for another post.")
    result = post_view(*db.execute(post_rows(user_id).where(Post.id == post.id)).one())
    db.commit()
    return result


def set_like(db: Session, user_id: int, post_id: int, liked: bool) -> LikeState:
    lock_user(db, user_id)
    post_by_id(db, post_id)
    existing = db.get(PostLike, (post_id, user_id))
    if liked and existing is None:
        db.add(PostLike(post_id=post_id, user_id=user_id))
    if not liked and existing is not None:
        db.delete(existing)
    db.flush()
    count = db.scalar(select(func.count()).select_from(PostLike).where(PostLike.post_id == post_id))
    result = LikeState(liked=liked, like_count=count)
    db.commit()
    return result


def comment_view(comment: Comment, user: User) -> CommentView:
    return CommentView(id=comment.id, author=profile(user), content=comment.content, created_at=comment.created_at)


def comments(db: Session, post_id: int, before_id: int | None, limit: int) -> CommentsPage:
    post_by_id(db, post_id)
    statement = select(Comment, User).join(User, User.id == Comment.user_id).where(Comment.post_id == post_id)
    if before_id is not None:
        statement = statement.where(Comment.id < before_id)
    rows = db.execute(statement.order_by(Comment.id.desc()).limit(limit + 1)).all()
    items = [comment_view(*row) for row in rows[:limit]]
    return CommentsPage(items=items, before_id=items[-1].id if len(rows) > limit else None)


def add_comment(db: Session, user_id: int, post_id: int, data: CommentInput) -> CommentCreated:
    lock_user(db, user_id)
    post_by_id(db, post_id)
    request_id = str(data.request_id)
    comment = db.scalar(select(Comment).where(Comment.user_id == user_id, Comment.request_id == request_id))
    if comment is None:
        comment = Comment(user_id=user_id, post_id=post_id, request_id=request_id, content=data.content)
        db.add(comment)
        db.flush()
    elif comment.post_id != post_id or comment.content != data.content:
        raise RequestConflict("This request ID was already used for another comment.")
    result = CommentCreated(
        comment=comment_view(comment, db.get(User, user_id)),
        comment_count=db.scalar(select(func.count()).select_from(Comment).where(Comment.post_id == post_id)),
    )
    db.commit()
    return result
