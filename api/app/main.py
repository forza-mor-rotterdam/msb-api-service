import requests
from schema_types import MorMeldingAanmakenRequest, MorMeldingVolgenRequest, ResponseOfUpdate, ResponseOfInsert, ResponseOfGetMorMeldingen, MorMelding, MorMeldingenWrapper
from fastapi import FastAPI, Request
from fastapi.exceptions import ResponseValidationError
from zeep.helpers import serialize_object
from fastapi.templating import Jinja2Templates
from zeep import Client
from jinja2 import Environment, PackageLoader
from utils import parse_mor_melding_aanmaken_response, generate_message_identification
from typing import Union
import os
import logging
import uvicorn

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from splitter import Splitter
from services.main import BaseService
from services.msb import MSBService
from services.mor_core import MeldingenService
from collections import OrderedDict

description = """
API endpoints are based on the existing external SOAP interface for MSB(Meldingen Systeem Buitenruimte) for the municipality Rotterdam, the Netherlands.
"""

### set defaults
os.environ.setdefault("MSB_EXTERN_WEBSERVICES_URL", "https://webservices-acc.rotterdam.nl/Msb.Extern.Services/MsbMorService.svc")
os.environ.setdefault("MSB_EXTERN_WEBSERVICES_WSDL_URL", "https://webservices-acc.rotterdam.nl/Msb.Extern.Services/MsbMorService.svc?wsdl")


## configure logging and log start
logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
logger = logging.getLogger(__name__)
logger.info("Application started")
logger.info("MSB_EXTERN_WEBSERVICES_URL=%s", os.environ.get("MSB_EXTERN_WEBSERVICES_URL"))
logger.info("MSB_EXTERN_WEBSERVICES_WSDL_URL=%s", os.environ.get("MSB_EXTERN_WEBSERVICES_WSDL_URL"))


client = Client(os.environ.get("MSB_EXTERN_WEBSERVICES_WSDL_URL"))

version = "v1"

app = FastAPI(
    title="Rest API for MSB",
    description=description,
    version="0.0.1",
)

@app.post(f"/{version}/AanmakenMelding/", response_model=ResponseOfInsert)
def aanmaken_melding(mor_melding: MorMeldingAanmakenRequest):
    service: type[BaseService]
    validated_address: Union[dict, None]
    service, validated_address = Splitter(mor_melding).get_service()
    response = service().aanmaken_melding(mor_melding, validated_address)

    return response


@app.patch(f"/{version}/MeldingVolgen/", response_model=ResponseOfUpdate)
def melding_volgen(melding_volgen: MorMeldingVolgenRequest):
    morcore_response = serialize_object(MeldingenService().melding_volgen(melding_volgen))
    if morcore_response.get("rowsUpdatedField") == 1:
        return morcore_response
    return MSBService().melding_volgen(melding_volgen)


@app.get(f"/{version}/MeldingenOpvragen/", response_model=ResponseOfGetMorMeldingen)
def meldingen_opvragen(dagenField: float, morIdField: Union[str, None] = None):
    logger.info("meldingen_opvragen: msb en morecore meldingen opvragen en gecombineert teruggeven")
    msb_response = serialize_object(MSBService().meldingen_opvragen(dagenField=dagenField, morIdField=morIdField))
    morcore_response = serialize_object(MeldingenService().meldingen_opvragen(dagenField=dagenField, morIdField=morIdField))
    msb_meldingen = [] 
    morcore_meldingen = []
    if msb_response.get("morMeldingenField"):
        msb_meldingen = msb_response.get("morMeldingenField", {}).get("MorMelding", [])
    if morcore_response.get("morMeldingenField"):
        morcore_meldingen = morcore_response.get("morMeldingenField", {}).get("MorMelding", [])
    logger.info("msb_meldingen: %s", msb_meldingen)
    logger.info("morcore_meldingen: %s", morcore_meldingen)

    msb_errors = msb_response.get("serviceResultField", {}).get("errorsField", {}).get("Error", [])
    morcore_errors = morcore_response.get("serviceResultField", {}).get("errorsField", {}).get("Error", [])
    standaard_errors = [f"In MORCORE en MSB is een melding aangemaakt met dezelfde morIdField: {morIdField}"] if morIdField and len(list(msb_meldingen + morcore_meldingen)) > 1 else []
    service_result_field = OrderedDict([
        ('codeField', '000'), 
        ('errorsField', OrderedDict([('Error', msb_errors + morcore_errors + standaard_errors)])), 
        ('messageField', f"Totaal aantal {len(list(msb_meldingen + morcore_meldingen))} gevonden")
    ])

    return serialize_object(OrderedDict([
        ("morMeldingenField", OrderedDict([("MorMelding", msb_meldingen + morcore_meldingen)])), 
        ("messagesField", OrderedDict([("string", [f"MORCORE aantal: {len(morcore_meldingen)}", f"MSB aantal: {len(msb_meldingen)}"])])),
        ("serviceResultField", service_result_field),
    ]))


@app.exception_handler(ResponseValidationError)
async def validation_exception_handler(request: Request, exc: ResponseValidationError):
    return JSONResponse(
        status_code=500,
        content=jsonable_encoder({"detail": exc.errors(), "Error": "Name field is missing"}),
    )

# for debugging
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)