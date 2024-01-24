import requests
from services.msb import MSBService
from services.mor_core import MeldingenService
from services.ontdbblr import OntdbblRService
from services.main import BaseService
from schema_types import MorMeldingAanmakenRequest, MorMeldingVolgenRequest, ResponseOfUpdate, ResponseOfInsert, ResponseOfGetMorMeldingen
from typing import Union
from services.location import get_validated_address
import logging
from config import MORCORE_MELDR_ONDERWERPEN
import os


logger = logging.getLogger(__name__)


class Splitter:
    service = MSBService
    filter_config = {}
    morcore_pdok_wijken = []
    morcore_pdok_buurten = []
    validated_address: Union[dict, None] = None
    onderwerp = None
    straatnaam = None
    wijknaam = None
    buurtnaam = None

    def __init__(self, request_data: Union[MorMeldingAanmakenRequest, MorMeldingVolgenRequest, dict]):
        self.filter_config = MORCORE_MELDR_ONDERWERPEN
        self.onderwerpen = [k for k in self.filter_config.keys()]
        data = dict(request_data) 
        logger.info(f"Splitter request_data: {data}")
        self.onderwerp = data.get("onderwerpField")
        self.straatnaam = data.get("straatnaamField")
        try:
            self.validated_address = get_validated_address({
                "locatie": {
                    "adres": {
                        "straatNaam": self.straatnaam,
                        "huisnummer": data.get("huisnummerField"),
                    },
                    "x": data.get("xCoordField"),
                    "y": data.get("yCoordField"),
                }
            })
            logger.info(f"validated_address: {self.validated_address}")
            self.wijknaam = self.validated_address.get("wijknaam", None)
            self.buurtnaam = self.validated_address.get("buurtnaam", None)
        except Exception as e:
            logger.error(f"error validating addres: {e}")
            self.service = MSBService
        if self._melding_for_morcore():
            self.service = OntdbblRService

    def _set_service(self):
        self.service = MSBService
    
    def _melding_for_morcore(self):
        if self.onderwerp in self.onderwerpen:
            wijken_buurten_filter = self.filter_config.get(self.onderwerp)
            if not wijken_buurten_filter:
                return True
            if self.wijknaam in wijken_buurten_filter.get("wijken", []):
                return True
            if self.buurtnaam in wijken_buurten_filter.get("buurten", []):
                return True
        return False

    def get_service(self) -> tuple[type[BaseService], Union[dict, None]]:
        logger.info(f"Splitter using service: {self.service}")
        return self.service, self.validated_address

