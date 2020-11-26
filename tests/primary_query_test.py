
import pytest

import wn


def test_get_project_info():
    info = wn.get_project_info('ewn')

    assert info['project'] == 'ewn'
    assert info['label'] == 'English WordNet'
    assert info['language'] == 'en'

    # the following may change as new versions are added
    assert info['version'] == '2020'
    assert wn.get_project_info('ewn') == wn.get_project_info('ewn', version='2020')

    with pytest.raises(wn.Error):
        wn.get_project_info('foo')
    with pytest.raises(wn.Error):
        wn.get_project_info('ewn', version='1983')
    with pytest.raises(wn.Error):
        wn.get_project_info('ewn', version=2020)  # version is string, not int
