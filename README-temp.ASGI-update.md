## Notes:

For my use case, I want to add some load- balancing to the server search api. Specifically I want requests not to be executed when user is filing query. I want a server- based solution.
For this, I think I need async functionality within the server. I didn't figure out how to- or if I could- reconfigure gunicorn.

So the idea is that this changes server from WSGI to ASGI (I think)

Which meant with (minimal) changes to change Flask library to Quart.

To run, I use the following command:

pip install gunicorn quart

>gunicorn -w 4 -b 0.0.0.0:5722 "supysonic.web:create_application()" --worker-class asgi

So, in short the changes I made/ or think I did are:

### flask => quart; async/ await; gunicorn works;
- changed import flask to import quart
- copied /supysonic/app/flask.py to quart.py
- all endpoints @api and @frontend => async / await
	... I had some trouble with the error handlers, they're yet todo for proper formatting, they don't return formatted output; took me forever to return the error to the front though (as it is now)
- @frontend, all flash functions are either awaited, commented out or returned
	... Maybe these changes breaks frontend integrity. Should be a small fix for someone who knows what they're doing..
- all request.form, request.values are awaited
- removed csrf protect; 
	... didn't get it to work with Quart, also not quart_wtf. This seems to be an outdated library? I'm quite unfamiliar with all these libraries so it's hard for me to understand what currentdays best practice is for these things.
- changed some line endings to lf

### Temporary patches:
- testing with sqlite database gave me some errors, I assume it's because sqlite is single-thread/ locked by process; I added a patch in temporary patches
- I had some trouble in my environment with the songCount, the exception handing of the get_int in api/\_helpers.py maybe. To patch I hardcoded max_int to 500 and return instead of raising error, see temporary patches commit.

### Conclusion
	I didn't run any unit tests, no idea how it works, but I did run the substreamer app (ios) against the server without encountering errors

	- I log in, run some searches, play some music and sync library.
	No idea about the scrobblers or potential admin functions etc.

