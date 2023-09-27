from schema_types import MorMeldingAanmakenRequest, MorMeldingVolgenRequest, ResponseOfUpdate, ResponseOfInsert, ResponseOfGetMorMeldingen
import os
from services.main import BaseService
from urllib.parse import urlparse
import logging
import re
import requests
from typing import Union


logger = logging.getLogger(__name__)


class OnderwerpenService(BaseService):
    _v = "v1"
    _api_path: str = f"/api/{_v}"

    def _get_url(self, url):
        return f"{self._api_base_url}{self._relatieve_url(url)}"

    def __init__(self, *args, **kwargs: dict):
        self._api_base_url = os.environ.get("ONDERWERPEN_URL")
        super().__init__(*args, **kwargs)

    def get_category_url(self, meldr_onderwerp):
        response = self._do_request(
            f"{self._api_path}/category/?meldr_category={meldr_onderwerp}",
        )
        if response.status_code == 200:
            return self._to_json(response)
        print(response.text)
        raise OnderwerpenService.DataOphalenFout(
            f"signaal_aanmaken: Verwacht status code 201, kreeg status code '{response.status_code}'"
        )