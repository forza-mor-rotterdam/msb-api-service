import requests
from schema_types import MorMeldingAanmakenRequest, MorMeldingVolgenRequest, ResponseOfUpdate, ResponseOfInsert, ResponseOfGetMorMeldingen
from fastapi import FastAPI, Request
from zeep.helpers import serialize_object
from fastapi.templating import Jinja2Templates
from zeep import Client
from jinja2 import Environment, PackageLoader
from utils import parse_mor_melding_aanmaken_response, generate_message_identification
from typing import Union
import os


description = """
API endpoints are based on the existing external SOAP interface for MSB(Meldingen Systeem Buitenruimte) for the municipality Rotterdam, the Netherlands 
"""


client = Client(os.environ.get("MSB_EXTERN_WEBSERVICES_WSDL_URL", "wsdl/MsbMorService.xml"))

version = "v1"

app = FastAPI(
    title="Rest API for MSB",
    description=description,
    version="0.0.1",
)

templates = Jinja2Templates(directory="templates")
env = Environment(loader=PackageLoader("main"))
env.trim_blocks = True
env.lstrip_blocks = True
env.strip_trailing_newlines = True
AanmakenMelding_template = env.get_template("AanmakenMelding.xml")


@app.post(f"/{version}/AanmakenMelding/", response_model=ResponseOfInsert)
def aanmaken_melding(mor_melding: MorMeldingAanmakenRequest):

    url = os.environ.get("MSB_EXTERN_WEBSERVICES_URL", "https://webservices-acc.rotterdam.nl/Msb.Extern.Services/MsbMorService.svc")
    action_url = "http://tempuri.org/IService/AanmakenMelding"
    context_data = {
        "action_url": action_url,
        "message_uuid": generate_message_identification(),
        "services_url": url,
    }
    context_data.update(dict(mor_melding))

    body = AanmakenMelding_template.render(context_data)

    headers = {
        "content-type": "text/xml",
        "SOAPAction": action_url,
    }
    response = requests.post(url, data=body, headers=headers)

    response.raise_for_status()

    return parse_mor_melding_aanmaken_response(response.text)


@app.patch(f"/{version}/MeldingVolgen/", response_model=ResponseOfUpdate)
def melding_volgen(melding_volgen: MorMeldingVolgenRequest):

    response = client.service.MeldingVolgen(dict(melding_volgen))

    return serialize_object(response)


@app.get(f"/{version}/MeldingenOpvragen/", response_model=ResponseOfGetMorMeldingen)
def meldingen_opvragen(dagenField: float, morIdField: Union[str, None] = None):

    response = client.service.MeldingenOpvragen(locals())

    return serialize_object(response)