import logging
from urllib.parse import urlparse

import requests
from requests import Request, Response
import os
from zeep import Client
from zeep.helpers import serialize_object
from utils import parse_mor_melding_aanmaken_response, generate_message_identification
from typing import Union
from services.main import BaseService
from jinja2 import Environment, PackageLoader
from fastapi.templating import Jinja2Templates
from schema_types import MorMeldingAanmakenRequest, MorMeldingVolgenRequest, ResponseOfUpdate, ResponseOfInsert, ResponseOfGetMorMeldingen


logger = logging.getLogger(__name__)


class MSBService(BaseService):
    client = None
    _api_base_url = None
    _timeout: tuple[int, ...] = (5, 10)
    _api_path: str = "/api/v1"
    _data_type = "data"

    def __init__(self, *args, **kwargs: dict):
        self._api_base_url = os.environ.get("MSB_EXTERN_WEBSERVICES_URL")
        self.client = Client(os.environ.get("MSB_EXTERN_WEBSERVICES_WSDL_URL"))
        super().__init__(*args, **kwargs)

    def aanmaken_melding(self, mor_melding: MorMeldingAanmakenRequest, validated_address: Union[dict, None] = {}):
        message_id = generate_message_identification()

        logger.info("New aanmaken melding request, message_id=%s", message_id)
        logger.info("Client meldingsnummer=%s", mor_melding.meldingsnummerField)
        logger.info("Request content=%s", mor_melding)

        Jinja2Templates(directory="templates")
        env = Environment(loader=PackageLoader("main"))
        env.trim_blocks = True
        env.lstrip_blocks = True
        env.strip_trailing_newlines = True
        AanmakenMelding_template = env.get_template("AanmakenMelding.xml")

        action_url = "http://tempuri.org/IService/AanmakenMelding"
        context_data = {
            "action_url": action_url,
            "message_uuid": message_id,
            "services_url": self._api_base_url,
        }
        context_data.update(dict(mor_melding))

        body = AanmakenMelding_template.render(context_data)
        encoded_body = body.encode('utf-8')
        logger.info("Generated body=%s", encoded_body)

        headers = {
            "content-type": "text/xml",
            "SOAPAction": action_url,
        }

        response =  self._do_request(
            self._api_base_url, method="post", data=encoded_body, extra_headers=headers
        )

        logger.info("MSB HTTP status code=%s", response.status_code)
        logger.info("MSB HTTP response=%s", response.text)
        logger.info("MSB HTTP headers=%s", response.headers)

        response.raise_for_status()
        return parse_mor_melding_aanmaken_response(response.text)

    def melding_volgen(self, data):
        response = self.client.service.MeldingVolgen(dict(data))
        return serialize_object(response)

    def meldingen_opvragen(self, dagenField: float, morIdField: Union[str, None] = None):
        logger.info(f"meldingen_opvragen request, dagenField={dagenField}, morIdField={morIdField}")
        response = self.client.service.MeldingenOpvragen(locals())
        logger.info(f"meldingen_opvragen response text={response.text}")
        serialized_object = serialize_object(response)
        logger.info(f"meldingen_opvragen serialized_object={serialized_object}")
        meldr_status = {
            "MORS": "Z",
            "MORN": "X",
        }
        for melding in serialized_object.get("morMeldingenField").get("MorMelding", []):
            melding["statusField"] = meldr_status.get(melding.get("statusTemplateField"), melding["statusField"])
        return serialized_object
