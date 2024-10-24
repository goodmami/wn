# Contributing to Wn

Thanks for helping to make Wn better!

**Quick Links:**

- [Report a bug or request a features](https://github.com/goodmami/wn/issues/new)
- [Ask a question](https://github.com/goodmami/wn/discussions)
- [View documentation](https://wn.readthedocs.io/)

**Developer Information:**

- Versioning scheme: [Semantic Versioning](https://semver.org/)
- Branching scheme: [GitHub Flow](https://guides.github.com/introduction/flow/)
- Changelog: [keep a changelog](https://keepachangelog.com/en/1.0.0/)
- Documentation framework: [Sphinx](https://www.sphinx-doc.org/)
- Docstring style: [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) (via [sphinx.ext.napoleon](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html))
- Unit/regression testing: [pytest](https://pytest.org/)
- Packaging framework: [Hatch](https://hatch.pypa.io/)
- Coding style: [PEP-8](https://www.python.org/dev/peps/pep-0008/) (via [Ruff](https://beta.ruff.rs/docs/))
- Type checking: [Mypy](http://mypy-lang.org/)


## Get Help

Confused about wordnets in general? See the [Global Wordnet
Association Documentation](https://globalwordnet.github.io/gwadoc/)

Confused about using Wn or wish to share some tips? [Start a
discussion](https://github.com/goodmami/wn/discussions)

Encountering a problem with Wn or wish to propose a new features? [Raise an
issue](https://github.com/goodmami/wn/issues/new)


## Report a Bug

When reporting a bug, please provide enough information for someone to
reproduce the problem. This might include the version of Python you're
running, the version of Wn you have installed, the wordnet lexicons
you have installed, and possibly the platform (Linux, Windows, macOS)
you're on. Please give a minimal working example that illustrates the
problem. For example:

> I'm using Wn 0.9.5 with Python 3.11 on Linux and [description of
> problem...]. Here's what I have tried:
>
> ```pycon
> >>> import wn
> >>> # some code
> ... # some result or error
> ```


## Request a Feature

If there's a feature that you think would make a good addition to Wn,
raise an issue describing what the feature is and what problems it
would address.

## Guidelines for Contributing

See the "developer information" above for a brief description of
guidelines and conventions used in Wn. If you have a fix, please
submit a pull request to the `main` branch. In general, every pull
request should have an associated issue.

Developers should run and test Wn locally from source using
[Hatch](https://hatch.pypa.io/). Hatch may be installed
system-wide or within a virtual environment:

```bash
$ pip install hatch
```

You can then use the `hatch` commands like the following:

```console
$ hatch shell           # activate a Wn virtual environment
$ hatch fmt --check     # lint the code and check code style
$ hatch run mypy:check  # type check with mypy
$ hatch test            # run unit tests
$ hatch build           # build a source distribution and wheel
$ hatch publish         # publish build artifacts to PyPI
```
