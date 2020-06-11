
# Relation Types

SENSE_RELATIONS = {
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
}

SYNSET_RELATIONS = {
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
}


# Adjective Positions

ADJPOSITIONS = (
    'a',   # attributive
    'ip',  # immediate postnominal
    'p',   # predicative
)


# Parts of Speech

NOUN = 'n'
VERB = 'v'
ADJ = ADJECTIVE = 'a'
ADV = ADVERB = 'r'
ADJ_SAT = ADJECTIVE_SATELLITE = 's'
PHRASE = 't'
CONJ = CONJUNCTION = 'c'
ADP = ADPOSITION = 'p'
OTHER = 'x'
UNKNOWN = 'u'

POS_LIST = (
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
)
