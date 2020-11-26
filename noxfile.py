import nox


@nox.session
def lint(session):
    session.install('flake8', 'mypy')
    session.install('.')
    session.run('flake8', '--max-line-length', '88', 'wn')
    session.run('mypy', 'wn')


@nox.session
def test(session):
    session.install('pytest')
    session.install('.')
    session.run('pytest')
