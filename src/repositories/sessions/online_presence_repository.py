# Consulta e atualiza chaves temporárias de presença dos usuários no Redis.
from database import get_redis_client


class OnlinePresenceRepository:
    def __init__(self, client=None):
        self.client = client if client is not None else get_redis_client()

    # Considera online o usuário cuja chave de presença ainda existe.
    def get_by_user_id(self, user_id):
        return bool(self.client.exists(f"presence:{user_id}"))

    # Consulta várias chaves de uma vez e devolve o conjunto de usuários online.
    def get_online_users(self, user_ids):
        if not user_ids:
            return set()
        values = self.client.mget([f"presence:{user_id}" for user_id in user_ids])
        return {user_id for user_id, value in zip(user_ids, values) if value == b"online"}

    # Atualiza presença e último acesso por Lua; a atividade explícita também renova a sessão.
    def update_last_seen(self, session_id, inactivity_ttl, *, activity=False):
        # O script executa no Redis sem intercalar comandos de outras operações durante sua execução.
        return bool(self.client.eval("""
            local user = redis.call('HGET', KEYS[1], 'user_id')
            if not user then return 0 end
            if ARGV[1] == '1' then
                redis.call('EXPIRE', KEYS[1], ARGV[2])
                redis.call('EXPIRE', 'user_sessions:' .. user, ARGV[2])
            end
            local clock = redis.call('TIME')
            local now = tonumber(clock[1]) * 1000 + math.floor(tonumber(clock[2]) / 1000)
            local ttl = math.min(60000, redis.call('PTTL', KEYS[1]))
            if ttl < 1 then return 0 end
            redis.call('HSET', KEYS[1], 'presence_until', now + ttl)
            local presence = 'presence:' .. user
            if redis.call('PTTL', presence) <= ttl then
                redis.call('SET', presence, 'online', 'PX', ttl)
            end
            redis.call('SET', 'presence:last_seen:' .. user, clock[1])
            return 1
        """, 1, f"session:{session_id}", int(activity), inactivity_ttl))
