from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest
from bson import ObjectId

from controllers.shared.media_controller import MediaController
from services.shared.media_errors import MediaPersistenceError
from services.shared.media_service import MediaFile


ASSETS_DIRECTORY = Path(__file__).parent / "assets"
IMAGE_CASES = (
    ("profile-test.svg", "usuario", "imagem_perfil"),
    ("post-test.svg", "post", "imagem_publicacao"),
)


def _media_payload(
    asset_name: str = "profile-test.svg",
    owner_type: str = "usuario",
    media_type: str = "imagem_perfil",
) -> dict:
    return {
        "filename": asset_name,
        "content": (ASSETS_DIRECTORY / asset_name).read_bytes(),
        "metadata": {
            "proprietario_tipo": owner_type,
            "tipo_mime": "image/svg+xml",
            "tipo": media_type,
            "visibilidade": "publica",
            "proprietario_id": str(ObjectId()),
        },
    }


def _saved_media(payload: dict) -> dict:
    return {
        "media_id": str(ObjectId()),
        "filename": payload["filename"],
        "length": len(payload["content"]),
        "chunk_size": 261120,
        "upload_date": datetime(2026, 11, 11, tzinfo=timezone.utc),
        "metadata": payload["metadata"],
    }


def test_controller_validates_before_calling_service() -> None:
    service = Mock()
    controller = MediaController(service)

    response = controller.create({"filename": "", "content": b""})

    assert response.status is False
    assert response.message.startswith("Dados inválidos:")
    service.create.assert_not_called()


def test_controller_rejects_unsupported_filter() -> None:
    service = Mock()
    controller = MediaController(service)

    response = controller.list({"$where": "true"})

    assert response.status is False
    assert response.message.startswith("Dados inválidos:")
    service.list.assert_not_called()


def test_controller_returns_standard_response_for_missing_media() -> None:
    service = Mock()
    service.get_by_id.return_value = None
    controller = MediaController(service)

    response = controller.get_by_id(str(ObjectId()))

    assert response.status is False
    assert response.data is None
    assert response.message == "Mídia não encontrada."


def test_controller_returns_standard_response_for_profile_image() -> None:
    service = Mock()
    media = {"media_id": str(ObjectId()), "filename": "profile.png"}
    service.create_profile_image.return_value = media
    controller = MediaController(service)
    upload = MediaFile("profile.png", "image/png", b"\x89PNG\r\n\x1a\n")
    owner_id = str(ObjectId())

    response = controller.create_profile_image(upload, owner_id)

    assert response.status is True
    assert response.data == media
    service.create_profile_image.assert_called_once_with(upload, owner_id)


@pytest.mark.parametrize(
    ("asset_name", "owner_type", "media_type"),
    IMAGE_CASES,
)
def test_controller_returns_realistic_created_media(
    asset_name: str,
    owner_type: str,
    media_type: str,
) -> None:
    service = Mock()
    payload = _media_payload(asset_name, owner_type, media_type)
    media = _saved_media(payload)
    service.create.return_value = media
    controller = MediaController(service)

    response = controller.create(payload)

    assert response.status is True
    assert response.data == media
    assert response.data["length"] == len(payload["content"])
    service.create.assert_called_once()
    assert service.create.call_args.args[0]["content"] == payload["content"]


def test_controller_returns_failure_when_gridfs_create_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = Mock()
    service.create.side_effect = MediaPersistenceError(
        "database connection details"
    )
    controller = MediaController(service)

    response = controller.create(_media_payload())

    assert response.status is False
    assert response.data is None
    assert response.message == (
        "Não foi possível concluir a operação de mídia. Tente novamente."
    )
    assert "database connection details" not in response.message
    assert "A media persistence operation failed" in caplog.text
