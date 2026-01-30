"""
Database retrieval queries.
"""

import itertools
from collections.abc import Collection, Iterator, Sequence
from typing import cast

from wn._db import connect
from wn._exceptions import Error
from wn._metadata import Metadata

# Local Types

Pronunciation = tuple[
    str,  # value
    str | None,  # variety
    str | None,  # notation
    bool,  # phonemic
    str | None,  # audio
    str,  # lexicon specifier
]
Tag = tuple[str, str, str]  # tag, category, lexicon specifier
Form = tuple[
    str,  # form
    str | None,  # id
    str | None,  # script
    str,  # lexicon
    list[Pronunciation],  # pronunciations
    list[Tag],  # tags
]
_Word = tuple[
    str,  # id
    str,  # pos
    str,  # lexicon specifier
]
_Synset = tuple[
    str,  # id
    str,  # pos
    str,  # ili
    str,  # lexicon specifier
]
_Synset_Relation = tuple[
    str,  # rel_name
    str,  # lexicon
    Metadata,  # metadata
    str,  # srcid
    str,  # _Synset...
    str,
    str,
    str,
]
_Definition = tuple[
    str,  # text
    str,  # language
    str,  # sourceSense
    str,  # lexicon
    Metadata | None,  # metadata
]
_Example = tuple[
    str,  # text
    str,  # language
    str,  # lexicon
    Metadata | None,  # metadata
]
Sense = tuple[
    str,  # id
    str,  # entry_id
    str,  # synset_id
    str,  # lexicon specifier
]
_Sense_Relation = tuple[
    str,  # rel_name
    str,  # lexicon
    Metadata,  # metadata
    str,  # Sense...
    str,
    str,
    str,
]
_Count = tuple[int, str, Metadata]  # count, lexicon, metadata
_SyntacticBehaviour = tuple[
    str,  # id
    str,  # frame
    list[str],  # sense ids
]
_ExistingILI = tuple[
    str,  # id
    str,  # status
    str | None,  # definition
    Metadata,
]
_ProposedILI = tuple[
    str,  # synset id
    str,  # lexicon
    str,  # definition
    Metadata,
]
_Lexicon = tuple[
    str,  # specifier
    str,  # id
    str,  # label
    str,  # language
    str,  # email
    str,  # license
    str,  # version
    str,  # url
    str,  # citation
    str,  # logo
    Metadata | None,  # metadata
]


def resolve_lexicon_specifiers(
    lexicon: str,
    lang: str | None = None,
) -> list[str]:
    cur = connect().cursor()
    specifiers: list[str] = []
    for specifier in lexicon.split():
        limit = "-1" if "*" in lexicon else "1"
        if ":" not in specifier:
            specifier += ":*"
        query = f"""
            SELECT DISTINCT specifier
              FROM lexicons
             WHERE specifier GLOB :specifier
               AND (:language ISNULL OR language = :language)
             LIMIT {limit}
        """
        params = {"specifier": specifier, "language": lang}
        specifiers.extend(row[0] for row in cur.execute(query, params))
    # only raise an error when the query specifies something
    if not specifiers and (lexicon != "*" or lang is not None):
        raise Error(f"no lexicon found with lang={lang!r} and lexicon={lexicon!r}")
    return specifiers


def get_lexicon(lexicon: str) -> _Lexicon:
    query = """
        SELECT DISTINCT specifier, id, label, language, email, license,
                        version, url, citation, logo, metadata
        FROM lexicons
        WHERE specifier = ?
    """
    row: _Lexicon | None = connect().execute(query, (lexicon,)).fetchone()
    if row is None:
        raise LookupError(lexicon)  # should we have a WnLookupError?
    return row


def get_modified(lexicon: str) -> bool:
    query = "SELECT modified FROM lexicons WHERE specifier = ?"
    return connect().execute(query, (lexicon,)).fetchone()[0]


def get_lexicon_dependencies(lexicon: str) -> list[tuple[str, str, bool]]:
    query = """
        SELECT provider_id || ":" || provider_version, provider_url, provider_rowid
          FROM lexicon_dependencies
          JOIN lexicons AS lex ON lex.rowid = dependent_rowid
         WHERE lex.specifier = ?
    """
    return [
        (spec, url, rowid is not None)
        for spec, url, rowid in connect().execute(query, (lexicon,))
    ]


def get_lexicon_extension_bases(lexicon: str, depth: int = -1) -> list[str]:
    query = """
          WITH RECURSIVE ext(x, d) AS
               (SELECT base_rowid, 1
                  FROM lexicon_extensions
                  JOIN lexicons AS lex ON lex.rowid = extension_rowid
                 WHERE lex.specifier = :specifier
                 UNION SELECT base_rowid, d+1
                         FROM lexicon_extensions
                         JOIN ext ON extension_rowid = x)
        SELECT baselex.specifier
          FROM ext
          JOIN lexicons AS baselex ON baselex.rowid = ext.x
         WHERE :depth < 0 OR d <= :depth
         ORDER BY d
    """
    rows = connect().execute(query, {"specifier": lexicon, "depth": depth})
    return [row[0] for row in rows]


def get_lexicon_extensions(lexicon: str, depth: int = -1) -> list[str]:
    query = """
          WITH RECURSIVE ext(x, d) AS
               (SELECT extension_rowid, 1
                  FROM lexicon_extensions
                  JOIN lexicons AS lex ON lex.rowid = base_rowid
                 WHERE lex.specifier = :specifier
                 UNION SELECT extension_rowid, d+1
                         FROM lexicon_extensions
                         JOIN ext ON base_rowid = x)
        SELECT extlex.specifier
          FROM ext
          JOIN lexicons AS extlex ON extlex.rowid = ext.x
         WHERE :depth < 0 OR d <= :depth
         ORDER BY d
    """
    rows = connect().execute(query, {"specifier": lexicon, "depth": depth})
    return [row[0] for row in rows]


def get_ili(id: str) -> _ExistingILI | None:
    query = """
        SELECT i.id, ist.status, i.definition, i.metadata
          FROM ilis AS i
          JOIN ili_statuses AS ist ON i.status_rowid = ist.rowid
         WHERE i.id = ?
         LIMIT 1
    """
    return connect().execute(query, (id,)).fetchone()


def find_ilis(
    status: str | None = None,
    lexicons: Sequence[str] = (),
) -> Iterator[_ExistingILI]:
    query = """
        SELECT DISTINCT i.id, ist.status, i.definition, i.metadata
          FROM ilis AS i
          JOIN ili_statuses AS ist ON i.status_rowid = ist.rowid
    """
    conditions: list[str] = []
    params: list = []
    if status:
        conditions.append("ist.status = ?")
        params.append(status)
    if lexicons:
        # this runs much faster than just adding a condition
        query = """
        SELECT DISTINCT i.id, ist.status, i.definition, i.metadata
          FROM lexicons as lex
          JOIN synsets AS ss ON ss.lexicon_rowid = lex.rowid
          JOIN ilis AS i ON i.rowid = ss.ili_rowid
          JOIN ili_statuses AS ist ON i.status_rowid = ist.rowid
        """
        conditions.append(f"lex.specifier IN ({_qs(lexicons)})")
        params.extend(lexicons)

    if conditions:
        query += " WHERE " + "\n           AND ".join(conditions)

    yield from connect().execute(query, params)


def find_proposed_ilis(
    synset_id: str | None = None,
    lexicons: Sequence[str] = (),
) -> Iterator[_ProposedILI]:
    query = """
    SELECT ss.id, lex.specifier, pi.definition, pi.metadata
      FROM proposed_ilis AS pi
      JOIN synsets AS ss ON ss.rowid = synset_rowid
      JOIN lexicons AS lex ON lex.rowid = ss.lexicon_rowid
    """
    conditions: list[str] = []
    params: list = []
    if synset_id is not None:
        conditions.append("ss.id = ?")
        params.append(synset_id)
    if lexicons:
        conditions.append(f"lex.specifier IN ({_qs(lexicons)})")
        params.extend(lexicons)
    if conditions:
        query += " WHERE " + "\n           AND ".join(conditions)
    yield from connect().execute(query, params)


def find_entries(
    id: str | None = None,
    forms: Sequence[str] = (),
    pos: str | None = None,
    lexicons: Sequence[str] = (),
    normalized: bool = False,
    search_all_forms: bool = False,
) -> Iterator[_Word]:
    conn = connect()
    cte, cteparams, conditions, condparams = _build_entry_conditions(
        forms, pos, lexicons, normalized, search_all_forms
    )

    if id:
        conditions.insert(0, "e.id = ?")
        condparams.insert(0, id)

    condition = ""
    if conditions:
        condition = "WHERE " + "\n           AND ".join(conditions)

    query = f"""
          {cte}
        SELECT DISTINCT e.id, e.pos, lex.specifier
          FROM entries AS e
          JOIN lexicons AS lex ON lex.rowid = e.lexicon_rowid
         {condition}
         ORDER BY e.rowid ASC
    """

    rows: Iterator[_Word] = conn.execute(query, cteparams + condparams)
    yield from rows


def _load_lemmas_with_details(
    conn,
    cte: str,
    cteparams: list,
    conditions: list[str],
    condparams: list,
    with_lexicons: bool,
) -> Iterator[Form]:
    """Load lemmas with pronunciations and tags (full details)."""
    plex_cond = "AND plex.specifier IN lexspecs" if with_lexicons else ""
    tlex_cond = "AND tlex.specifier IN lexspecs" if with_lexicons else ""
    condition = ""
    if conditions:
        condition = "AND " + "\n           AND ".join(conditions)
    query = f"""
          {cte}
        SELECT DISTINCT f.rowid, f.form, f.id, f.script, lex.specifier,
               p.value, p.variety, p.notation, p.phonemic, p.audio, plex.specifier,
               t.tag, t.category, tlex.specifier
          FROM forms AS f
          JOIN entries AS e ON e.rowid = f.entry_rowid
          JOIN lexicons AS lex ON lex.rowid = e.lexicon_rowid
          LEFT JOIN pronunciations AS p ON p.form_rowid = f.rowid
          LEFT JOIN lexicons AS plex ON plex.rowid = p.lexicon_rowid {plex_cond}
          LEFT JOIN tags AS t ON t.form_rowid = f.rowid
          LEFT JOIN lexicons AS tlex ON tlex.rowid = t.lexicon_rowid {tlex_cond}
         WHERE f.rank = 0
         {condition}
         ORDER BY f.rowid ASC
    """

    # Group results by form_rowid and process pronunciations/tags
    forms_dict: dict[
        int, tuple[str, str | None, str | None, str, list[Pronunciation], list[Tag]]
    ] = {}

    for row in conn.execute(query, cteparams + condparams):
        form_rowid, form, form_id, script, lexicon = row[0:5]
        pron_data = row[5:11]
        tag_data = row[11:14]

        if form_rowid not in forms_dict:
            forms_dict[form_rowid] = (form, form_id, script, lexicon, [], [])

        # Add pronunciation if present
        if pron_data[0] is not None:  # value
            pron = cast("Pronunciation", pron_data)
            if pron not in forms_dict[form_rowid][4]:
                forms_dict[form_rowid][4].append(pron)

        # Add tag if present
        if tag_data[0] is not None:  # tag
            tag = cast("Tag", tag_data)
            if tag not in forms_dict[form_rowid][5]:
                forms_dict[form_rowid][5].append(tag)

    # Yield forms in order
    yield from forms_dict.values()


def find_lemmas(
    forms: Sequence[str] = (),
    pos: str | None = None,
    lexicons: Sequence[str] = (),
    normalized: bool = False,
    search_all_forms: bool = False,
    load_details: bool = False,
) -> Iterator[Form]:
    """Find lemmas matching the given criteria.

    Returns form data for the lemma of each matching entry.
    If load_details is False, pronunciations and tags are not loaded.
    """
    conn = connect()
    cte, cteparams, conditions, condparams = _build_entry_conditions(
        forms, pos, lexicons, normalized, search_all_forms
    )

    if not load_details:
        # Fast path: don't load pronunciations and tags
        condition = ""
        if conditions:
            condition = "AND " + "\n           AND ".join(conditions)
        query = f"""
              {cte}
            SELECT f.form, f.id, f.script, lex.specifier
              FROM forms AS f
              JOIN entries AS e ON e.rowid = f.entry_rowid
              JOIN lexicons AS lex ON lex.rowid = e.lexicon_rowid
             WHERE f.rank = 0
             {condition}
             ORDER BY f.rowid ASC
        """
        for row in conn.execute(query, cteparams + condparams):
            form, form_id, script, lexicon = row
            yield (form, form_id, script, lexicon, [], [])
    else:
        # Full path: load pronunciations and tags
        yield from _load_lemmas_with_details(
            conn, cte, cteparams, conditions, condparams, bool(lexicons)
        )


def find_senses(
    id: str | None = None,
    forms: Sequence[str] = (),
    pos: str | None = None,
    lexicons: Sequence[str] = (),
    normalized: bool = False,
    search_all_forms: bool = False,
) -> Iterator[Sense]:
    conn = connect()
    ctes: list[str] = []
    params: list = []
    conditions = []
    order = "s.rowid"
    if id:
        conditions.append("s.id = ?")
        params.append(id)
    if forms:
        ctes, subquery = _query_forms(forms, normalized, search_all_forms)
        conditions.append(f"s.entry_rowid IN {subquery}")
        params.extend(forms)
        order = "s.lexicon_rowid, e.pos, s.entry_rank"
    if pos:
        conditions.append("e.pos = ?")
        params.append(pos)
    if lexicons:
        conditions.append(f"slex.specifier IN ({_qs(lexicons)})")
        params.extend(lexicons)

    cte = ""
    if ctes:
        cte = "WITH " + ",\n         ".join(ctes)

    condition = ""
    if conditions:
        condition = "WHERE " + "\n           AND ".join(conditions)

    query = f"""
          {cte}
        SELECT DISTINCT s.id, e.id, ss.id, slex.specifier
          FROM senses AS s
          JOIN entries AS e ON e.rowid = s.entry_rowid
          JOIN synsets AS ss ON ss.rowid = s.synset_rowid
          JOIN lexicons AS slex ON slex.rowid = s.lexicon_rowid
         {condition}
         ORDER BY {order} ASC
    """

    rows: Iterator[Sense] = conn.execute(query, params)
    yield from rows


def find_synsets(
    id: str | None = None,
    forms: Sequence[str] = (),
    pos: str | None = None,
    ili: str | None = None,
    lexicons: Sequence[str] = (),
    normalized: bool = False,
    search_all_forms: bool = False,
) -> Iterator[_Synset]:
    conn = connect()
    ctes: list[str] = []
    join = ""
    conditions = []
    order = "ss.rowid"
    params: list = []
    if id:
        conditions.append("ss.id = ?")
        params.append(id)
    if forms:
        ctes, subquery = _query_forms(forms, normalized, search_all_forms)
        join = f"""\
          JOIN (SELECT _s.entry_rowid, _s.synset_rowid, _s.entry_rank
                  FROM senses AS _s
                 WHERE _s.entry_rowid IN {subquery}
               ) AS s
            ON s.synset_rowid = ss.rowid
        """.strip()
        params.extend(forms)
        order = "ss.lexicon_rowid, ss.pos, s.entry_rank"
    if pos:
        conditions.append("ss.pos = ?")
        params.append(pos)
    if ili:
        conditions.append(
            "ss.ili_rowid IN (SELECT ilis.rowid FROM ilis WHERE ilis.id = ?)"
        )
        params.append(ili)
    if lexicons:
        conditions.append(f"sslex.specifier IN ({_qs(lexicons)})")
        params.extend(lexicons)

    cte = ""
    if ctes:
        cte = "WITH " + ",\n         ".join(ctes)

    condition = ""
    if conditions:
        condition = "WHERE " + "\n           AND ".join(conditions)

    query = f"""
          {cte}
        SELECT DISTINCT ss.id, ss.pos,
                        (SELECT ilis.id FROM ilis WHERE ilis.rowid=ss.ili_rowid),
                        sslex.specifier
          FROM synsets AS ss
          JOIN lexicons AS sslex ON sslex.rowid = ss.lexicon_rowid
          {join}
         {condition}
         ORDER BY {order} ASC
    """

    rows: Iterator[_Synset] = conn.execute(query, params)
    yield from rows


def get_entry_forms(id: str, lexicons: Sequence[str]) -> Iterator[Form]:
    form_query = f"""
          WITH lexspecs(s) AS (VALUES {_vs(lexicons)})
        SELECT f.rowid, f.form, f.id, f.script, lex.specifier
          FROM forms AS f
          JOIN entries AS e ON e.rowid = entry_rowid
          JOIN lexicons AS lex ON lex.rowid = e.lexicon_rowid
         WHERE e.id = ?
           AND lex.specifier IN lexspecs
         ORDER BY f.rank
    """
    pron_query = f"""
          WITH lexspecs(s) AS (VALUES {_vs(lexicons)})
        SELECT p.value, p.variety, p.notation, p.phonemic, p.audio, lex.specifier
          FROM pronunciations AS p
          JOIN lexicons AS lex ON lex.rowid = p.lexicon_rowid
         WHERE form_rowid = ?
           AND lex.specifier IN lexspecs
    """
    tag_query = f"""
          WITH lexspecs(s) AS (VALUES {_vs(lexicons)})
        SELECT t.tag, t.category, lex.specifier
          FROM tags AS t
          JOIN lexicons AS lex ON lex.rowid = t.lexicon_rowid
         WHERE form_rowid = ?
           AND lex.specifier IN lexspecs
    """

    cur = connect().cursor()
    for row in cur.execute(form_query, (*lexicons, id)).fetchall():
        params = (*lexicons, row[0])
        prons: list[Pronunciation] = cur.execute(pron_query, params).fetchall()
        tags: list[Tag] = cur.execute(tag_query, params).fetchall()
        yield (*row[1:], prons, tags)


def get_synsets_for_ilis(
    ilis: Collection[str],
    lexicons: Sequence[str],
) -> Iterator[_Synset]:
    conn = connect()
    query = f"""
        SELECT DISTINCT ss.id, ss.pos, ili.id, sslex.specifier
          FROM synsets as ss
          JOIN ilis as ili ON ss.ili_rowid = ili.rowid
          JOIN lexicons AS sslex ON sslex.rowid = ss.lexicon_rowid
         WHERE ili.id IN ({_qs(ilis)})
           AND sslex.specifier IN ({_qs(lexicons)})
    """
    params = *ilis, *lexicons
    result_rows: Iterator[_Synset] = conn.execute(query, params)
    yield from result_rows


def get_synset_relations(
    synset_id: str,
    synset_lexicon: str,
    relation_types: Collection[str],
    lexicons: Sequence[str],
    target_lexicons: Sequence[str],
) -> Iterator[_Synset_Relation]:
    conn = connect()
    params: list = []
    constraint = ""
    if relation_types and "*" not in relation_types:
        constraint = f"WHERE type IN ({_qs(relation_types)})"
        params.extend(relation_types)
    params.extend(lexicons)
    params.extend(target_lexicons)
    params.append(synset_id)
    params.append(synset_lexicon)
    query = f"""
        WITH
          reltypes(rowid) AS
            (SELECT rowid FROM relation_types {constraint}),
          lexrowids(rowid) AS
            (SELECT rowid FROM lexicons
              WHERE specifier IN ({_vs(lexicons)})),
          tgtlexrowids(rowid) AS
            (SELECT rowid FROM lexicons
              WHERE specifier IN ({_vs(target_lexicons)})),
          srcsynset(rowid) AS
            (SELECT ss.rowid
               FROM synsets AS ss
               JOIN lexicons AS lex ON lex.rowid = ss.lexicon_rowid
              WHERE ss.id = ?
                AND lex.specifier = ?),
          matchingrels(rowid) AS
            (SELECT srel.rowid
               FROM synset_relations AS srel
              WHERE srel.source_rowid IN srcsynset
                AND srel.lexicon_rowid IN lexrowids
                AND srel.type_rowid IN reltypes)
        SELECT DISTINCT rt.type, lex.specifier, srel.metadata,
                        src.id, tgt.id, tgt.pos, tgtili.id, tgtlex.specifier
          FROM matchingrels AS mr
          JOIN synset_relations AS srel ON srel.rowid=mr.rowid
          JOIN relation_types AS rt ON rt.rowid=srel.type_rowid
          JOIN synsets AS src ON src.rowid = srel.source_rowid
          JOIN synsets AS tgt ON tgt.rowid = srel.target_rowid
          JOIN lexicons AS lex ON lex.rowid = srel.lexicon_rowid
          JOIN lexicons AS tgtlex ON tgtlex.rowid = tgt.lexicon_rowid
          LEFT JOIN ilis AS tgtili ON tgtili.rowid = tgt.ili_rowid  -- might be null
         WHERE tgt.lexicon_rowid IN tgtlexrowids  -- ensure target is included
    """
    result_rows: Iterator[_Synset_Relation] = conn.execute(query, params)
    yield from result_rows


def get_expanded_synset_relations(
    ili_id: str,
    relation_types: Collection[str],
    expands: Sequence[str],
) -> Iterator[_Synset_Relation]:
    conn = connect()
    params: list = []
    constraint = ""
    if relation_types and "*" not in relation_types:
        constraint = f"WHERE type IN ({_qs(relation_types)})"
        params.extend(relation_types)
    params.extend(expands)
    params.append(ili_id)
    query = f"""
        WITH
          reltypes(rowid) AS
            (SELECT rowid FROM relation_types {constraint}),
          lexrowids(rowid) AS
            (SELECT rowid FROM lexicons WHERE specifier IN ({_vs(expands)})),
          srcsynset(rowid) AS
            (SELECT ss.rowid
               FROM synsets AS ss
               JOIN ilis ON ilis.rowid = ss.ili_rowid
              WHERE ilis.id = ?
                AND ss.lexicon_rowid IN lexrowids),
          matchingrels(rowid) AS
            (SELECT srel.rowid
               FROM synset_relations AS srel
              WHERE srel.source_rowid IN srcsynset
                AND srel.lexicon_rowid IN lexrowids
                AND srel.type_rowid IN reltypes)
        SELECT DISTINCT rt.type, lex.specifier, srel.metadata,
                        src.id, tgt.id, tgt.pos, tgtili.id, tgtlex.specifier
          FROM matchingrels AS mr
          JOIN synset_relations AS srel ON srel.rowid=mr.rowid
          JOIN relation_types AS rt ON rt.rowid=srel.type_rowid
          JOIN synsets AS src ON src.rowid = srel.source_rowid
          JOIN synsets AS tgt ON tgt.rowid = srel.target_rowid
          JOIN ilis AS tgtili ON tgtili.rowid = tgt.ili_rowid
          JOIN lexicons AS lex ON lex.rowid = srel.lexicon_rowid
          JOIN lexicons AS tgtlex ON tgtlex.rowid = tgt.lexicon_rowid
    """
    result_rows: Iterator[_Synset_Relation] = conn.execute(query, params)
    yield from result_rows


def get_definitions(
    synset_id: str,
    lexicons: Sequence[str],
) -> list[_Definition]:
    conn = connect()
    query = f"""
        SELECT d.definition,
               d.language,
               (SELECT s.id FROM senses AS s WHERE s.rowid=d.sense_rowid),
               lex.specifier,
               d.metadata
          FROM definitions AS d
          JOIN synsets AS ss ON ss.rowid = d.synset_rowid
          JOIN lexicons AS lex ON lex.rowid = d.lexicon_rowid
         WHERE ss.id = ?
           AND lex.specifier IN ({_qs(lexicons)})
    """
    return conn.execute(query, (synset_id, *lexicons)).fetchall()


_SANITIZED_EXAMPLE_PREFIXES = {
    "senses": "sense",
    "synsets": "synset",
}


def get_examples(
    id: str,
    table: str,
    lexicons: Sequence[str],
) -> list[_Example]:
    conn = connect()
    prefix = _SANITIZED_EXAMPLE_PREFIXES.get(table)
    if prefix is None:
        raise Error(f"'{table}' does not have examples")
    query = f"""
        SELECT ex.example, ex.language, lex.specifier, ex.metadata
          FROM {prefix}_examples AS ex
          JOIN {table} AS tbl ON tbl.rowid = ex.{prefix}_rowid
          JOIN lexicons AS lex ON lex.rowid = ex.lexicon_rowid
         WHERE tbl.id = ?
           AND lex.specifier IN ({_qs(lexicons)})
    """
    return conn.execute(query, (id, *lexicons)).fetchall()


def find_syntactic_behaviours(
    id: str | None = None,
    lexicons: Sequence[str] = (),
) -> Iterator[_SyntacticBehaviour]:
    conn = connect()
    query = """
        SELECT sb.id, sb.frame, s.id
          FROM syntactic_behaviours AS sb
          JOIN syntactic_behaviour_senses AS sbs
            ON sbs.syntactic_behaviour_rowid = sb.rowid
          JOIN senses AS s
            ON s.rowid = sbs.sense_rowid
          JOIN lexicons AS lex ON lex.rowid = sb.lexicon_rowid
    """
    conditions: list[str] = []
    params: list = []
    if id:
        conditions.append("sb.id = ?")
        params.append(id)
    if lexicons:
        conditions.append(f"lex.specifier IN ({_qs(lexicons)})")
        params.extend(lexicons)
    if conditions:
        query += "\n WHERE " + "\n   AND ".join(conditions)
    rows: Iterator[tuple[str, str, str]] = conn.execute(query, params)
    for key, group in itertools.groupby(rows, lambda row: row[0:2]):
        id, frame = cast("tuple[str, str]", key)
        sense_ids = [row[2] for row in group]
        yield id, frame, sense_ids


def get_syntactic_behaviours(
    sense_id: str,
    lexicons: Sequence[str],
) -> list[str]:
    conn = connect()
    query = f"""
        SELECT sb.frame
          FROM syntactic_behaviours AS sb
          JOIN syntactic_behaviour_senses AS sbs
            ON sbs.syntactic_behaviour_rowid = sb.rowid
          JOIN senses AS s ON s.rowid = sbs.sense_rowid
          JOIN lexicons AS lex ON lex.rowid = sb.lexicon_rowid
         WHERE s.id = ?
           AND lex.specifier IN ({_qs(lexicons)})
    """
    return [row[0] for row in conn.execute(query, (sense_id, *lexicons))]


def _get_senses(
    id: str, sourcetype: str, lexicons: Sequence[str], order_by_rank: bool = True
) -> Iterator[Sense]:
    conn = connect()
    match sourcetype:
        case "entry":
            sourcealias = "e"
        case "synset":
            sourcealias = "ss"
        case _:
            raise Error(f"invalid sense source type: {sourcetype}")
    order_col = f"{sourcetype}_rank" if order_by_rank else "rowid"
    query = f"""
        SELECT s.id, e.id, ss.id, slex.specifier
          FROM senses AS s
          JOIN entries AS e
            ON e.rowid = s.entry_rowid
          JOIN synsets AS ss
            ON ss.rowid = s.synset_rowid
          JOIN lexicons AS slex
            ON slex.rowid = s.lexicon_rowid
         WHERE {sourcealias}.id = ?
           AND slex.specifier IN ({_qs(lexicons)})
         ORDER BY s.{order_col}
    """
    return conn.execute(query, (id, *lexicons))


def get_entry_senses(
    sense_id: str, lexicons: Sequence[str], order_by_rank: bool = True
) -> Iterator[Sense]:
    yield from _get_senses(sense_id, "entry", lexicons, order_by_rank)


def get_synset_members(
    synset_id: str, lexicons: Sequence[str], order_by_rank: bool = True
) -> Iterator[Sense]:
    yield from _get_senses(synset_id, "synset", lexicons, order_by_rank)


def get_sense_relations(
    sense_id: str,
    relation_types: Collection[str],
    lexicons: Sequence[str],
    target_lexicons: Sequence[str],
) -> Iterator[_Sense_Relation]:
    params: list = []
    constraint = ""
    if relation_types and "*" not in relation_types:
        constraint = f"WHERE type IN ({_qs(relation_types)})"
        params.extend(relation_types)
    params.extend(lexicons)
    params.extend(target_lexicons)
    params.append(sense_id)
    query = f"""
        WITH
          rt(rowid, type) AS
            (SELECT rowid, type FROM relation_types {constraint}),
          lexrowids(rowid) AS
            (SELECT rowid FROM lexicons WHERE specifier IN ({_vs(lexicons)})),
          tgtlexrowids(rowid) AS
            (SELECT rowid FROM lexicons WHERE specifier IN ({_vs(target_lexicons)}))
        SELECT DISTINCT rel.type, rel.lexicon, rel.metadata,
                        s.id, e.id, ss.id, slex.specifier
          FROM (SELECT rt.type,
                       lex.specifier AS lexicon,
                       srel.metadata AS metadata,
                       target_rowid
                  FROM sense_relations AS srel
                  JOIN rt ON srel.type_rowid = rt.rowid
                  JOIN lexicons AS lex ON srel.lexicon_rowid = lex.rowid
                  JOIN senses AS s ON s.rowid = srel.source_rowid
                 WHERE s.id = ?
                   AND srel.lexicon_rowid IN lexrowids
               ) AS rel
          JOIN senses AS s
            ON s.rowid = rel.target_rowid
           AND s.lexicon_rowid IN tgtlexrowids
          JOIN lexicons AS slex
            ON slex.rowid = s.lexicon_rowid
          JOIN entries AS e
            ON e.rowid = s.entry_rowid
          JOIN synsets AS ss
            ON ss.rowid = s.synset_rowid
    """
    rows: Iterator[_Sense_Relation] = connect().execute(query, params)
    yield from rows


def get_sense_synset_relations(
    sense_id: str,
    relation_types: Collection[str],
    lexicons: Sequence[str],
    target_lexicons: Sequence[str],
) -> Iterator[_Synset_Relation]:
    params: list = []
    constraint = ""
    if "*" not in relation_types:
        constraint = f"WHERE type IN ({_qs(relation_types)})"
        params.extend(relation_types)
    params.extend(lexicons)
    params.extend(target_lexicons)
    params.append(sense_id)
    query = f"""
        WITH
          rt(rowid, type) AS
            (SELECT rowid, type FROM relation_types {constraint}),
          lexrowids(rowid) AS
            (SELECT rowid FROM lexicons WHERE specifier IN ({_vs(lexicons)})),
          tgtlexrowids(rowid) AS
            (SELECT rowid FROM lexicons WHERE specifier IN ({_vs(target_lexicons)}))
        SELECT DISTINCT rel.type, rel.lexicon, rel.metadata,
                        rel.source_rowid, tgt.id, tgt.pos,
                        (SELECT ilis.id FROM ilis WHERE ilis.rowid = tgt.ili_rowid),
                        tgtlex.specifier
          FROM (SELECT rt.type,
                       lex.specifier AS lexicon,
                       srel.metadata AS metadata,
                       source_rowid,
                       target_rowid
                  FROM sense_synset_relations AS srel
                  JOIN rt ON srel.type_rowid = rt.rowid
                  JOIN lexicons AS lex ON srel.lexicon_rowid = lex.rowid
                  JOIN senses AS s ON s.rowid = srel.source_rowid
                 WHERE s.id = ?
                   AND srel.lexicon_rowid IN lexrowids
               ) AS rel
          JOIN synsets AS tgt
            ON tgt.rowid = rel.target_rowid
           AND tgt.lexicon_rowid IN tgtlexrowids
          JOIN lexicons AS tgtlex
            ON tgtlex.rowid = tgt.lexicon_rowid
    """
    rows: Iterator[_Synset_Relation] = connect().execute(query, params)
    yield from rows


def get_relation_targets(
    rel_table: str,
    tgt_table: str,
    lexicons: Sequence[str],
    target_lexicons: Sequence[str],
) -> set[str]:
    if rel_table not in {
        "sense_relations",
        "sense_synset_relations",
        "synset_relations",
    }:
        raise ValueError(f"invalid relation table: {rel_table}")
    if tgt_table not in ("senses", "synsets"):
        raise ValueError(f"invalid target table: {tgt_table}")
    params: list = [*lexicons, *target_lexicons]
    query = f"""
        WITH
          lexrowids(rowid) AS
            (SELECT rowid FROM lexicons WHERE specifier IN ({_vs(lexicons)})),
          tgtlexrowids(rowid) AS
            (SELECT rowid FROM lexicons WHERE specifier IN ({_vs(target_lexicons)}))
        SELECT DISTINCT tgt.id
          FROM {rel_table} AS srel
          JOIN lexicons AS lex ON srel.lexicon_rowid = lex.rowid
          JOIN {tgt_table} AS tgt ON tgt.rowid = srel.target_rowid
         WHERE srel.lexicon_rowid IN lexrowids
           AND tgt.lexicon_rowid IN tgtlexrowids
    """
    rows: Iterator[str] = connect().execute(query, params)
    return {row[0] for row in rows}


_SANITIZED_METADATA_TABLES = {
    # 'ilis': 'ilis',
    # 'proposed_ilis': 'proposed_ilis',
    # 'lexicons': 'lexicons',
    "entries": "entries",
    "senses": "senses",
    "synsets": "synsets",
    # 'sense_relations': 'sense_relations',
    # 'sense_synset_relations': 'sense_synset_relations',
    # 'synset_relations': 'synset_relations',
    # 'sense_examples': 'sense_examples',
    # 'counts': 'counts',
    # 'synset_examples': 'synset_examples',
    # 'definitions': 'definitions',
}


def get_metadata(id: str, lexicon: str, table: str) -> Metadata:
    tablename = _SANITIZED_METADATA_TABLES.get(table)
    if tablename is None:
        raise Error(f"'{table}' does not contain metadata")
    query = f"""
        SELECT tbl.metadata
          FROM {tablename} AS tbl
          JOIN lexicons AS lex ON lex.rowid = lexicon_rowid
         WHERE tbl.id=?
           AND lex.specifier = ?
    """
    return cast(
        "Metadata",
        connect().execute(query, (id, lexicon)).fetchone()[0] or {},
    )  # TODO: benchmark using a TypeGuard


def get_ili_metadata(id: str) -> Metadata:
    query = "SELECT metadata FROM ilis WHERE id = ?"
    return cast(
        "Metadata",
        connect().execute(query, (id,)).fetchone()[0] or {},
    )


def get_proposed_ili_metadata(synset: str, lexicon: str) -> Metadata:
    query = """
        SELECT pili.metadata
          FROM proposed_ilis AS pili
          JOIN synsets AS ss ON ss.rowid = synset_rowid
          JOIN lexicons AS lex ON lex.rowid = ss.lexicon_rowid
         WHERE ss.id = ?
           AND lex.specifier = ?
    """
    return cast(
        "Metadata",
        connect().execute(query, (synset, lexicon)).fetchone()[0] or {},
    )


_SANITIZED_LEXICALIZED_TABLES = {
    "senses": ("senses", "sense_rowid"),
    "synsets": ("synsets", "synset_rowid"),
}


def get_lexicalized(id: str, lexicon: str, table: str) -> bool:
    conn = connect()
    if table not in _SANITIZED_LEXICALIZED_TABLES:
        raise Error(f"'{table}' does not mark lexicalization")
    tablename, column = _SANITIZED_LEXICALIZED_TABLES[table]
    if not id or not lexicon:
        return False
    query = f"""
        SELECT NOT EXISTS
               (SELECT {column}
                  FROM unlexicalized_{tablename} AS un
                  JOIN {tablename} AS tbl ON tbl.rowid = un.{column}
                  JOIN lexicons AS lex ON lex.rowid = tbl.lexicon_rowid
                 WHERE tbl.id = ?
                   AND lex.specifier = ?)
    """
    return bool(conn.execute(query, (id, lexicon)).fetchone()[0])


def get_adjposition(sense_id: str, lexicon: str) -> str | None:
    conn = connect()
    query = """
        SELECT adjposition
          FROM adjpositions
          JOIN senses AS s ON s.rowid = sense_rowid
          JOIN lexicons AS lex ON lex.rowid = s.lexicon_rowid
         WHERE s.id = ?
           AND lex.specifier = ?
    """
    row = conn.execute(query, (sense_id, lexicon)).fetchone()
    if row:
        return row[0]
    return None


def get_sense_counts(sense_id: str, lexicons: Sequence[str]) -> list[_Count]:
    conn = connect()
    query = f"""
        SELECT c.count, lex.specifier, c.metadata
          FROM counts AS c
          JOIN senses AS s ON s.rowid = c.sense_rowid
          JOIN lexicons AS lex ON lex.rowid = c.lexicon_rowid
         WHERE s.id = ?
           AND lex.specifier IN ({_qs(lexicons)})
    """
    rows: list[_Count] = conn.execute(query, (sense_id, *lexicons)).fetchall()
    return rows


def get_lexfile(synset_id: str, lexicon: str) -> str | None:
    conn = connect()
    query = """
        SELECT lf.name
          FROM lexfiles AS lf
          JOIN synsets AS ss ON ss.lexfile_rowid = lf.rowid
          JOIN lexicons AS lex ON lex.rowid = ss.lexicon_rowid
         WHERE ss.id = ?
           AND lex.specifier = ?
    """
    row = conn.execute(query, (synset_id, lexicon)).fetchone()
    if row is not None and row[0] is not None:
        return row[0]
    return None


def get_entry_index(entry_id: str, lexicon: str) -> str | None:
    conn = connect()
    query = """
        SELECT idx.lemma
          FROM entries AS e
          JOIN lexicons AS lex ON lex.rowid = e.lexicon_rowid
          JOIN entry_index AS idx ON idx.entry_rowid = e.rowid
         WHERE e.id = ?
           AND lex.specifier = ?
    """
    row = conn.execute(query, (entry_id, lexicon)).fetchone()
    if row is not None:
        return row[0]
    return None


def get_sense_n(sense_id: str, lexicon: str) -> int | None:
    conn = connect()
    query = """
        SELECT s.entry_rank
          FROM senses AS s
          JOIN lexicons AS lex ON lex.rowid = s.lexicon_rowid
         WHERE s.id = ?
           AND lex.specifier = ?
    """
    row = conn.execute(query, (sense_id, lexicon)).fetchone()
    if row is not None:
        return row[0]
    return None


def _qs(xs: Collection) -> str:
    return ",".join("?" * len(xs))


def _vs(xs: Collection) -> str:
    return ",".join(["(?)"] * len(xs))


def _kws(xs: Collection) -> str:
    return ",".join(f":{x}" for x in xs)


def _query_forms(
    forms: Sequence[str],
    normalized: bool,
    search_all_forms: bool,
    indexed: bool = True,
) -> tuple[list[str], str]:
    or_norm = "OR f.normalized_form IN wordforms" if normalized else ""
    and_rank = "" if search_all_forms else "AND f.rank = 0"
    ctes: list[str] = [
        f"wordforms(s) AS (VALUES {_vs(forms)})",
        f"""matched_entries(rowid) AS
          (SELECT f.entry_rowid
             FROM forms AS f
            WHERE (f.form IN wordforms {or_norm}) {and_rank})""",
    ]
    subquery = "matched_entries"
    if indexed:
        subquery = """\
          (SELECT rowid
             FROM matched_entries
            UNION SELECT idx.entry_rowid
                    FROM matched_entries AS _me
                    JOIN entry_index AS _idx ON _idx.entry_rowid = _me.rowid
                    JOIN entry_index AS idx ON idx.lemma = _idx.lemma)
        """
    return ctes, subquery


def _build_entry_conditions(
    forms: Sequence[str],
    pos: str | None,
    lexicons: Sequence[str],
    normalized: bool,
    search_all_forms: bool,
) -> tuple[str, list[str], list[str], list[str]]:
    """Build CTE, conditions, and parameters for entry-based queries.

    Returns:
        tuple of (cte, conditions, params)
    """
    ctes: list[str] = []
    cteparams: list[str] = []
    subquery = ""
    conditions: list[str] = []
    condparams: list[str] = []

    if lexicons:
        ctes.append(f"lexspecs(s) AS (VALUES {_vs(lexicons)})")
        conditions.append("lex.specifier IN lexspecs")
        cteparams.extend(lexicons)
    if forms:
        ctes_, subquery = _query_forms(forms, normalized, search_all_forms)
        ctes.extend(ctes_)
        conditions.append(f"e.rowid IN {subquery}")
        cteparams.extend(forms)
    if pos:
        conditions.append("e.pos = ?")
        condparams.append(pos)

    cte = ""
    if ctes:
        cte = "WITH " + ",\n               ".join(ctes)

    return cte, cteparams, conditions, condparams
