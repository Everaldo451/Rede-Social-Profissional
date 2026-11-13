# Testes de persistência de mídias no GridFS e de tradução das falhas do MongoDB.
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from bson import ObjectId
from pymongo.errors import ServerSelectionTimeoutError

from database import get_mongo_database
from repositories.shared.media_repository import MediaRepository
from services.shared.media_errors import MediaPersistenceError


ASSETS_DIRECTORY = Path(__file__).parent / "assets"
IMAGE_CASES = (
    ("profile-test.svg", "usuario", "imagem_perfil"),
    ("post-test.svg", "post", "imagem_publicacao"),
)
GRIDFS_COLLECTIONS = ("midias.files", "midias.chunks")


# Prepara a limpeza das coleções de mídia usadas pelos testes.
@pytest.fixture(autouse=True)
def clear_gridfs_collections() -> Iterator[None]:
    database = get_mongo_database()
    for collection_name in GRIDFS_COLLECTIONS:
        database.drop_collection(collection_name)
    try:
        yield
    finally:
        for collection_name in GRIDFS_COLLECTIONS:
            database.drop_collection(collection_name)


# Disponibiliza a instância do repositório de mídia para os cenários de teste.
@pytest.fixture
def media_repository() -> MediaRepository:
    return MediaRepository(get_mongo_database())


# Verifica se erros do driver são convertidos em erros de persistência de mídia.
def test_repository_wraps_mongodb_errors() -> None:
    database = MagicMock()
    with patch("repositories.shared.media_repository.GridFSBucket") as bucket:
        bucket.return_value.upload_from_stream_with_id.side_effect = (
            ServerSelectionTimeoutError("database connection details")
        )
        repository = MediaRepository(database)

        with pytest.raises(MediaPersistenceError) as exc_info:
            repository.create(
                {
                    "filename": "profile.svg",
                    "content": b"<svg></svg>",
                    "metadata": {},
                }
            )

    assert isinstance(exc_info.value.__cause__, ServerSelectionTimeoutError)


# Exercita criação, consulta, atualização e exclusão com imagens reais de teste.
@pytest.mark.parametrize(
    ("asset_name", "owner_type", "media_type"),
    IMAGE_CASES,
)
def test_repository_gridfs_crud_with_real_image_assets(
    media_repository: MediaRepository,
    asset_name: str,
    owner_type: str,
    media_type: str,
) -> None:
    content = (ASSETS_DIRECTORY / asset_name).read_bytes()
    owner_id = ObjectId()
    media_data = {
        "filename": asset_name,
        "content": content,
        "metadata": {
            "proprietario_tipo": owner_type,
            "tipo_mime": "image/svg+xml",
            "tipo": media_type,
            "visibilidade": "privada",
            "proprietario_id": owner_id,
        },
    }

    created = media_repository.create(media_data)
    media_id = created["media_id"]

    assert created["filename"] == asset_name
    assert created["metadata"]["proprietario_id"] == str(owner_id)
    assert created["length"] == len(content)
    assert media_repository.database["midias.chunks"].count_documents(
        {"files_id": ObjectId(media_id)}
    ) > 0

    downloaded = media_repository.get_by_id(media_id)
    assert downloaded is not None
    assert downloaded["content"] == content

    found = media_repository.get_one(
        {"proprietario_id": str(owner_id), "tipo": media_type}
    )
    assert found is not None
    assert found["media_id"] == media_id
    assert found["content"] == content

    listed = media_repository.list({"proprietario_tipo": owner_type})
    assert any(item["media_id"] == media_id for item in listed)

    updated = media_repository.update(
        media_id,
        {
            "filename": f"updated-{asset_name}",
            "metadata": {**media_data["metadata"], "visibilidade": "publica"},
        },
    )
    assert updated is not None
    assert updated["filename"] == f"updated-{asset_name}"
    assert updated["metadata"]["visibilidade"] == "publica"

    assert media_repository.delete(media_id) is True
    assert media_repository.get_by_id(media_id) is None
    assert media_repository.database["midias.files"].count_documents(
        {"_id": ObjectId(media_id)}
    ) == 0
    assert media_repository.database["midias.chunks"].count_documents(
        {"files_id": ObjectId(media_id)}
    ) == 0
