from wn._util import flatten, normalize_form, unique_list


def test_flatten():
    assert flatten([]) == []
    assert flatten([[]]) == []
    assert flatten([[], []]) == []
    assert flatten([[[], []], [[], []]]) == [[], [], [], []]
    assert flatten([[1]]) == [1]
    assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]
    assert flatten(["AB", "CD"]) == ["A", "B", "C", "D"]


def test_unique_list():
    assert unique_list([]) == []
    assert unique_list([1]) == [1]
    assert unique_list([1, 1, 1, 1, 1]) == [1]
    assert unique_list([1, 1, 2, 2, 1]) == [1, 2]
    assert unique_list([2, 1, 2, 2, 1]) == [2, 1]
    assert unique_list("A") == ["A"]
    assert unique_list("AAA") == ["A"]
    assert unique_list("ABABA") == ["A", "B"]
    assert unique_list([(1, 2), (1, 2), (2, 3)]) == [(1, 2), (2, 3)]


def test_normalize_form():
    assert normalize_form("ABC") == "abc"
    assert normalize_form("so\xf1ar") == "sonar"  # soñar with single ñ character
    assert normalize_form("son\u0303ar") == "sonar"  # soñar with combining tilde
    assert normalize_form("Weiß") == "weiss"
