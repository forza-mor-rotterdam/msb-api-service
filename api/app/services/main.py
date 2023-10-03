from schema_types import MorMeldingAanmakenRequest, MorMeldingVolgenRequest, ResponseOfUpdate, ResponseOfInsert, ResponseOfGetMorMeldingen
from typing import Union
import requests
from requests import Request, Response
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class BaseService:
    _api_base_url = None
    _timeout: tuple[int, ...] = (15, 30)
    _data_type = "json"

    class BasisUrlFout(Exception):
        ...

    class DataOphalenFout(Exception):
        ...

    class ToJsonFout(Exception):
        ...

    def _get_headers(self):
        headers = {}
        return headers

    def _relatieve_url(self, url: str):
        if not isinstance(url, str):
            raise BaseService.BasisUrlFout("Url kan niet None zijn")
        url_o = urlparse(url)
        if not url_o.scheme and not url_o.netloc:
            return url
        if f"{url_o.scheme}://{url_o.netloc}" == self._api_base_url:
            return f"{url_o.path}{url_o.query}"
        raise BaseService.BasisUrlFout(
            f"url: {url}, basis_url: {self._api_base_url}"
        )

    def _get_url(self, url):
        return url

    def _to_json(self, response):
        try:
            return response.json()
        except Exception:
            raise BaseService.ToJsonFout(
                f"Json antwoord verwacht, antwoord tekst: {response.text}"
            )

    def _do_request(self, url, method="get", data={}, raw_response=True, extra_headers={}, params={}):
        action: Request = getattr(requests, method)
        headers = self._get_headers()
        headers.update(extra_headers)
        action_params: dict = {
            "url": self._get_url(url),
            "headers": headers,
            self._data_type: data,
            "params": params,
            "timeout": self._timeout,
        }
        response: Response = action(**action_params)
        logger.info(f"response url {response.url}")
        if raw_response:
            return response
        return response.json()


    def aanmaken_melding(self, mor_melding: MorMeldingAanmakenRequest, validated_address: Union[dict, None] = {}):
        raise NotImplementedError

    def melding_volgen(self, melding_volgen: MorMeldingVolgenRequest):
        raise NotImplementedError

    def meldingen_opvragen(self, dagenField: float, morIdField: Union[str, None] = None):
        raise NotImplementedError