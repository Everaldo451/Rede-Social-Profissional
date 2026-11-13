from collections import deque

from seed import (
    GRAPH_RELATIONSHIPS,
    RELATIONSHIP_PROPERTIES,
    build_graph_data,
    load_collections,
    load_relationships,
)


def test_seed_graph_contains_nodes_and_supported_relationships() -> None:
    graph_data = build_graph_data(load_collections())

    assert len(graph_data["people"]) == 50
    assert len(graph_data["organizations"]) == 10
    assert len(graph_data["skills"]) == 15
    assert set(graph_data).issuperset(
        {"people", "organizations", "skills", *GRAPH_RELATIONSHIPS}
    )
    assert graph_data["POSSUI_HABILIDADE"]
    assert graph_data["TRABALHOU_EM"]
    assert graph_data["ESTUDOU_EM"]
    assert graph_data["ENSINA"]
    assert len(graph_data["ENSINA"]) == 27
    assert len(graph_data["DESEJA_DESENVOLVER"]) == 20
    assert len(graph_data["MENTORA"]) == 20
    assert len(graph_data["CONECTADO_COM"]) == 59
    assert len(graph_data["SOLICITOU_CONEXAO"]) == 8
    assert len(graph_data["MEMBRO_DE"]) == 10
    assert set(
        graph_data["POSSUI_HABILIDADE"][0]["properties"]
    ) == {"nivel"}
    assert set(
        graph_data["TRABALHOU_EM"][0]["properties"]
    ) == {"cargo", "data_inicio", "data_fim", "atual"}
    assert set(
        graph_data["ESTUDOU_EM"][0]["properties"]
    ) == {"curso", "grau", "ano_inicio", "ano_conclusao"}
    for relationship_type, expected_properties in RELATIONSHIP_PROPERTIES.items():
        assert all(
            set(relationship["properties"]) == expected_properties
            for relationship in graph_data[relationship_type]
        )


def test_file_relationship_ids_match_seeded_nodes() -> None:
    collections = load_collections()
    file_relationships = load_relationships()
    graph_data = build_graph_data(collections, file_relationships)
    person_ids = {node["id"] for node in graph_data["people"]}
    organization_ids = {node["id"] for node in graph_data["organizations"]}

    for relationship_type, rows in file_relationships.items():
        target_ids = {
            "CONECTADO_COM": person_ids,
            "SOLICITOU_CONEXAO": person_ids,
            "MEMBRO_DE": organization_ids,
            "ENSINA": {
                node["id"] for node in graph_data["skills"]
            },
        }[relationship_type]
        assert all(row["source_id"] in person_ids for row in rows)
        assert all(row["target_id"] in target_ids for row in rows)
        assert rows


def test_pending_requests_do_not_duplicate_direct_connections() -> None:
    relationships = load_relationships()
    connection_rows = relationships["CONECTADO_COM"]
    connected_pairs = [
        frozenset((row["source_id"], row["target_id"]))
        for row in connection_rows
    ]
    request_ids = [
        row["properties"]["id"]
        for row in relationships["SOLICITOU_CONEXAO"]
    ]

    assert len(connected_pairs) == len(set(connected_pairs))
    assert len(request_ids) == len(set(request_ids))
    assert all(
        frozenset((row["source_id"], row["target_id"])) not in connected_pairs
        for row in relationships["SOLICITOU_CONEXAO"]
        if row["properties"]["status"] == "pendente"
    )


def test_seed_connections_link_the_entire_network() -> None:
    people = {
        str(user["_id"])
        for user in load_collections()["usuarios"]
    }
    adjacency = {person_id: set() for person_id in people}
    for row in load_relationships()["CONECTADO_COM"]:
        adjacency[row["source_id"]].add(row["target_id"])
        adjacency[row["target_id"]].add(row["source_id"])

    visited = set()
    queue = deque([next(iter(people))])
    while queue:
        person_id = queue.popleft()
        if person_id in visited:
            continue
        visited.add(person_id)
        queue.extend(adjacency[person_id] - visited)

    assert visited == people


def test_seeded_teachers_accept_mentorship_and_bruno_teaches_python() -> None:
    collections = load_collections()
    graph_data = build_graph_data(collections)
    users_by_id = {
        str(user["_id"]): user
        for user in collections["usuarios"]
    }
    bruno = next(
        user
        for user in collections["usuarios"]
        if user["email"] == "bruno@example.com"
    )
    assert all(
        users_by_id[relationship["source_id"]]["aceita_mentoria"]
        for relationship in graph_data["ENSINA"]
    )
    python_id = str(
        next(
            skill["_id"]
            for skill in collections["habilidades"]
            if skill["nome"] == "Python"
        )
    )
    assert bruno["aceita_mentoria"] is True
    assert bruno["habilidades"] == []
    assert any(
        relationship["source_id"] == str(bruno["_id"])
        and relationship["target_id"] == python_id
        for relationship in graph_data["ENSINA"]
    )
