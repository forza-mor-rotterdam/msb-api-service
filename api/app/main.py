import requests
from schema_types import MorMeldingAanmakenRequest, MorMeldingVolgenRequest, ResponseOfUpdate, ResponseOfInsert, ResponseOfGetMorMeldingen
from fastapi import FastAPI, Request
from zeep.helpers import serialize_object
from fastapi.templating import Jinja2Templates
from zeep import Client
from jinja2 import Environment, PackageLoader
from utils import validate_mor_melding_aanmaken_response, generate_message_identification
from typing import Union
import os


client = Client(os.environ.get("MSB_EXTERN_WEBSERVICES_WSDL_URL", "wsdl/MsbMorService.xml"))

app = FastAPI()

templates = Jinja2Templates(directory="templates")
env = Environment(loader=PackageLoader("main"))
env.trim_blocks = True
env.lstrip_blocks = True
env.strip_trailing_newlines = True
AanmakenMelding_template = env.get_template("AanmakenMelding.xml")


@app.post("/AanmakenMelding/", response_model=ResponseOfInsert)
async def aanmaken_melding(mor_melding: MorMeldingAanmakenRequest):

    url = os.environ.get("MSB_EXTERN_WEBSERVICES_URL", "https://webservices-acc.rotterdam.nl/Msb.Extern.Services/MsbMorService.svc")
    action_url = "http://tempuri.org/IService/AanmakenMelding"
    context_data = {
        "action_url": action_url,
        "message_uuid": generate_message_identification(),
        "services_url": url,
    }
    context_data.update(dict(mor_melding))

    body = AanmakenMelding_template.render(context_data)

    headers = {'content-type': 'text/xml'}
    headers.update(
        {"SOAPAction": action_url}
    )
    response = requests.post(url, data=body, headers=headers)

    response.raise_for_status()

    return validate_mor_melding_aanmaken_response(response.text)


@app.patch("/MeldingVolgen/", response_model=ResponseOfUpdate)
async def melding_volgen(melding_volgen: MorMeldingVolgenRequest):

    response = client.service.MeldingVolgen(dict(melding_volgen))

    return serialize_object(response)


@app.get("/MeldingenOpvragen/", response_model=ResponseOfGetMorMeldingen)
async def meldingen_opvragen(dagenField: float, morIdField: Union[str, None] = None):

    response = client.service.MeldingenOpvragen(locals())

    return serialize_object(response)


@app.get("/")
def main(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})