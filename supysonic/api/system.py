#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from quart import request

from ._blueprint import api_routing

@api_routing("/ping")
async def ping():
    return await request.formatter.empty
    # return await request.formatter(None, None)

@api_routing("/getLicense")
async def license():
    return await request.formatter("license", {"valid": True})
