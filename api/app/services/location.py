from services.pdok import PDOKAddressValidation
from services.rd_convert import rd_to_wgs        
import logging


logger = logging.getLogger(__name__)


class ValidateAddressException(Exception):
    ...


def get_validated_address(data):
    address = {
        'openbare_ruimte': data["locatie"]["adres"]["straatNaam"], 
        'huisnummer': data["locatie"]["adres"]["huisnummer"],
        'woonplaats': data["locatie"]["adres"].get("woonplaats", ""),
    }
    lat, lon = rd_to_wgs(data["locatie"]["x"], data["locatie"]["y"])
    location_data = {}
    location_validator = PDOKAddressValidation()
    validated_address = None
    alternative_address = dict(address)
    try:
        validated_address = location_validator.validate_address(address=address, lon=lon, lat=lat)
    except Exception as e:
        raise ValidateAddressException(f"error: {e}")


    return validated_address