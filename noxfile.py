import nox


@nox.session
def lint(session):
    session.install('.[test]')
    session.run('mypy', 'wn')
    session.run('flake8', '--max-line-length', '88', 'wn', 'tests')


@nox.session
def test(session):
    session.install('pytest')
    session.install('.')
    session.run('pytest')
