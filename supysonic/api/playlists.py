# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from quart import request

from ..db.models import Playlist, PlaylistTrack, Track, User
from ..db.proxy import db
from ..parsers import parse_int
from ._blueprint import api_routing
from ._exceptions import Forbidden, InvalidParameter, MissingParameter
from ._helpers import get_bool, get_entity, get_entity_id, serialization_context


def _parse_song_index(value):
    """songIndexToRemove is a repeated parameter, so it can't go through get_int.

    Left unbounded on purpose: Playlist.remove_at_indexes already ignores negative
    and out-of-range indexes.
    """
    try:
        index = parse_int(value)
    except ValueError as e:
        raise InvalidParameter("songIndexToRemove", e) from e

    if index is None:
        raise InvalidParameter("songIndexToRemove", "not an integer")
    return index


@api_routing("/getPlaylists")
async def list_playlists():
    req_values = await request.values

    query = (
        Playlist.select()
        .orwhere(Playlist.user == request.user, Playlist.public)
        .order_by(Playlist.name)
    )

    username = req_values.get("username")
    if username:
        if not request.user.admin:
            raise Forbidden()

        # get rather than join in the following query to raise an exception if the
        # requested user doesn't exist
        user = User.get(name=username)
        query = Playlist.select().where(Playlist.user == user).order_by(Playlist.name)

    return await request.formatter(
        "playlists",
        {"playlist": [p.as_subsonic_playlist(request.user) for p in query]},
    )


@api_routing("/getPlaylist")
async def show_playlist():
    res = await get_entity(Playlist)
    if res.user != request.user and not res.public and not request.user.admin:
        raise Forbidden()

    tracks = res.get_tracks()
    ctx = serialization_context()
    ctx.add_tracks(tracks)

    info = res.as_subsonic_playlist(request.user)
    info["entry"] = [t.as_subsonic_child(ctx) for t in tracks]
    return await request.formatter("playlist", info)


@api_routing("/createPlaylist")
@db.atomic()
async def create_playlist():
    req_values = await request.values

    playlist_id, name = map(req_values.get, ("playlistId", "name"))
    # songId actually doesn't seem to be required
    songs = req_values.getlist("songId")
    playlist_id = get_entity_id(Playlist, playlist_id) if playlist_id else None

    if playlist_id:
        playlist = Playlist[playlist_id]

        if playlist.user != request.user and not request.user.admin:
            raise Forbidden()

        playlist.clear()
        if name:
            playlist.name = name
    elif name:
        playlist = Playlist.create(user=request.user, name=name)
    else:
        raise MissingParameter("playlistId or name")

    for sid in songs:
        sid = get_entity_id(Track, sid)
        track = Track[sid]
        playlist.add(track)
    playlist.save()

    return await request.formatter.empty


@api_routing("/deletePlaylist")
async def delete_playlist():
    res = await get_entity(Playlist)
    if res.user != request.user and not request.user.admin:
        raise Forbidden()

    PlaylistTrack.delete().where(PlaylistTrack.playlist == res).execute()
    res.delete_instance()
    return await request.formatter.empty


@api_routing("/updatePlaylist")
async def update_playlist():
    req_values = await request.values

    res = await get_entity(Playlist, "playlistId")
    if res.user != request.user and not request.user.admin:
        raise Forbidden()

    playlist = res
    name, comment = map(req_values.get, ("name", "comment"))
    public = await get_bool("public")
    to_add, to_remove = map(
        req_values.getlist, ("songIdToAdd", "songIndexToRemove")
    )

    if name:
        playlist.name = name
    if comment:
        playlist.comment = comment
    if public is not None:
        playlist.public = public

    to_add = [get_entity_id(Track, i) for i in to_add]
    to_remove = [_parse_song_index(i) for i in to_remove]

    for sid in to_add:
        track = Track[sid]
        playlist.add(track)

    playlist.remove_at_indexes(to_remove)
    playlist.save()

    return await request.formatter.empty
