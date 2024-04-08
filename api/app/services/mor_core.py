import copy
import json
import logging
import os
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Union

import pytz
import requests
import validators
from schema_types import MorMeldingAanmakenRequest, ResponseOfGetMorMeldingen
from services.main import BaseService
from services.onderwerpen import OnderwerpenService
from zeep.helpers import serialize_object

logger = logging.getLogger(__name__)


class MeldingenService(BaseService):
    _v = "v1"
    _api_path: str = f"/api/{_v}"
    _enable_ontdbblr = True
    _mor_core_url = None
    _ontdbblr_url = None

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

    def _to_json(self, response):
        try:
            return response.json()
        except Exception:
            raise MeldingenService.ToJsonFout(
                f"Json antwoord verwacht, antwoord tekst: {response.text}"
            )

    def __init__(self, *args, **kwargs: dict):
        self._mor_core_url = f"{os.environ.get('MELDINGEN_URL')}{self._api_path}"
        self._ontdbblr_url = f"{os.environ.get('ONTDBBLR_URL')}{self._api_path}"
        super().__init__(*args, **kwargs)

    def get_onderwerp_url(self, meldr_onderwerp):
        default_onderwerp_url = (
            f"{self._api_base_url}/api/v1/onderwerp/grofvuil-op-straat/"
        )
        mor_categories = OnderwerpenService().get_category_url(meldr_onderwerp)
        results = mor_categories.get("results", [])
        if len(results) == 1:
            return results[0].get("_links", {}).get("self", default_onderwerp_url)
        logger.error(
            f"Er zijn meerdere onderwerpen gevonden met deze naam: {json.dumps(results, indent=4)}"
        )
        return default_onderwerp_url

    def get_signaal_url(self, meldr_meldingsnummer):
        return f"https://meldr.rotterdam.nl/melding/{meldr_meldingsnummer}"

    @staticmethod
    def morcore_signaal_to_mormelding_response(morcore_signaal) -> OrderedDict:
        morcore_melding = morcore_signaal.get("melding")
        morcore_status_naar_meldr_status_codes = {
            "openstaand": "N",
            "in_behandeling": "I",
            "controle": "I",
            "afgehandeld": (
                "X" if morcore_melding["resolutie"] == "niet_opgelost" else "A"
            ),
        }
        meldr_status_code = morcore_status_naar_meldr_status_codes.get(
            morcore_melding.get("status", {}).get("naam")
        )
        afgesloten_op = morcore_melding.get("afgesloten_op")
        aangepast_op = morcore_melding.get("aangepast_op")
        try:
            afgesloten_op = datetime.strptime(
                afgesloten_op, "%Y-%m-%dT%H:%M:%S.%f%z"
            ).strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            ...
        try:
            aangepast_op = datetime.strptime(
                aangepast_op, "%Y-%m-%dT%H:%M:%S.%f%z"
            ).strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            ...

        statusBerichtField = morcore_melding.get("laatste_meldinggebeurtenis", {}).get(
            "omschrijving_extern"
        )
        meldingsnummer = (
            morcore_signaal.get("bron_signaal_id")
            if morcore_signaal.get("bron_signaal_id")
            else morcore_melding.get("meta", {}).get("meldingsnummerField")
        )
        return OrderedDict(
            [
                ("datumAfhandelingField", afgesloten_op),
                ("datumStatusWijzigingField", aangepast_op),
                ("morIdField", meldingsnummer),
                ("msbIdField", morcore_melding.get("_links", {}).get("self")),
                ("statusBerichtField", statusBerichtField),
                ("statusField", meldr_status_code),
                (
                    "statusOmschrijvingField",
                    morcore_melding.get("status", {}).get("naam"),
                ),
                ("statusTemplateField", "MORR"),
            ]
        )

    def aanmaken_melding(
        self,
        mor_melding: MorMeldingAanmakenRequest,
        validated_address: Union[dict, None] = {},
    ):
        logger.info(f"MOR Core: meldingsnummerField={mor_melding.meldingsnummerField}")

        existing_signalen_response = self.bestaande_signalen(
            mor_melding.meldingsnummerField
        )
        if existing_signalen_response.status_code == 200:
            existing_signalen_response_dict = self._to_json(existing_signalen_response)
            signalen = existing_signalen_response_dict.get("results", [])
            logger.warning("bestaande signalen: %s", signalen)
            if signalen:
                return {
                    "messagesField": None,
                    "serviceResultField": {
                        "codeField": "A107",
                        "errorsField": None,
                        "messageField": f"MOR Melding {mor_melding.meldingsnummerField} bestaat al onder MOR CORE url {signalen[0].get('_links', {}).get('melding')}",
                    },
                    "dataField": None,
                    "newIdField": None,
                }

        mor_melding_dict = dict(mor_melding)
        if mor_melding_dict.get("aanvullendeVragenField"):
            logger.warning(
                f"aanvullendeVragenField: {mor_melding.aanvullendeVragenField}"
            )
        fotos = mor_melding_dict.pop("fotosField", [])
        melderEmailField = (
            mor_melding_dict.get("melderEmailField")
            if validators.email(mor_melding_dict.get("melderEmailField"))
            else ""
        )
        omschrijving_melder = (
            mor_melding_dict.get("omschrijvingField", "")
            if mor_melding_dict.get("omschrijvingField")
            else ""
        )

        geometrie = None
        try:
            omschrijving_melder_json = json.loads(omschrijving_melder)
            omschrijving_melder = omschrijving_melder_json["orgineleOmschrijving"]
            geometrie = f"POINT({omschrijving_melder_json['longitude']} {omschrijving_melder_json['latitude']})"
        except Exception:
            ...

        data = {
            "signaal_url": self.get_signaal_url(
                mor_melding_dict.get("meldingsnummerField")
            ),
            "bron_id": "MeldR",
            "bron_signaal_id": mor_melding_dict.get("meldingsnummerField"),
            "melder": {
                "naam": mor_melding_dict.get("melderNaamField"),
                "email": melderEmailField,
                "telefoonnummer": mor_melding_dict.get("melderTelefoonField"),
            },
            "origineel_aangemaakt": mor_melding_dict.get("aanmaakDatumField"),
            "urgentie": 0.5 if mor_melding_dict.get("spoedField") else 0.2,
            "onderwerpen": [
                {
                    "bron_url": self.get_onderwerp_url(
                        mor_melding_dict.get("onderwerpField")
                    )
                }
            ],
            "omschrijving_melder": omschrijving_melder[:500],
            "aanvullende_informatie": mor_melding_dict.get(
                "aanvullendeInformatieField", ""
            )[:5000],
            "aanvullende_vragen": (
                mor_melding_dict.get("aanvullendeVragenField", [])
                if mor_melding_dict.get("aanvullendeVragenField")
                else []
            ),
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
            data.update(
                {
                    "adressen": [
                        {
                            "plaatsnaam": validated_address.get("woonplaats"),
                            "straatnaam": validated_address.get("straatnaam"),
                            "huisnummer": validated_address.get("huisnummer"),
                            "huisletter": validated_address.get("huisletter"),
                            "toevoeging": validated_address.get(
                                "huisnummer_toevoeging"
                            ),
                            "postcode": validated_address.get("postcode"),
                            "buurtnaam": validated_address.get("buurtnaam"),
                            "wijknaam": validated_address.get("wijknaam"),
                            "geometrie": (
                                geometrie
                                if geometrie
                                else validated_address.get("geometrie")
                            ),
                        },
                    ]
                }
            )
        logger.info(
            f"MOR Core signaal aanmaken: data={json.dumps(data, indent=4)}, aantal foto's={len(fotos)}"
        )
        data["bijlagen"] = [{"bestand": file} for file in fotos]

        response = self._do_request(
            f"{self._ontdbblr_url if self._enable_ontdbblr and os.environ.get('ONTDBBLR_URL') else self._mor_core_url}/signaal/",
            method="post",
            data=data,
        )
        if response.status_code == 201:
            response_dict = self._to_json(response)
            logger.info(
                f"MOR Core signaal aangemaakt: bron_signaal_id={response_dict.get('bron_signaal_id')}"
            )
            response_dict.update(
                {
                    "messagesField": None,
                    "serviceResultField": {
                        "codeField": "201",
                        "errorsField": None,
                        "messageField": "Het signaal is aangemaakt in MOR CORE",
                    },
                    "dataField": copy.deepcopy(response_dict),
                    "newIdField": response_dict.get("_links", {}).get("melding"),
                }
            )
            return response_dict

        logentry = f"MOR Core signaal_aanmaken error: status code: {response.status_code}, text: {response.text}"
        logger.error(logentry)
        return serialize_object(
            OrderedDict(
                [
                    (
                        "serviceResultField",
                        OrderedDict(
                            [
                                ("codeField", "000"),
                                ("errorsField", OrderedDict([("Error", [logentry])])),
                                ("messageField", None),
                            ]
                        ),
                    ),
                    ("messagesField", None),
                    ("dataField", None),
                    ("newIdField", None),
                ]
            )
        )

    def melding_volgen(self, data):
        morIdField = dict(data).get("morIdField")
        logger.info(f"MOR Core: morIdField={morIdField}")
        errors = []

        signalen_response = self.bestaande_signalen(morIdField)
        melding_url = None
        if signalen_response.status_code == 200:
            signalen_response_dict = self._to_json(signalen_response)
            signalen_results = signalen_response_dict.get("results", [])
            if signalen_results:
                melding_url = signalen_results[0].get("_links", {}).get("melding")
            else:
                logentry = f"morcore melding_volgen melding url is niet gevonden obv signaal url: {self.get_signaal_url(morIdField)}"
                errors.append(logentry)
        else:
            logentry = f"morcore melding_volgen signalen error: {signalen_response.status_code}, {signalen_response.text}"
            logger.error(logentry)
            errors.append(logentry)

        if not melding_url:
            return serialize_object(
                OrderedDict(
                    [
                        ("rowsUpdatedField", 0),
                        (
                            "serviceResultField",
                            OrderedDict(
                                [
                                    ("codeField", "000"),
                                    ("errorsField", OrderedDict([("Error", errors)])),
                                    ("messageField", None),
                                ]
                            ),
                        ),
                        ("messagesField", None),
                    ]
                )
            )

        response = self._do_request(
            melding_url,
            method="get",
        )
        if response.status_code == 200:
            return serialize_object(
                OrderedDict(
                    [
                        ("rowsUpdatedField", 1),
                        (
                            "serviceResultField",
                            OrderedDict(
                                [
                                    ("codeField", "000"),
                                    ("errorsField", OrderedDict([("Error", [])])),
                                    (
                                        "messageField",
                                        "Morcore operatie succesvol uitgevoerd.",
                                    ),
                                ]
                            ),
                        ),
                        ("messagesField", None),
                    ]
                )
            )
        logentry = (
            f"morcore melding_volgen error: {response.status_code}, {response.text}"
        )
        logger.error(logentry)
        return serialize_object(
            OrderedDict(
                [
                    ("rowsUpdatedField", 0),
                    (
                        "serviceResultField",
                        OrderedDict(
                            [
                                ("codeField", "000"),
                                ("errorsField", OrderedDict([("Error", [logentry])])),
                                ("messageField", None),
                            ]
                        ),
                    ),
                    ("messagesField", None),
                ]
            )
        )

    def meldingen_opvragen(
        self, dagenField: float, morIdField: Union[str, None] = None
    ) -> ResponseOfGetMorMeldingen:
        now = datetime.now(pytz.timezone("Europe/Amsterdam"))
        dagen_eerder_dan_nu = now - timedelta(days=dagenField)
        filter_params = {
            "limit": 100,
            "ordering": "melding__origineel_aangemaakt",
            "melding__origineel_aangemaakt_gte": dagen_eerder_dan_nu.isoformat(),
        }
        melding_url = f"{self._mor_core_url}/signaal/"

        if morIdField:
            filter_params = {
                "signaal_url": {self.get_signaal_url(morIdField)},
            }
        response = self._do_request(
            melding_url,
            method="get",
            params=filter_params,
        )
        if response.status_code == 200:
            response_dict = self._to_json(response)
            mapped_meldingen = [
                MeldingenService.morcore_signaal_to_mormelding_response(m)
                for m in response_dict.get("results", [])
            ]

            return serialize_object(
                OrderedDict(
                    [
                        (
                            "morMeldingenField",
                            OrderedDict([("MorMelding", mapped_meldingen)]),
                        ),
                        ("messagesField", None),
                        (
                            "serviceResultField",
                            OrderedDict(
                                [
                                    ("codeField", "000"),
                                    ("errorsField", OrderedDict([("Error", [])])),
                                    (
                                        "messageField",
                                        f"Operatie succesvol uitgevoerd. {len(mapped_meldingen)} rij(en) gevonden",
                                    ),
                                ]
                            ),
                        ),
                    ]
                )
            )
        logentry = f"morcore meldingen_opvragen meldingen error: {response.status_code}, {response.text}"
        logger.error(logentry)
        return serialize_object(
            OrderedDict(
                [
                    ("morMeldingenField", None),
                    (
                        "serviceResultField",
                        OrderedDict(
                            [
                                ("codeField", "000"),
                                ("errorsField", OrderedDict([("Error", [logentry])])),
                                ("messageField", None),
                            ]
                        ),
                    ),
                    ("messagesField", None),
                ]
            )
        )

    def bestaande_signalen(self, morIdField):
        signalen_response = self._do_request(
            f"{self._mor_core_url}/signaal/",
            method="get",
            params={
                "signaal_url": {self.get_signaal_url(morIdField)},
            },
        )
        return signalen_response
