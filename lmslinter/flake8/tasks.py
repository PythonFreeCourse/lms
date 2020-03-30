from lmslinter.config.celery import app


@app.task
def foo(pita):
    print(pita)
