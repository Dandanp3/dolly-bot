import unicodedata

def normalize_text(text: str) -> str:
    if not text:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', text)
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return only_ascii.lower().strip()

class ServerController:
    def __init__(self, servers_collection):
        self.collection = servers_collection

    async def get_or_create_server(self, server_id: int) -> dict:
        server = await self.collection.find_one({"server_id": server_id})
        if not server:
            server = {
                "server_id": server_id,
                "economy": {},
                "store": [],
                "role_boosts": {},
                "role_salaries": {}
            }
            await self.collection.insert_one(server)
        return server

    async def find_store_item(self, server_id: int, query: str) -> dict:
        server_data = await self.get_or_create_server(server_id)
        items = server_data.get("store", [])
        
        normalized_query = normalize_text(query)
        
        for item in items:
            item_name_norm = normalize_text(item.get("name", ""))
            item_id = str(item.get("id", "")).strip()
            
            if item_name_norm == normalized_query or item_id == query.strip():
                return item
                
        return None