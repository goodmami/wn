from pprint import pprint
from typing import List

from wn.morphy import morphy
from wn.constants import NOUN, VERB, ADJ

def quick_morphy_test(word: str, pos: str = NOUN) -> List[str]:
    gen = morphy(word, pos)
    print(f"{word!r} -> {list(gen)}")

if __name__ == "__main__":
    # quick_morphy_test("cars pools")
    # quick_morphy_test("sons of bitches")
    # quick_morphy_test("attorneys general")
    # quick_morphy_test("asks for it")
    # quick_morphy_test("customs duties")
    # quick_morphy_test("asking for it")
    # quick_morphy_test("asking for trouble", pos=VERB) # This fails
    quick_morphy_test("apples.")
    pass