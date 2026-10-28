# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from quart import request

from ..app.quart import app_layer
from ..db.models import User
from ._blueprint import api_routing
from ._exceptions import Forbidden
from ._helpers import admin_only, decode_password, get_bool, get_mail


@api_routing("/getUser")
async def user_info():
    req_values = await request.values

    username = req_values["username"]

    if username != request.user.name and not request.user.admin:
        raise Forbidden()

    user = User.get(name=username)
    return await request.formatter("user", user.as_subsonic_user(app_layer.scrobblers))


@api_routing("/getUsers")
@admin_only
async def users_info():
    scrobblers = app_layer.scrobblers
    return await request.formatter(
        "users", {"user": [u.as_subsonic_user(scrobblers) for u in User.select()]}
    )


def get_roles_dict():
    return {role: get_bool(role + "Role", False) for role in ("admin", "jukebox")}


@api_routing("/createUser")
@admin_only
async def user_add():
    req_values = await request.values

    username = req_values["username"]
    password = req_values["password"]
    email = await get_mail("email")
    roles = get_roles_dict()

    password = decode_password(password)
    app_layer.users.add(username, password, mail=email, **roles)

    return await request.formatter.empty


@api_routing("/deleteUser")
@admin_only
async def user_del():
    req_values = await request.values

    username = req_values["username"]
    app_layer.users.delete_by_name(username)

    return await request.formatter.empty


@api_routing("/changePassword")
async def user_changepass():
    req_values = await request.values

    username = req_values["username"]
    password = req_values["password"]

    if username != request.user.name and not request.user.admin:
        raise Forbidden()

    password = decode_password(password)
    app_layer.users.change_password2(username, password)

    return await request.formatter.empty


@api_routing("/updateUser")
@admin_only
async def user_edit():
    req_values = await request.values

    username = req_values["username"]
    user = User.get(name=username)

    if "password" in req_values:
        password = decode_password(req_values["password"])
        app_layer.users.change_password2(user, password)

    admin = await get_bool("adminRole")
    jukebox = await get_bool("jukeboxRole")

    if "email" in req_values:
        user.mail = await get_mail("email")

    if admin is not None:
        user.admin = admin

    if jukebox is not None:
        user.jukebox = jukebox

    user.save()

    return await request.formatter.empty
