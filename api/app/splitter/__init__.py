import requests
from services.msb import MSBService
from services.mor_core import MeldingenService
from services.main import BaseService
from schema_types import MorMeldingAanmakenRequest, MorMeldingVolgenRequest, ResponseOfUpdate, ResponseOfInsert, ResponseOfGetMorMeldingen
from typing import Union
from services.location import get_validated_address
import logging
from config import MORCORE_MELDR_ONDERWERPEN, MORCORE_WIJKEN
import os


logger = logging.getLogger(__name__)


class Splitter:
    service = MSBService
    meldr_onderwerpen_for_morcore = []
    morcore_pdok_wijken = []
    morcore_pdok_buurten = []
    validated_address: Union[dict, None] = None
    onderwerp = None
    straatnaam = None
    wijknaam = None
    buurtnaam = None

    def __init__(self, request_data: Union[MorMeldingAanmakenRequest, MorMeldingVolgenRequest, dict]):
        self.meldr_onderwerpen_for_morcore = [onderwerp.strip() for onderwerp in os.environ.get("MORCORE_MELDR_ONDERWERPEN", MORCORE_MELDR_ONDERWERPEN).split(",")]
        self.morcore_pdok_wijken = [wijk.strip() for wijk in os.environ.get("MORCORE_WIJKEN", MORCORE_WIJKEN).split(",")]
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
            self.service = MeldingenService

    def _set_service(self):
        self.service = MSBService

    def _onderwerp_for_morcore(self):
        return self.onderwerp in self.meldr_onderwerpen_for_morcore
    
    def _wijknaam_for_morcore(self):
        return self.wijknaam in self.morcore_pdok_wijken
    
    def _buurtnaam_for_morcore(self):
        return self.buurtnaam in self.morcore_pdok_buurten
    
    def _melding_for_morcore(self):
        if self.morcore_pdok_wijken:
            return self._onderwerp_for_morcore() and self._wijknaam_for_morcore()
        return self._onderwerp_for_morcore() and self._buurtnaam_for_morcore()

    def get_service(self) -> tuple[type[BaseService], Union[dict, None]]:
        logger.info(f"Splitter using service: {self.service}")
        return self.service, self.validated_address
