from lmsweb import app


@app.route('/')
def t():
    return 'hi'
