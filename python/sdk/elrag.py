from httpx import AsyncClient


class Elrag:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = AsyncClient(base_url=self.base_url)

    async def get_data(self, endpoint: str):
        response = await self.client.get(endpoint)
        response.raise_for_status()
        return response.json()

    async def post_data(self, endpoint: str, data: dict):
        response = await self.client.post(endpoint, json=data)
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()