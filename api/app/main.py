import logging
import os
from collections import OrderedDict
from typing import Union

import uvicorn
from fastapi import FastAPI
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from schema_types import (
    MorMeldingAanmakenRequest,
    MorMeldingVolgenRequest,
    ResponseOfGetMorMeldingen,
    ResponseOfInsert,
    ResponseOfUpdate,
)
from services.main import BaseService
from services.mor_core import MeldingenService
from services.msb import MSBService
from splitter import Splitter
from zeep import Client
from zeep.helpers import serialize_object

description = """
API endpoints are based on the existing external SOAP interface for MSB(Meldingen Systeem Buitenruimte) for the municipality Rotterdam, the Netherlands.
"""

### set defaults
os.environ.setdefault(
    "MSB_EXTERN_WEBSERVICES_URL",
    "https://webservices-acc.rotterdam.nl/Msb.Extern.Services/MsbMorService.svc",
)
os.environ.setdefault(
    "MSB_EXTERN_WEBSERVICES_WSDL_URL",
    "https://webservices-acc.rotterdam.nl/Msb.Extern.Services/MsbMorService.svc?wsdl",
)


## configure logging and log start
logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)
logger.info("Application started")
logger.info(
    "MSB_EXTERN_WEBSERVICES_URL=%s", os.environ.get("MSB_EXTERN_WEBSERVICES_URL")
)
logger.info(
    "MSB_EXTERN_WEBSERVICES_WSDL_URL=%s",
    os.environ.get("MSB_EXTERN_WEBSERVICES_WSDL_URL"),
)


client = Client(os.environ.get("MSB_EXTERN_WEBSERVICES_WSDL_URL"))

version = "v1"

app = FastAPI(
    title="Rest API for MSB",
    description=description,
    version="0.0.1",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(
        f"request method: {request.method}, url: {request.url}, validation error: {exc}"
    )
    return await request_validation_exception_handler(request, exc)


@app.post(f"/{version}/AanmakenMelding/", response_model=ResponseOfInsert)
def aanmaken_melding(mor_melding: MorMeldingAanmakenRequest):
    logger.warning(
        f"meldingsnummerField={mor_melding.meldingsnummerField}, aanmaakDatumField={mor_melding.aanmaakDatumField}"
    )
    service: type[BaseService]
    validated_address: Union[dict, None]
    service, validated_address = Splitter(mor_melding).get_service()
    response = service().aanmaken_melding(mor_melding, validated_address)

    return response


@app.patch(f"/{version}/MeldingVolgen/", response_model=ResponseOfUpdate)
def melding_volgen(melding_volgen: MorMeldingVolgenRequest):
    morcore_response = serialize_object(
        MeldingenService().melding_volgen(melding_volgen)
    )
    if morcore_response.get("rowsUpdatedField") == 1:
        return morcore_response
    return MSBService().melding_volgen(melding_volgen)


@app.get(f"/{version}/MeldingenOpvragen/", response_model=ResponseOfGetMorMeldingen)
def meldingen_opvragen(dagenField: float, morIdField: Union[str, None] = None):
    msb_response = serialize_object(
        MSBService().meldingen_opvragen(dagenField=dagenField, morIdField=morIdField)
    )
    morcore_response = serialize_object(
        MeldingenService().meldingen_opvragen(
            dagenField=dagenField, morIdField=morIdField
        )
    )
    msb_meldingen = []
    morcore_meldingen = []
    if msb_response.get("morMeldingenField"):
        msb_meldingen = msb_response.get("morMeldingenField", {}).get("MorMelding", [])
    if morcore_response.get("morMeldingenField"):
        morcore_meldingen = morcore_response.get("morMeldingenField", {}).get(
            "MorMelding", []
        )
    logger.info(
        f"morcore_signalen={[signaal.get('morIdField') for signaal in morcore_meldingen]}, msb_aantal={len(msb_meldingen)}"
    )

    msb_errors = (
        msb_response.get("serviceResultField", {})
        .get("errorsField", {})
        .get("Error", [])
    )
    morcore_errors = (
        morcore_response.get("serviceResultField", {})
        .get("errorsField", {})
        .get("Error", [])
    )
    standaard_errors = (
        [
            f"In MORCORE en MSB is een melding aangemaakt met dezelfde morIdField: {morIdField}"
        ]
        if morIdField and len(list(msb_meldingen + morcore_meldingen)) > 1
        else []
    )
    service_result_field = OrderedDict(
        [
            ("codeField", "000"),
            (
                "errorsField",
                OrderedDict(
                    [("Error", msb_errors + morcore_errors + standaard_errors)]
                ),
            ),
            (
                "messageField",
                f"Totaal aantal {len(list(msb_meldingen + morcore_meldingen))} gevonden",
            ),
        ]
    )

    return serialize_object(
        OrderedDict(
            [
                (
                    "morMeldingenField",
                    OrderedDict([("MorMelding", msb_meldingen + morcore_meldingen)]),
                ),
                (
                    "messagesField",
                    OrderedDict(
                        [
                            (
                                "string",
                                [
                                    f"MORCORE aantal: {len(morcore_meldingen)}",
                                    f"MSB aantal: {len(msb_meldingen)}",
                                ],
                            )
                        ]
                    ),
                ),
                ("serviceResultField", service_result_field),
            ]
        )
    )


# for debugging
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
