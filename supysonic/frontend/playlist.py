# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import uuid
from functools import wraps

from quart import Response, flash, redirect, render_template, request, url_for

from ..db import Playlist, PlaylistTrack
from ._blueprint import frontend
from ._helpers import parse_checkbox

@frontend.get("/playlist")
async def playlist_index():
    return await render_template(
        "playlists.html",
        mine=Playlist.select().where(Playlist.user == request.user),
        others=Playlist.select().where(Playlist.user != request.user, Playlist.public),
    )


def resolve_and_inject_playlist(func):
    @wraps(func)
    async def decorated(uid):
        try:
            uid = uuid.UUID(uid)
        except ValueError:
            await flash("Invalid playlist id", "warning")
            return redirect(url_for("frontend.playlist_index"))

        try:
            playlist = Playlist[uid]
        except Playlist.DoesNotExist:
            await flash("Unknown playlist", "warning")
            return redirect(url_for("frontend.playlist_index"))

        return await func(uid, playlist)

    return decorated


@frontend.get("/playlist/<uid>")
@resolve_and_inject_playlist
async def playlist_details(uid, playlist):
    return await render_template("playlist.html", playlist=playlist)


@frontend.get("/playlist/<uid>/export")
@resolve_and_inject_playlist
async def playlist_export(uid, playlist):
    response = Response(
        await render_template("playlist_export.m3u", playlist=playlist),
        mimetype="audio/mpegurl",
    )
    response.headers.set(
        "Content-disposition", "attachment", filename=f"{playlist.name}.m3u"
    )
    return response


@frontend.post("/playlist/<uid>")
@resolve_and_inject_playlist
async def playlist_update(uid, playlist):
    if playlist.user_id != request.user.id:
        await flash("You're not allowed to edit this playlist", "danger")
    elif not request.form.get("name"):
        await flash("Missing playlist name", "danger")
    else:
        playlist.name = request.form.get("name")
        playlist.public = parse_checkbox(request.form, "public")
        playlist.save()
        await flash("Playlist updated.", "success")

    return await playlist_details(str(uid))


@frontend.post("/playlist/del/<uid>")
@resolve_and_inject_playlist
async def playlist_delete(uid, playlist):
    if playlist.user_id != request.user.id:
        await flash("You're not allowed to delete this playlist", "danger")
    else:
        PlaylistTrack.delete().where(PlaylistTrack.playlist == playlist).execute()
        playlist.delete_instance()
        await flash("Playlist deleted", "success")

    return redirect(url_for("frontend.playlist_index"))
