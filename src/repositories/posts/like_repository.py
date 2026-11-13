from repositories.shared.mongo_utils import serialize

class LikeRepository:
    def __init__(self,database):
        self._items=database["likes"]; self._items.create_index([("user_id",1),("post_id",1)],unique=True)
    def create(self,user_id,post_id):
        doc={"user_id":user_id,"post_id":post_id}; self._items.update_one(doc,{"$setOnInsert":doc},upsert=True); return serialize(self._items.find_one(doc))
    def get_by_id(self,like_id):
        from repositories.shared.mongo_utils import to_object_id
        oid=to_object_id(like_id); return serialize(self._items.find_one({"_id":oid})) if oid else None
    def get_by_post_id(self,post_id): return [serialize(x) for x in self._items.find({"post_id":post_id})]
    def delete_user_like(self,user_id,post_id): return self._items.delete_one({"user_id":user_id,"post_id":post_id}).deleted_count>0
    def delete(self,like_id):
        from repositories.shared.mongo_utils import to_object_id
        oid=to_object_id(like_id); return bool(oid and self._items.delete_one({"_id":oid}).deleted_count)
