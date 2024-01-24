from schema_types import MorMeldingAanmakenRequest, MorMeldingVolgenRequest, ResponseOfUpdate, ResponseOfInsert, ResponseOfGetMorMeldingen, MorMelding, MorMeldingenWrapper
import os
import json
from services.main import BaseService
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


class MeldingenService(BaseService):
    _v = "v1"
    _api_path: str = f"/api/{_v}"

    def _relatieve_url(self, url: str):
        if not isinstance(url, str):
            raise MeldingenService.BasisUrlFout("Url kan niet None zijn")
        url_o = urlparse(url)
        if not url_o.scheme and not url_o.netloc:
            return url
        if f"{url_o.scheme}://{url_o.netloc}" == self._api_base_url:
            return f"{url_o.path}{url_o.query}"
        raise MeldingenService.BasisUrlFout(
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
                raise MeldingenService.DataOphalenFout(
                    f"status code: {token_response.status_code}, response text: {token_response.text}"
                )

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
            raise MeldingenService.ToJsonFout(
                f"Json antwoord verwacht, antwoord tekst: {response.text}"
            )

    def __init__(self, *args, **kwargs: dict):
        self._api_base_url = os.environ.get("MELDINGEN_URL")
        super().__init__(*args, **kwargs)

    def get_signaal_url(self, meldr_meldingsnummer):
        return f"https://meldr.rotterdam.nl/melding/{meldr_meldingsnummer}"

    @staticmethod
    def morcore_melding_to_mormelding_response(morcore_melding) -> OrderedDict:
        morcore_status_naar_meldr_status_codes = {
            "openstaand": "N",
            "in_behandeling": "I",
            "controle": "I",
            "afgehandeld": "X" if morcore_melding["resolutie"] == "niet_opgelost" else "A",
        }
        meldr_status_code = morcore_status_naar_meldr_status_codes.get(morcore_melding.get("status", {}).get("naam"))
        afgesloten_op = morcore_melding.get("afgesloten_op")
        aangepast_op = morcore_melding.get("aangepast_op")
        try:
            afgesloten_op = datetime.strptime(afgesloten_op, "%Y-%m-%dT%H:%M:%S.%f%z").strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            ...
        try:
            aangepast_op = datetime.strptime(aangepast_op, "%Y-%m-%dT%H:%M:%S.%f%z").strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            ...

        statusBerichtField = morcore_melding.get("laatste_meldinggebeurtenis", {}).get("omschrijving_extern")
        meldingsnummer = morcore_melding.get("meldingsnummer_lijst", [None])[0] if morcore_melding.get("meldingsnummer_lijst") else None
        return OrderedDict([
            ("datumAfhandelingField", afgesloten_op),
            ("datumStatusWijzigingField", aangepast_op),
            ("morIdField", meldingsnummer),
            ("msbIdField", morcore_melding.get("_links", {}).get("self")),
            ("statusBerichtField", statusBerichtField),
            ("statusField", meldr_status_code),
            ("statusOmschrijvingField", morcore_melding.get("status", {}).get("naam")),
            ("statusTemplateField", "MORR"),
        ])

    def bestaande_signalen(self, morIdField):
        signalen_response = self._do_request(
            f"{self._api_path}/signaal/",
            method="get",
            params={
                "signaal_url": {self.get_signaal_url(morIdField)},
            },
        )
        return signalen_response
    
    def melding_volgen(self, data):
        morIdField = dict(data).get("morIdField")
        errors = []
        signalen_response = self._do_request(
            f"{self._api_path}/signaal/",
            method="get",
            params={
                "signaal_url": {self.get_signaal_url(morIdField)},
            },
        )
        logger.info("meldingen_opvragen signalen response url: %s", signalen_response.url)
        melding_url = None
        if signalen_response.status_code == 200:
            signalen_response_dict = self._to_json(signalen_response)
            signalen_results = signalen_response_dict.get("results", [])
            if signalen_results:
                logger.info("morcore melding_volgen signalen: %s", signalen_results)
                melding_url = signalen_results[0].get("_links", {}).get("melding")
            else:
                logentry = f"morcore melding_volgen melding url is niet gevonden obv signaal url: {self.get_signaal_url(morIdField)}"
                logger.info(logentry)
                errors.append(logentry)
        else:
            logentry = f"morcore melding_volgen signalen error: {signalen_response.status_code}, {signalen_response.text}"
            logger.error(logentry)
            errors.append(logentry)

        if not melding_url:
            return serialize_object(OrderedDict([
                ("rowsUpdatedField", 0), 
                ("serviceResultField", OrderedDict([
                    ('codeField', '000'), 
                    ('errorsField', OrderedDict([('Error', errors)])), 
                    ('messageField', None)])),
                ("messagesField", None),
            ]))

        response = self._do_request(
            melding_url,
            method="get",
        )
        if response.status_code == 200:
            response_dict = self._to_json(response)
            logger.info("melding_volgen antwoord: %s", response_dict)
            return serialize_object(OrderedDict([
                ("rowsUpdatedField", 1), 
                ("serviceResultField", OrderedDict([
                    ('codeField', '000'), 
                    ('errorsField', OrderedDict([('Error', [])])), 
                    ('messageField', "Morcore operatie succesvol uitgevoerd.")])),
                ("messagesField", None),
            ]))
        logentry = f"morcore melding_volgen error: {response.status_code}, {response.text}"
        logger.info(logentry)
        return serialize_object(OrderedDict([
            ("rowsUpdatedField", 0), 
            ("serviceResultField", OrderedDict([
                ('codeField', '000'), 
                ('errorsField', OrderedDict([('Error', [logentry])])), 
                ('messageField', None)])),
            ("messagesField", None),
        ]))

    def meldingen_opvragen(self, dagenField: float, morIdField: Union[str, None] = None) -> ResponseOfGetMorMeldingen:
        now = datetime.now(pytz.timezone("Europe/Amsterdam"))
        dagen_eerder_dan_nu = now - timedelta(days=dagenField)
        filter_params = {
            "limit": 100,
            "ordering": "origineel_aangemaakt",
            "origineel_aangemaakt_gte": dagen_eerder_dan_nu.isoformat(),
        }
        melding_url = f"{self._api_path}/melding/"
        errors = []
        if morIdField:
            signalen_response = self._do_request(
                f"{self._api_path}/signaal/",
                method="get",
                params={
                    "signaal_url": {self.get_signaal_url(morIdField)},
                },
            )
            logger.info("meldingen_opvragen signalen response url: %s", signalen_response.url)
            if signalen_response.status_code == 200:
                signalen_response_dict = self._to_json(signalen_response)
                signalen_results = signalen_response_dict.get("results", [])
                if signalen_results:
                    logger.info("meldingen_opvragen signalen: %s", signalen_results)
                    filter_params = {}
                    melding_url = signalen_results[0].get("_links", {}).get("melding")
                else:
                    logentry = f"morcore meldingen_opvragen melding url is niet gevonden obv signaal url: {self.get_signaal_url(morIdField)}"
                    logger.info(logentry)
                    errors.append(logentry)
            else:
                logentry = f"morcore meldingen_opvragen signalen error: {signalen_response.status_code}, {signalen_response.text}"
                logger.error(logentry)
                errors.append(logentry)

        if errors:
            return serialize_object(OrderedDict([
                ("morMeldingenField", None), 
                ("serviceResultField", OrderedDict([
                    ('codeField', '000'), 
                    ('errorsField', OrderedDict([('Error', errors)])), 
                    ('messageField', None)])),
                ("messagesField", None),
            ]))
        response = self._do_request(
            melding_url,
            method="get",
            params=filter_params,
        )
        logger.info("morcore meldingen_opvragen response url: %s", response.url)
        if response.status_code == 200:
            response_dict = self._to_json(response)
            logger.info("meldingen_opvragen antwoord: %s", response_dict)
            meldingen = [response_dict] if morIdField else response_dict.get("results", [])
            logger.info("meldingen_opvragen meldingen: %s", meldingen)
            mapped_meldingen = [
                MeldingenService.morcore_melding_to_mormelding_response(m) 
                for m in meldingen
            ]
            
            logger.info("meldingen_opvragen mapped_meldingen: %s", mapped_meldingen)
            return serialize_object(OrderedDict([
                ("morMeldingenField", OrderedDict([("MorMelding", mapped_meldingen)])), 
                ("messagesField", None),
                ("serviceResultField", OrderedDict([('codeField', '000'), ('errorsField', OrderedDict([('Error', [])])), ('messageField', f'Operatie succesvol uitgevoerd. {len(mapped_meldingen)} rij(en) gevonden')])),
            ]))
        logentry = f"morcore meldingen_opvragen meldingen error: {response.status_code}, {response.text}"
        logger.error(logentry)
        return serialize_object(OrderedDict([
            ("morMeldingenField", None), 
            ("serviceResultField", OrderedDict([('codeField', '000'), ('errorsField', OrderedDict([('Error', [logentry])])), ('messageField', None)])),
            ("messagesField", None),
        ]))