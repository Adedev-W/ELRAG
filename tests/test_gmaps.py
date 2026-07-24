from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

import httpx

from elrag.lib.gmaps import (
    DEFAULT_ROUTE_FIELDS,
    DEFAULT_TEXT_SEARCH_FIELDS,
    GoogleMapsService,
)


class GoogleMapsServiceTest(unittest.IsolatedAsyncioTestCase):
    def test_constructor_requires_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "GMAPS_API_KEY is not configured"):
                GoogleMapsService(api_key="")

    async def test_autocomplete_posts_to_places_autocomplete(self) -> None:
        requests = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"suggestions": []})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GoogleMapsService(api_key="test-key", client=client)
            response = await service.autocomplete(
                "Dutamall pky",
                session_token="token-1",
                language_code="id",
                region_code="ID",
            )

        self.assertEqual({"suggestions": []}, response)
        self.assertEqual("/v1/places:autocomplete", requests[0].url.path)
        self.assertEqual("test-key", requests[0].headers["X-Goog-Api-Key"])
        self.assertEqual(
            {
                "input": "Dutamall pky",
                "sessionToken": "token-1",
                "languageCode": "id",
                "regionCode": "ID",
            },
            json.loads(requests[0].content),
        )

    async def test_text_search_sends_field_mask(self) -> None:
        requests = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"places": []})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GoogleMapsService(api_key="test-key", client=client)
            response = await service.text_search(
                "coffee in Palangkaraya",
                max_result_count=3,
                language_code="id",
                region_code="ID",
            )

        self.assertEqual({"places": []}, response)
        self.assertEqual("/v1/places:searchText", requests[0].url.path)
        self.assertEqual(
            ",".join(DEFAULT_TEXT_SEARCH_FIELDS),
            requests[0].headers["X-Goog-FieldMask"],
        )
        self.assertEqual(
            {
                "textQuery": "coffee in Palangkaraya",
                "maxResultCount": 3,
                "languageCode": "id",
                "regionCode": "ID",
            },
            json.loads(requests[0].content),
        )

    async def test_place_detail_uses_place_path_and_api_key(self) -> None:
        requests = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"id": "abc"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GoogleMapsService(api_key="test-key", client=client)
            response = await service.place_detail(
                "places/abc",
                fields=("id", "displayName"),
                language_code="id",
            )

        self.assertEqual({"id": "abc"}, response)
        self.assertEqual("/v1/places/abc", requests[0].url.path)
        self.assertEqual("id", requests[0].url.params["languageCode"])
        self.assertEqual("test-key", requests[0].headers["X-Goog-Api-Key"])
        self.assertEqual("id,displayName", requests[0].headers["X-Goog-FieldMask"])

    async def test_distance_time_posts_to_routes_with_field_mask(self) -> None:
        requests = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "routes": [
                        {
                            "distanceMeters": 1200,
                            "duration": "600s",
                            "staticDuration": "650s",
                        }
                    ]
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GoogleMapsService(api_key="test-key", client=client)
            response = await service.distance_time("Jakarta", "Bandung")

        self.assertEqual(1200, response["routes"][0]["distanceMeters"])
        self.assertEqual("/directions/v2:computeRoutes", requests[0].url.path)
        self.assertEqual(
            ",".join(DEFAULT_ROUTE_FIELDS),
            requests[0].headers["X-Goog-FieldMask"],
        )
        self.assertEqual(
            {
                "origin": {"address": "Jakarta"},
                "destination": {"address": "Bandung"},
                "travelMode": "DRIVE",
                "routingPreference": "TRAFFIC_AWARE",
            },
            json.loads(requests[0].content),
        )


if __name__ == "__main__":
    unittest.main()
