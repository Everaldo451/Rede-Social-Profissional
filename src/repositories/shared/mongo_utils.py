# Compartilha a conversão de ObjectId e a adaptação do campo _id para os serviços.
from bson import ObjectId
from bson.errors import InvalidId


def to_object_id(value):
    """Converte para ObjectId; devolve None se o valor for inválido."""
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return None


def serialize(doc):
    """Troca `_id` (ObjectId) por `id` (str)."""
    if doc is None:
        return None
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc
