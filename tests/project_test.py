from wn import project

def test_is_package_directory(datadir):
    assert project.is_package_directory(datadir / "test-package")
    assert not project.is_package_directory(datadir)


def test_is_collection_directory(datadir):
    # not really, but it is a directory containing a package
    assert project.is_collection_directory(datadir)
    assert not project.is_collection_directory(datadir / "test-package")


def test_get_project(datadir):
    proj = project.get_project(path=datadir / "test-package")
    assert proj.resource_file() == datadir / "test-package" / "test-wn.xml"
    assert proj.readme() == datadir / "test-package" / "README.md"
    assert proj.license() == datadir / "test-package" / "LICENSE"
    assert proj.citation() == datadir / "test-package" / "citation.bib"

    proj = project.get_project(path=datadir / "mini-lmf-1.0.xml")
    assert proj.resource_file() == datadir / "mini-lmf-1.0.xml"
    assert proj.readme() is None
    assert proj.license() is None
    assert proj.citation() is None


def test_iterpackages(datadir):
    # for now, collection.packages() does not return contained resource files
    pkg_names = {
        pkg.resource_file().name
        for pkg in project.iterpackages(datadir)
    }
    assert "mini-lmf-1.0.xml" not in pkg_names
    assert "test-wn.xml" in pkg_names

    # explicitly giving a resource file path works, though
    pkg_names = {
        pkg.resource_file().name
        for pkg in project.iterpackages(datadir /  "mini-lmf-1.0.xml")
    }
    assert "mini-lmf-1.0.xml" in pkg_names
    assert "test-wn.xml" not in pkg_names
