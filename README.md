# RedLeaf

A minimal Django blog with role-based access control.

## Setup

```bash
cd redleaf
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Test Accounts

Created by `python manage.py seed_data`. Credentials are defined in
`blog/management/commands/seed_data.py` and shared separately with reviewers.

| Username  | Role        |
|-----------|-------------|
| admin     | super_admin |
| moderator | moderator   |
| usera     | user        |
| userb     | user        |
| userc     | user        |

## Roles

- **super_admin** — full access: manage users, delete any post/comment
- **moderator** — delete any post/comment; no user management
- **user** — create posts/comments; edit/delete own posts; delete comments on own posts
- **guest** (not logged in) — read only

## Pages

| URL | Description |
|-----|-------------|
| `/` | Post list |
| `/post/<id>/` | Post detail with comments |
| `/post/create/` | Create post (login required) |
| `/post/<id>/edit/` | Edit post (author only) |
| `/post/<id>/delete/` | Delete post (author/mod/admin) |
| `/comment/<id>/delete/` | Delete comment (see permission rules) |
| `/register/` | Register |
| `/login/` | Login |
| `/logout/` | Logout |
| `/users/` | User management (super_admin only) |

## Project Structure

```
redleaf/
  blog/
    management/commands/seed_data.py
    migrations/
    templates/
      blog/          # all blog templates
      registration/  # login, register
    admin.py
    forms.py
    models.py
    permissions.py   # can_edit_post, can_delete_post, can_delete_comment
    urls.py
    views.py
  config/
    settings.py
    urls.py
  manage.py
  requirements.txt
```
