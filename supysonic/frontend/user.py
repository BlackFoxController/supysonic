# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging

from quart import (
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ..app.quart import app_layer
from ..db.models import ClientPrefs, User
from ..parsers import parse_format, parse_int, parse_mail
from ._blueprint import frontend
from ._helpers import admin_only, me_or_uuid, parse_checkbox, uuid_user

logger = logging.getLogger(__name__)


@frontend.get("/user")
@admin_only
async def user_index():
    return await render_template("users.html", users=User.select())


@frontend.get("/user/<uid>")
@me_or_uuid
async def user_profile(uid, user):
    return await render_template(
        "profile.html",
        user=user,
        scrobblers=app_layer.scrobblers,
        clients=user.clients,
    )


@frontend.post("/user/<uid>")
@me_or_uuid
async def update_clients(uid, user):
    clients_opts = {}
    for key, value in request.form.items():
        if "_" not in key:
            continue
        parts = key.split("_")
        if len(parts) != 2:
            continue
        client, opt = parts
        if not client or not opt:
            continue

        if client not in clients_opts:
            clients_opts[client] = {opt: value}
        else:
            clients_opts[client][opt] = value
    logger.debug(clients_opts)

    for client, opts in clients_opts.items():
        prefs = user.clients.where(ClientPrefs.client_name == client).first()
        if prefs is None:
            continue

        if parse_checkbox(opts, "delete"):
            prefs.delete_instance()
            continue

        try:
            bitrate = parse_int(opts.get("bitrate"), min=0)
        except ValueError:
            await flash(f"Invalid bitrate for client '{client}'.", "danger")
            return await user_profile(uid, user)

        try:
            fmt = parse_format(opts.get("format"))
        except ValueError:
            await flash(f"Invalid format for client '{client}'.", "danger")
            return await user_profile(uid, user)

        prefs.format = fmt
        prefs.bitrate = bitrate
        prefs.save()

    await flash("Clients preferences updated.", "success")
    return await user_profile(uid, user)


@frontend.get("/user/<uid>/changeusername")
@admin_only
@uuid_user
async def change_username_form(uid, user):
    return await render_template("change_username.html", user=user)


@frontend.post("/user/<uid>/changeusername")
@admin_only
@uuid_user
async def change_username_post(uid, user):
    req_form = await request.form

    username = req_form.get("user")
    if username in ("", None):
        await flash("The username is required", "danger")
        return await render_template("change_username.html", user=user)
    if user.name != username:
        try:
            User.get(name=username)
            await flash("This name is already taken", "danger")
            return await render_template("change_username.html", user=user)
        except User.DoesNotExist:
            pass

    admin = parse_checkbox(req_form, "admin")

    if user.name != username or user.admin != admin:
        user.name = username
        user.admin = admin
        user.save()
        await flash(f"User '{username}' updated.", "success")
    else:
        await flash(f"No changes for '{username}'.")

    return redirect(url_for("frontend.user_profile", uid=uid))


@frontend.get("/user/<uid>/changemail")
@me_or_uuid
async def change_mail_form(uid, user):
    return await render_template("change_mail.html", user=user)


@frontend.post("/user/<uid>/changemail")
@me_or_uuid
async def change_mail_post(uid, user):
    req_form = await request.form
    try:
        user.mail = parse_mail(req_form.get("mail"))
    except ValueError as e:
        await flash(f"Invalid email address: {e}", "danger")
        return change_mail_form(uid, user)

    user.save()
    return redirect(url_for("frontend.user_profile", uid=uid))


@frontend.get("/user/<uid>/changepass")
@me_or_uuid
async def change_password_form(uid, user):
    return await render_template("change_pass.html", user=user)


@frontend.post("/user/<uid>/changepass")
@me_or_uuid
async def change_password_post(uid, user):
    req_form = await request.form
    error = False
    if user.id == request.user.id:
        current = req_form.get("current")
        if not current:
            await flash("The current password is required", "danger")
            error = True

    new, confirm = map(req_form.get, ("new", "confirm"))

    if not new:
        await flash("The new password is required", "danger")
        error = True
    if new != confirm:
        await flash("The new password and its confirmation don't match", "danger")
        error = True

    if not error:
        try:
            if user.id == request.user.id:
                app_layer.users.change_password(user.id, current, new)
            else:
                app_layer.users.change_password2(user.name, new)

            await flash("Password changed", "success")
            return redirect(url_for("frontend.user_profile", uid=uid))
        except ValueError as e:
            await flash(str(e), "danger")

    return change_password_form(uid, user)


@frontend.get("/user/add")
@admin_only
async def add_user_form():
    return await render_template("adduser.html")


@frontend.post("/user/add")
@admin_only
async def add_user_post():
    req_form = await request.form

    error = False
    args = req_form.copy()
    (name, passwd, passwd_confirm) = map(
        args.pop, ("user", "passwd", "passwd_confirm"), (None,) * 3
    )
    if not name:
        await flash("The name is required.", "danger")
        error = True
    if not passwd:
        await flash("Please provide a password.", "danger")
        error = True
    elif passwd != passwd_confirm:
        await flash("The passwords don't match.", "danger")
        error = True

    mail = None
    try:
        mail = parse_mail(args.pop("mail", None))
    except ValueError as e:
        await flash(f"Invalid email address: {e}", "danger")
        error = True

    if not error:
        try:
            app_layer.users.add(name, passwd, mail=mail, **args)
            await flash(f"User '{name}' successfully added", "success")
            return redirect(url_for("frontend.user_index"))
        except ValueError as e:
            await flash(str(e), "danger")

    return await add_user_form()


@frontend.post("/user/del/<uid>")
@admin_only
async def del_user(uid):
    try:
        app_layer.users.delete(uid)
        await flash("Deleted user", "success")
    except ValueError as e:
        await flash(str(e), "danger")
    except User.DoesNotExist:
        await flash("No such user", "danger")

    return redirect(url_for("frontend.user_index"))


@frontend.route("/user/login", methods=["GET", "POST"])
async def login():
    req_form = await request.form

    return_url = url_for("frontend.index")
    if request.user:
        await flash("Already logged in")
        return redirect(return_url)

    if request.method == "GET":
        return await render_template("login.html")

    name, password = map(req_form.get, ("user", "password"))

    print (name, password)
    error = False
    if not name:
        await flash("Missing user name", "danger")
        error = True
    if not password:
        await flash("Missing password", "danger")
        error = True

    if not error:
        user = app_layer.users.try_auth(name, password)
        if user:
            logger.info("Logged user %s (IP: %s)", name, request.remote_addr)
            session["userid"] = str(user.id)
            await flash("Logged in!", "success")
            return redirect(return_url)
        else:
            logger.error(
                "Failed login attempt for user %s (IP: %s)", name, request.remote_addr
            )
            await flash("Wrong username or password", "danger")

    return await render_template("login.html")


@frontend.get("/user/logout")
async def logout():
    session.clear()
    await flash("Logged out!", "success")
    return redirect(url_for("frontend.login"))
