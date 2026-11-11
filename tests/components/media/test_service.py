from pathlib import Path
from unittest.mock import Mock

import pytest
from bson import ObjectId

from services.shared.media_errors import MediaValidationError
from services.shared.media_service import MediaService


ASSETS_DIRECTORY = Path(__file__).parent / "assets"
IMAGE_CASES = (
    ("profile-test.svg", "usuario", "imagem_perfil"),
    ("post-test.svg", "post", "imagem_publicacao"),
)


@pytest.mark.parametrize(
    ("asset_name", "owner_type", "media_type"),
    IMAGE_CASES,
)
def test_service_passes_real_image_data_to_repository(
    asset_name: str,
    owner_type: str,
    media_type: str,
) -> None:
    repository = Mock()
    owner_id = ObjectId()
    content = (ASSETS_DIRECTORY / asset_name).read_bytes()
    repository.create.side_effect = lambda data: {
        "media_id": str(ObjectId()),
        "filename": data["filename"],
        "length": len(data["content"]),
        "metadata": {
            **data["metadata"],
            "proprietario_id": str(data["metadata"]["proprietario_id"]),
        },
    }
    service = MediaService(repository)
    payload = {
        "filename": asset_name,
        "content": content,
        "metadata": {
            "proprietario_tipo": owner_type,
            "tipo_mime": "image/svg+xml",
            "tipo": media_type,
            "visibilidade": "publica",
            "proprietario_id": str(owner_id),
        },
    }

    result = service.create(payload)

    repository.create.assert_called_once()
    repository_data = repository.create.call_args.args[0]
    assert repository_data["content"] == content
    assert repository_data["metadata"]["proprietario_id"] == owner_id
    assert result["filename"] == asset_name
    assert result["length"] == len(content)
    assert result["metadata"]["proprietario_id"] == str(owner_id)


def test_service_reports_invalid_filter_as_media_validation_error() -> None:
    repository = Mock()
    service = MediaService(repository)

    with pytest.raises(MediaValidationError, match="unknown"):
        service.list({"unknown": "value"})

    repository.list.assert_not_called()
