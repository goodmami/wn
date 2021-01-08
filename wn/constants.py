"""
Constants and literals used in wordnets.
"""

RELATION_INFO = {
    # 'constitutive': 0
    'hypernym': 10,
    'instance_hypernym': 11,
    'hyponym': 20,
    'instance_hyponym': 21,
    'antonym': 30,
    'eq_synonym': 40,
    'similar': 50,

    'holonym': 60,
    'holo_location': 61,
    'holo_member': 62,
    'holo_part': 63,
    'holo_portion': 64,
    'holo_substance': 65,

    'meronym': 70,
    'mero_location': 71,
    'mero_member': 72,
    'mero_part': 73,
    'mero_portion': 74,
    'mero_substance': 75,

    # others
    'other': 100,
    'also': 101,
    'state_of': 102,
    'causes': 103,
    'subevent': 104,
    'manner_of': 105,
    'attribute': 106,
    'restricts': 107,
    'classifies': 108,
    'entails': 109,

    'be_in_state': 122,
    'is_caused_by': 123,
    'is_subevent_of': 124,
    'in_manner': 125,
    'restricted_by': 127,
    'classified_by': 128,
    'is_entailed_by': 129,

    # 'domain': 200,
    'domain_region': 201,
    'domain_topic': 202,
    'exemplifies': 203,
    # 'has_domain': 220,
    'has_domain_region': 221,
    'has_domain_topic': 222,
    'is_exemplified_by': 223,

    # syntactic roles
    'role': 300,
    'agent': 301,
    'patient': 302,
    'result': 303,
    'instrument': 304,
    'location': 305,
    'direction': 306,
    'target_direction': 307,
    'source_direction': 308,

    'involved': 320,
    'involved_agent': 321,
    'involved_patient': 322,
    'involved_result': 323,
    'involved_instrument': 324,
    'involved_location': 325,
    'involved_direction': 326,
    'involved_target_direction': 327,
    'involved_source_direction': 328,

    'co_role': 350,
    'co_agent_patient': 351,
    'co_patient_agent': 352,
    'co_agent_instrument': 353,
    'co_instrument_agent': 354,
    'co_agent_result': 355,
    'co_result_agent': 356,
    'co_patient_instrument': 357,
    'co_instrument_patient': 358,
    'co_result_instrument': 359,
    'co_instrument_result': 360,

    # Sense-only relations
    'participle': 410,
    'pertainym': 420,
    'derivation': 430,
}


SENSE_RELATIONS = frozenset([
    'antonym',
    'also',
    'participle',
    'pertainym',
    'derivation',
    'domain_topic',
    'has_domain_topic',
    'domain_region',
    'has_domain_region',
    'exemplifies',
    'is_exemplified_by',
    'similar',
    'other',
])

SENSE_SYNSET_RELATIONS = frozenset([
    'other',
    'domain_topic',
    'domain_region',
    'exemplifies',
])

SYNSET_RELATIONS = frozenset([
    'agent',
    'also',
    'attribute',
    'be_in_state',
    'causes',
    'classified_by',
    'classifies',
    'co_agent_instrument',
    'co_agent_patient',
    'co_agent_result',
    'co_instrument_agent',
    'co_instrument_patient',
    'co_instrument_result',
    'co_patient_agent',
    'co_patient_instrument',
    'co_result_agent',
    'co_result_instrument',
    'co_role',
    'direction',
    'domain_region',
    'domain_topic',
    'exemplifies',
    'entails',
    'eq_synonym',
    'has_domain_region',
    'has_domain_topic',
    'is_exemplified_by',
    'holo_location',
    'holo_member',
    'holo_part',
    'holo_portion',
    'holo_substance',
    'holonym',
    'hypernym',
    'hyponym',
    'in_manner',
    'instance_hypernym',
    'instance_hyponym',
    'instrument',
    'involved',
    'involved_agent',
    'involved_direction',
    'involved_instrument',
    'involved_location',
    'involved_patient',
    'involved_result',
    'involved_source_direction',
    'involved_target_direction',
    'is_caused_by',
    'is_entailed_by',
    'location',
    'manner_of',
    'mero_location',
    'mero_member',
    'mero_part',
    'mero_portion',
    'mero_substance',
    'meronym',
    'similar',
    'other',
    'patient',
    'restricted_by',
    'restricts',
    'result',
    'role',
    'source_direction',
    'state_of',
    'target_direction',
    'subevent',
    'is_subevent_of',
    'antonym',
])


# consistency check
assert SENSE_RELATIONS.issubset(RELATION_INFO)
assert SENSE_SYNSET_RELATIONS.issubset(RELATION_INFO)
assert SYNSET_RELATIONS.issubset(RELATION_INFO)


# Adjective Positions

ADJPOSITIONS = frozenset((
    'a',   # attributive
    'ip',  # immediate postnominal
    'p',   # predicative
))


# Parts of Speech

NOUN = 'n'  #:
VERB = 'v'  #:
ADJ = ADJECTIVE = 'a'  #:
ADV = ADVERB = 'r'  #:
ADJ_SAT = ADJECTIVE_SATELLITE = 's'  #:
PHRASE = 't'  #:
CONJ = CONJUNCTION = 'c'  #:
ADP = ADPOSITION = 'p'  #:
OTHER = 'x'  #:
UNKNOWN = 'u'  #:

PARTS_OF_SPEECH = frozenset((
    NOUN,
    VERB,
    ADJECTIVE,
    ADVERB,
    ADJECTIVE_SATELLITE,
    PHRASE,
    CONJUNCTION,
    ADPOSITION,
    OTHER,
    UNKNOWN,
))


# Lexicographer Files
# from https://wordnet.princeton.edu/documentation/lexnames5wn

LEXICOGRAPHER_FILES = {
    'adj.all': 0,
    'adj.pert': 1,
    'adv.all': 2,
    'noun.Tops': 3,
    'noun.act': 4,
    'noun.animal': 5,
    'noun.artifact': 6,
    'noun.attribute': 7,
    'noun.body': 8,
    'noun.cognition': 9,
    'noun.communication': 10,
    'noun.event': 11,
    'noun.feeling': 12,
    'noun.food': 13,
    'noun.group': 14,
    'noun.location': 15,
    'noun.motive': 16,
    'noun.object': 17,
    'noun.person': 18,
    'noun.phenomenon': 19,
    'noun.plant': 20,
    'noun.possession': 21,
    'noun.process': 22,
    'noun.quantity': 23,
    'noun.relation': 24,
    'noun.shape': 25,
    'noun.state': 26,
    'noun.substance': 27,
    'noun.time': 28,
    'verb.body': 29,
    'verb.change': 30,
    'verb.cognition': 31,
    'verb.communication': 32,
    'verb.competition': 33,
    'verb.consumption': 34,
    'verb.contact': 35,
    'verb.creation': 36,
    'verb.emotion': 37,
    'verb.motion': 38,
    'verb.perception': 39,
    'verb.possession': 40,
    'verb.social': 41,
    'verb.stative': 42,
    'verb.weather': 43,
    'adj.ppl': 44,
}
