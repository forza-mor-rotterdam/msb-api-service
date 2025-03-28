import logging
from typing import Union

from config import MORCORE_MELDR_ONDERWERPEN
from schema_types import MorMeldingAanmakenRequest, MorMeldingVolgenRequest
from services.location import get_validated_address
from services.main import BaseService
from services.mor_core import MeldingenService
from services.msb import MSBService

logger = logging.getLogger(__name__)


class Splitter:
    service = MSBService
    filter_config = {}
    validated_address: Union[dict, None] = None
    onderwerp = None
    wijknaam = None
    buurtnaam = None

    def __init__(
        self,
        request_data: Union[MorMeldingAanmakenRequest, MorMeldingVolgenRequest, dict],
    ):
        self.filter_config = MORCORE_MELDR_ONDERWERPEN
        self.onderwerpen = [k for k in self.filter_config.keys()]
        data = dict(request_data)
        self.onderwerp = data.get("onderwerpField")
        try:
            self.validated_address = get_validated_address(
                rd_x=data.get("xCoordField"),
                rd_y=data.get("yCoordField"),
            )
            self.wijknaam = self.validated_address.get("wijknaam", None)
            self.buurtnaam = self.validated_address.get("buurtnaam", None)
        except Exception as e:
            logger.error(f"error validating addres: {e}")
            self.service = MSBService
        if self._melding_for_morcore():
            self.service = MeldingenService

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
        return self.service, self.validated_address
