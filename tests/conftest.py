
import pytest


@pytest.fixture
def test_en_lmf(tmp_path):
    path = tmp_path / 'test_en.lmf'
    path.write_text('''\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE LexicalResource SYSTEM "http://globalwordnet.github.io/schemas/WN-LMF-1.0.dtd">
<LexicalResource xmlns:dc="http://purl.org/dc/elements/1.1/">
  <Lexicon id="test-en"
           label="Testing English WordNet"
           language="en"
           email="maintainer@example.com"
           license="https://creativecommons.org/licenses/by/4.0/"
           version="1"
           url="https://example.com/test-en">

    <LexicalEntry id="test-en-example-n">
      <Lemma partOfSpeech="n" writtenForm="example" />
      <Sense id="test-en-example-n-05828980-01" synset="test-en-05828980-n" dc:identifier="example%1:09:00::">
        <SenseRelation relType="derivation" target="test-en-exemplify-v-01023137-01" />
      </Sense>
    </LexicalEntry>

    <Synset id="test-en-05828980-n" ili="i67469" partOfSpeech="n" dc:subject="noun.cognition">
      <Definition>something that exemplifies</Definition>
      <SynsetRelation relType="hypernym" target="test-en-05824413-n" />
      <Example>"this is an example"</Example>
    </Synset>

    <Synset id="test-en-01023137-v" ili="i26682" partOfSpeech="v" dc:subject="verb.communication">
      <Definition>providing an example</Definition>
    </Synset>

  </Lexicon>
</LexicalResource>
''')
    return path
