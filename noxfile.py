import nox


@nox.session
def lint(session):
    session.install('.[test,web]')
    session.run('flake8', '--max-line-length', '88', 'wn', 'tests')
    session.run('mypy', '--python-version', '3.7', 'wn')


@nox.session
def test(session):
    session.install('pytest')
    session.install('.')
    session.run('pytest')
