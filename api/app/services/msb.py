import logging
import os
from collections import OrderedDict
from typing import Union

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, PackageLoader
from schema_types import MorMeldingAanmakenRequest
from services.main import BaseService
from utils import generate_message_identification, parse_mor_melding_aanmaken_response
from zeep import Client
from zeep.helpers import serialize_object

logger = logging.getLogger(__name__)


class MSBService(BaseService):
    client = None
    _api_base_url = None
    _api_path: str = "/api/v1"
    _data_type = "data"

    def __init__(self, *args, **kwargs: dict):
        self._api_base_url = os.environ.get("MSB_EXTERN_WEBSERVICES_URL")
        self.client = Client(os.environ.get("MSB_EXTERN_WEBSERVICES_WSDL_URL"))
        super().__init__(*args, **kwargs)

    def aanmaken_melding(
        self,
        mor_melding: MorMeldingAanmakenRequest,
        validated_address: Union[dict, None] = {},
    ):
        message_id = generate_message_identification()
        logger.info(f"MSB: meldingsnummerField={mor_melding.meldingsnummerField}")

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
        encoded_body = body.encode("utf-8")

        headers = {
            "content-type": "text/xml",
            "SOAPAction": action_url,
        }

        response = self._do_request(
            self._api_base_url, method="post", data=encoded_body, extra_headers=headers
        )

        response.raise_for_status()

        try:
            return parse_mor_melding_aanmaken_response(response.text)
        except Exception as e:
            logentry = f"parse_mor_melding_aanmaken_response: Exception={e}, response text={response.text}"
            logger.error(logentry)
            return serialize_object(
                OrderedDict(
                    [
                        (
                            "serviceResultField",
                            OrderedDict(
                                [
                                    ("codeField", "000"),
                                    (
                                        "errorsField",
                                        OrderedDict([("Error", [logentry])]),
                                    ),
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
        response = self.client.service.MeldingVolgen(dict(data))
        return serialize_object(response)

    def meldingen_opvragen(
        self, dagenField: float, morIdField: Union[str, None] = None
    ):
        response = self.client.service.MeldingenOpvragen(locals())
        serialized_object = serialize_object(response)
        meldr_status = {
            "MORS": "Z",
            "MORN": "X",
        }
        meldingen_field = (
            serialized_object.get("morMeldingenField", {})
            if serialized_object.get("morMeldingenField", {})
            else {}
        )
        for melding in meldingen_field.get("MorMelding", []):
            melding["statusField"] = meldr_status.get(
                melding.get("statusTemplateField"), melding["statusField"]
            )
        return serialized_object
