import aiohttp
import json
import os

CACHE_PATH = "cache/pending_approvals.json"

class AuthController:
    def __init__(self, bot):
        self.bot = bot
        os.makedirs("cache", exist_ok=True)

    def save_pending_approval(self, message_id, user_id, guild_id, roblox_nick, print_url):
        data = self._load_json()
        data[str(message_id)] = {
            "user_id": user_id,
            "guild_id": guild_id,
            "roblox_nick": roblox_nick,
            "print_url": print_url
        }
        self._save_json(data)

    def get_pending_approval(self, message_id):
        return self._load_json().get(str(message_id))

    def remove_pending_approval(self, message_id):
        data = self._load_json()
        if str(message_id) in data:
            del data[str(message_id)]
            self._save_json(data)

    def _load_json(self):
        if not os.path.exists(CACHE_PATH): return {}
        try:
            with open(CACHE_PATH, "r") as f: return json.load(f)
        except: return {}

    def _save_json(self, data):
        with open(CACHE_PATH, "w") as f: json.dump(data, f, indent=4)

    async def get_roblox_avatar(self, roblox_nick):
        async with aiohttp.ClientSession() as session:
            # Pega o ID
            async with session.post("https://users.roblox.com/v1/usernames/users", 
                                    json={"usernames": [roblox_nick], "excludeBannedUsers": True}) as r:
                res = await r.json()
                if not res.get('data'): return None
                rbx_id = res['data'][0]['id']
            
            # Pega a foto de perfil
            url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={rbx_id}&size=420x420&format=Png&isCircular=false"
            async with session.get(url) as r:
                res = await r.json()
                if res.get('data'):
                    return res['data'][0]['imageUrl']
        return None