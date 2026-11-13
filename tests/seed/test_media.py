# Teste da geração de mídias de exemplo vinculadas aos usuários e às publicações.
from seed import ASSETS_DIR, MEDIA_ASSETS, load_collections


# Confere se cada usuário e publicação recebe o documento de mídia correspondente.
def test_seed_builds_media_for_every_user_and_post() -> None:
    collections = load_collections()
    media_documents = collections["midias.files"]
    repeated_media_documents = load_collections()["midias.files"]

    assert len(media_documents) == len(collections["usuarios"]) + len(
        collections["posts"]
    )
    assert len({media["_id"] for media in media_documents}) == len(media_documents)
    assert [media["_id"] for media in media_documents] == [
        media["_id"] for media in repeated_media_documents
    ]

    expected_owners = {
        ("usuario", user["_id"]) for user in collections["usuarios"]
    } | {("post", post["_id"]) for post in collections["posts"]}
    actual_owners = {
        (
            media["metadata"]["proprietario_tipo"],
            media["metadata"]["proprietario_id"],
        )
        for media in media_documents
    }
    assert actual_owners == expected_owners

    for media in media_documents:
        metadata = media["metadata"]
        assert metadata["tipo_mime"] == "image/svg+xml"
        assert metadata["tipo"] == (
            "imagem_perfil"
            if metadata["proprietario_tipo"] == "usuario"
            else "imagem_publicacao"
        )
        asset = ASSETS_DIR / MEDIA_ASSETS[metadata["proprietario_tipo"]]
        assert asset.read_text(encoding="utf-8").startswith("<svg")
