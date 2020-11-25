import nox

PYTHON_VERSIONS = sorted(['3.6', '3.7', '3.8', '3.9'])

@nox.session(python=PYTHON_VERSIONS)
def lint(session):
    session.install('flake8', 'mypy')
    session.install('.')
    # session.run('python', '-m', 'flit', 'build')
    session.run('flake8', '--max-line-length', '88', 'wn')
    session.run('mypy', 'wn')
