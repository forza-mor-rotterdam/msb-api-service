from schema_types import MorMeldingAanmakenRequest, MorMeldingVolgenRequest, ResponseOfUpdate, ResponseOfInsert, ResponseOfGetMorMeldingen, MorMelding, MorMeldingenWrapper
import os
import json
from services.main import BaseService
from services.mor_core import MeldingenService
from urllib.parse import urlparse
import logging
import re
import requests
from typing import Union
from services.onderwerpen import OnderwerpenService
import copy
from datetime import datetime, timedelta
import pytz
import validators
from urllib.parse import quote
from zeep.helpers import serialize_object
from collections import OrderedDict
import validators


logger = logging.getLogger(__name__)


class OntdbblRService(BaseService):
    _v = "v1"
    _api_path: str = f"/api/{_v}"

    def _relatieve_url(self, url: str):
        if not isinstance(url, str):
            raise OntdbblRService.BasisUrlFout("Url kan niet None zijn")
        url_o = urlparse(url)
        if not url_o.scheme and not url_o.netloc:
            return url
        if f"{url_o.scheme}://{url_o.netloc}" == self._api_base_url:
            return f"{url_o.path}{url_o.query}"
        raise OntdbblRService.BasisUrlFout(
            f"url: {url}, basis_url: {self._api_base_url}"
        )
    
    def _get_token(self):
        meldingen_token = None
        if not meldingen_token:
            meldingen_username = os.environ.get("MELDINGEN_USERNAME", "")
            email = meldingen_username
            if not validators.email(email):
                email = f"{meldingen_username}@forzamor.nl"

            token_url = f"{os.environ.get('MELDINGEN_URL', '')}/api-token-auth/"
            print("token_url")
            print(token_url)
            password = os.environ.get("MELDINGEN_PASSWORD", "")
            token_response = requests.post(
                token_url,
                json={
                    "username": email,
                    "password": password,
                },
            )
            logger.info(f"token response status code: {token_response.status_code}")
            if token_response.status_code == 200:
                meldingen_token = token_response.json().get("token")
            else:
                raise OntdbblRService.DataOphalenFout(
                    f"status code: {token_response.status_code}, response text: {token_response.text}"
                )
        print(meldingen_token)
        return meldingen_token

    def _get_headers(self):
        headers = {"Authorization": f"Token {self._get_token()}"}
        return headers

    def _get_url(self, url):
        return f"{self._api_base_url}{self._relatieve_url(url)}"

    def _to_json(self, response):
        try:
            return response.json()
        except Exception:
            raise OntdbblRService.ToJsonFout(
                f"Json antwoord verwacht, antwoord tekst: {response.text}"
            )

    def __init__(self, *args, **kwargs: dict):
        self._api_base_url = os.environ.get("ONTDBBLR_URL")
        self._api_base_url = os.environ.get("ONTDBBLR_URL")
        super().__init__(*args, **kwargs)

    def get_onderwerp_url(self, meldr_onderwerp):
        default_onderwerp_url = f"{self._api_base_url}/api/v1/onderwerp/grofvuil-op-straat/"
        mor_categories = OnderwerpenService().get_category_url(meldr_onderwerp)
        logger.info(f"get_onderwerp_url: meldr_onderwerp={meldr_onderwerp}")
        logger.info(f"get_onderwerp_url: response={mor_categories}")
        results = mor_categories.get("results", [])
        if results:
            return results[0].get("_links", {}).get("self", default_onderwerp_url)
        return default_onderwerp_url
    
    def get_signaal_url(self, meldr_meldingsnummer):
        return f"https://meldr.rotterdam.nl/melding/{meldr_meldingsnummer}"

    def aanmaken_melding(self, mor_melding: MorMeldingAanmakenRequest, validated_address: Union[dict, None] = {}):
        existing_signalen_response = MeldingenService().bestaande_signalen(mor_melding.meldingsnummerField)
        logger.info("bestaande signalen status_code: %s", existing_signalen_response.status_code)
        if existing_signalen_response.status_code == 200:
            existing_signalen_response_dict = self._to_json(existing_signalen_response)
            signalen = existing_signalen_response_dict.get("results", [])
            logger.info("bestaande signalen: %s", signalen)
            if signalen:
                return {
                    "messagesField": None,
                    "serviceResultField": {
                        "codeField": "A107",
                        "errorsField": None,
                        "messageField": f"MOR Melding {mor_melding.meldingsnummerField} bestaat al onder MOR CORE url {signalen[0].get('_links', {}).get('melding')}"
                    },
                    "dataField": None,
                    "newIdField": None
                }



        mor_melding_dict = dict(mor_melding)
        fotos = mor_melding_dict.pop("fotosField", [])
        melderEmailField = mor_melding_dict.get("melderEmailField") if validators.email(mor_melding_dict.get("melderEmailField")) else None
        omschrijving_kort = mor_melding_dict.get("omschrijvingField", "") if mor_melding_dict.get("omschrijvingField") else "- geen korte omschrijving beschikbaar -"

        geometrie = None
        try:
            omschrijving_kort_json = json.loads(omschrijving_kort)
            omschrijving_kort = omschrijving_kort_json["orgineleOmschrijving"]
            geometrie = f"POINT({omschrijving_kort_json['longitude']} {omschrijving_kort_json['latitude']})"
        except Exception:
            ...

        data = {
            "signaal_url": self.get_signaal_url(mor_melding_dict.get('meldingsnummerField')),
            "bron_id": "MeldR",
            "bron_signaal_id": mor_melding_dict.get('meldingsnummerField'),
            "melder": {
                "naam": mor_melding_dict.get("melderNaamField"),
                "email": melderEmailField,
                "telefoonnummer": mor_melding_dict.get("melderTelefoonField"),
            },
            "origineel_aangemaakt": mor_melding_dict.get("aanmaakDatumField"),
            "onderwerpen": [{"bron_url":self.get_onderwerp_url(mor_melding_dict.get("onderwerpField"))}],
            "omschrijving_kort": omschrijving_kort[:500],
            "omschrijving": mor_melding_dict.get("aanvullendeInformatieField", "")[:5000],
            "meta": mor_melding_dict,
            "meta_uitgebreid": {},
            "adressen": [
                {
                    "plaatsnaam": "Rotterdam",
                    "straatnaam": mor_melding_dict.get("straatnaamField"),
                    "huisnummer": mor_melding_dict.get("huisnummerField"),
                },
            ],
        }
        if validated_address:
            logger.info(f"new geo: {geometrie}")
            logger.info(f"existing geo: {validated_address.get('geometrie')}")
            data.update({
                "adressen": [
                    {
                        "plaatsnaam": validated_address.get("woonplaats"),
                        "straatnaam": validated_address.get("straatnaam"),
                        "huisnummer": validated_address.get("huisnummer"),
                        "huisletter": validated_address.get("huisletter"),
                        "toevoeging": validated_address.get("huisnummer_toevoeging"),
                        "postcode": validated_address.get("postcode"),
                        "buurtnaam": validated_address.get("buurtnaam"),
                        "wijknaam": validated_address.get("wijknaam"),
                        "geometrie": geometrie if geometrie else validated_address.get("geometrie"),
                    },
                ]
            })
        data["bijlagen"] = [{"bestand": file} for file in fotos]

        response = self._do_request(
            f"{self._api_path}/signaal/",
            method="post",
            data=data,
        )
        if response.status_code == 201:
            response_dict = self._to_json(response)
            logger.info("signaal_aanmaken antwoord: %s", response_dict)
            response_dict.update({
                "messagesField": None,
                "serviceResultField": {
                    "codeField": "201",
                    "errorsField": None,
                    "messageField": "Het signaal is aangemaakt in MOR CORE",
                },
                "dataField": copy.deepcopy(response_dict),
                "newIdField": response_dict.get("_links", {}).get("melding"),
            })
            return response_dict

        logentry = f"morcore signaal_aanmaken error: status code: {response.status_code}, text: {response.text}"
        logger.error(logentry)
        return serialize_object(OrderedDict([
            ("serviceResultField", OrderedDict([('codeField', '000'), ('errorsField', OrderedDict([('Error', [logentry])])), ('messageField', None)])),
            ("messagesField", None),
            ("dataField", None),
            ("newIdField", None),
        ]))
    