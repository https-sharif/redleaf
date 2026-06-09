def get_role(user):
    if not user.is_authenticated:
        return 'guest'
    try:
        return user.profile.role
    except Exception:
        return 'user'


def can_edit_post(user, post):
    return user.is_authenticated and post.author == user


def can_delete_post(user, post):
    if not user.is_authenticated:
        return False
    role = get_role(user)
    return role in ('super_admin', 'moderator') or post.author == user


def can_delete_comment(user, comment):
    if not user.is_authenticated:
        return False
    role = get_role(user)
    if role in ('super_admin', 'moderator'):
        return True
    if comment.author == user:
        return True
    # post owner can delete comments on their post
    if comment.post.author == user:
        return True
    return False


def is_super_admin(user):
    return user.is_authenticated and get_role(user) == 'super_admin'
