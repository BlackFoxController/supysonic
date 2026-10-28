# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2020-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from quart import request

from ..db import RadioStation
from ._blueprint import api_routing
from ._exceptions import Forbidden, MissingParameter
from ._helpers import get_entity


@api_routing("/getInternetRadioStations")
async def get_radio_stations():
    query = RadioStation.select().order_by(RadioStation.name)
    return await request.formatter(
        "internetRadioStations",
        {"internetRadioStation": [p.as_subsonic_station() for p in query]},
    )


@api_routing("/createInternetRadioStation")
async def create_radio_station():
    if not request.user.admin:
        raise Forbidden()

    req_values = await request.values

    stream_url, name, homepage_url = map(
        req_values.get, ("streamUrl", "name", "homepageUrl")
    )

    if stream_url and name:
        RadioStation.create(stream_url=stream_url, name=name, homepage_url=homepage_url)
    else:
        raise MissingParameter("streamUrl or name")

    return await request.formatter.empty


@api_routing("/updateInternetRadioStation")
async def update_radio_station():
    if not request.user.admin:
        raise Forbidden()

    req_values = await request.values

    res = await get_entity(RadioStation)

    stream_url, name, homepage_url = map(
        req_values.get, ("streamUrl", "name", "homepageUrl")
    )
    if stream_url and name:
        res.stream_url = stream_url
        res.name = name

        if homepage_url:
            res.homepage_url = homepage_url

        res.save()
    else:
        raise MissingParameter("streamUrl or name")

    return await request.formatter.empty


@api_routing("/deleteInternetRadioStation")
async def delete_radio_station():
    if not request.user.admin:
        raise Forbidden()

    res = await get_entity(RadioStation)
    res.delete_instance()

    return await request.formatter.empty
