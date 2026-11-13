# Armazena sessões e seus índices no Redis, usando expiração e operações atômicas.
import time
from hashlib import sha256

from database import get_redis_client


class SessionRepository:
    # O prazo padrão da sessão é de uma hora, expresso em segundos.
    ttl = 3600

    def __init__(self, client=None):
        self.client = client if client is not None else get_redis_client()

    # Grava usuário e horário da sessão e atualiza seu índice com prazo de expiração.
    def create(self, session_id, user_id):
        key = f"session:{session_id}"
        index = f"user_sessions:{user_id}"
        # A pipeline agrupa a gravação da sessão, do índice e dos respectivos prazos.
        with self.client.pipeline() as pipe:
            pipe.hset(key, mapping={"user_id": user_id, "created_at": int(time.time())})
            pipe.expire(key, self.ttl)
            pipe.sadd(index, session_id)
            pipe.expire(index, self.ttl)
            pipe.execute()

    # Consulta o usuário do token e decodifica a resposta binária do Redis.
    def get_by_id(self, session_id):
        user_id = self.client.hget(f"session:{session_id}", "user_id")
        return user_id.decode() if user_id else None

    # Lista as sessões do usuário com referências SHA-256 em vez de expor os tokens.
    def get_all_session_for_user(self, session_id):
        rows = self._active_sessions(session_id)
        if rows is None:
            return None
        # A referência hash identifica a sessão na interface sem entregar seu token de autenticação.
        return [
            {
                "reference": sha256(token).hexdigest(),
                "created_at": int(created_at) if created_at else None,
                "current": bool(current),
            }
            for token, created_at, current in rows
        ]

    # Executa Lua no Redis para listar sessões do usuário e limpar referências expiradas do índice.
    def _active_sessions(self, session_id):
        return self.client.eval("""
            local user = redis.call('HGET', KEYS[1], 'user_id')
            if not user then return nil end
            local index = 'user_sessions:' .. user
            local active = {}
            for _, id in ipairs(redis.call('SMEMBERS', index)) do
                local key = 'session:' .. id
                if redis.call('HGET', key, 'user_id') == user then
                    table.insert(active, {
                        id,
                        redis.call('HGET', key, 'created_at') or '',
                        id == ARGV[1] and 1 or 0
                    })
                else
                    redis.call('SREM', index, id)
                end
            end
            return active
        """, 1, f"session:{session_id}", session_id)

    # Localiza outra sessão pela referência e solicita a remoção após conferir a propriedade.
    def revoke_other(self, session_id, reference):
        for token, _, current in self._active_sessions(session_id) or ():
            if not current and sha256(token).hexdigest() == reference:
                return self._delete_owned_session(session_id, token)
        return False

    # Solicita a remoção da própria sessão autenticada.
    def delete(self, session_id):
        return self._delete_owned_session(session_id, session_id)

    # Confere as duas sessões e ajusta a presença em uma operação atômica no Redis.
    def _delete_owned_session(self, session_id, target):
        # Recheck both sessions atomically in case either expired after listing.
        return bool(self.client.eval("""
            local user = redis.call('HGET', KEYS[1], 'user_id')
            if not user then return 0 end
            local index = 'user_sessions:' .. user
            local target = ARGV[1]
            local target_key = 'session:' .. target
            if redis.call('HGET', target_key, 'user_id') ~= user then return 0 end
            redis.call('DEL', target_key)
            redis.call('SREM', index, target)
            local remaining = 0
            local clock = redis.call('TIME')
            local now = tonumber(clock[1]) * 1000 + math.floor(tonumber(clock[2]) / 1000)
            for _, id in ipairs(redis.call('SMEMBERS', index)) do
                local key = 'session:' .. id
                local seen = redis.call('HGET', key, 'presence_until')
                if seen then
                    local ttl = redis.call('PTTL', key)
                    remaining = math.max(remaining, math.min(tonumber(seen) - now, ttl))
                end
            end
            if remaining > 0 then
                redis.call('SET', 'presence:' .. user, 'online', 'PX', remaining)
            else
                redis.call('DEL', 'presence:' .. user)
            end
            return 1
        """, 1, f"session:{session_id}", target))
