# from django.http import QueryDict
import logging
import os

from geojson import Point
from requests import get
import urllib3
from requests.exceptions import RequestException
from services.rd_convert import rd_to_wgs

logger = logging.getLogger(__name__)

DEFAULT_PDOK_MUNICIPALITIES = ["Rotterdam"]
DEFAULT_PDOK_CITIES = ["Rotterdam", "Rozenburg"]


class AddressValidationUnavailableException(Exception):
    pass


class NoResultsException(Exception):
    pass


class BaseAddressValidation:
    address_validation_url = None

    def _search(self, address, *args, **kwargs):
        raise NotImplementedError(
            "The search functionality should be implemented derived class"
        )

    def _address_by_rd_search(self, rd_x, rd_y, *args, **kwargs):
        raise NotImplementedError(
            "The address_by_rd_search functionality should be implemented derived class"
        )

    def _search_result_to_address(self, result):
        """
        If specific mapping is needed this functionality can be overwritten in the derived class
        """
        return result

    def validate_address(self, address, *args, **kwargs):
        results = self._search(address, *args, **kwargs)
        if len(results) == 0:
            raise NoResultsException("No results found!")
        return self._search_result_to_address(results[0])

    def rd_to_address(self, rd_x, rd_y, *args, **kwargs):
        results = self._search(rd_x, rd_y, *args, **kwargs)

        if len(results) == 0:
            raise NoResultsException("No results found!")
        return self._search_result_to_address(results[0])



class PDOKReverseRD(BaseAddressValidation):
    PDOK_API_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1"

    def __init__(self):
        self.address_validation_url = (
            f'{os.environ.get("PDOK_API_URL", self.PDOK_API_URL)}/reverse'
        )
        self.gemeente_code = os.environ.get("WIJKEN_EN_BUURTEN_GEMEENTECODE", "0599")
        self.adres_max_afstand = os.environ.get("ADRES_MAX_AFSTAND", "75")

    def _search(self, rd_x=None, rd_y=None, *args, **kwargs):
        self.rd_x = rd_x
        self.rd_y = rd_y
        try:
            query_params = {
                "X": rd_x,
                "Y": rd_y,
                "fl": [
                    "wijknaam",
                    "straatnaam",
                    "huisnummer",
                    "huisletter",
                    "toevoeging",
                    "postcode",
                    "buurtnaam",
                    "woonplaatsnaam",
                    "centroide_ll",
                ],
            }
            response = get(
                self.address_validation_url, 
                query_params, 
                headers={
                    "user-agent": urllib3.util.SKIP_HEADER,
                },
            )
            response.raise_for_status()
        except RequestException as e:
            raise AddressValidationUnavailableException(e)
        return response.json()["response"]["docs"]

    def _search_result_to_address(self, result):
        mapping = {
            "straatnaam": "straatnaam",
            "postcode": "postcode",
            "huisnummer": "huisnummer",
            "huisletter": "huisletter",
            "huisnummertoevoeging": "huisnummer_toevoeging",
            "woonplaatsnaam": "woonplaats",
            "wijknaam": "wijknaam",
            "buurtnaam": "buurtnaam",
        }

        sia_address_dict = {}
        for PDOK_key, sia_key in mapping.items():
            sia_address_dict[sia_key] = result[PDOK_key] if PDOK_key in result else ""
        lat, lon = rd_to_wgs(self.rd_x, self.rd_y)
        sia_address_dict["geometrie"] = Point((lon, lat))
        return sia_address_dict
    
    def search_address_with_distance(self, rd_x, rd_y):
        self.rd_x = rd_x
        self.rd_y = rd_y
        try:
            query_params = {
                "X": rd_x,
                "Y": rd_y,
                "rows": 10,
                "distance": self.adres_max_afstand,
                "fq": [
                    f"gemeentecode:{self.gemeente_code}",
                ],
                "fl": [
                    "id",
                    "straatnaam",
                    "postcode",
                    "huisnummer",
                    "huisletter",
                    "huisnummertoevoeging",
                    "woonplaatsnaam",
                    "gemeentenaam",
                    "wijknaam",
                    "buurtnaam",
                    "zijde",
                    "afstand",
                    "huis_nlt",
                    "centroide_ll",
                ],
            }
            response = get(
                self.address_validation_url, 
                query_params, 
                headers={
                    "user-agent": urllib3.util.SKIP_HEADER,
                },
            )

        except RequestException as e:
            raise AddressValidationUnavailableException(e)
        return response.json()["response"]["docs"]
    

    def search_object_with_distance(self, rd_x, rd_y):
        headers = {
            "user-agent": urllib3.util.SKIP_HEADER,
        }
        try:
            query_params = {
                "X": rd_x,
                "Y": rd_y,
                "rows": 100,
                "type": ["weg", "buurt"],
                "fq": [
                    f"gemeentecode:{self.gemeente_code}",
                ],
                "fl": [
                    "id",
                    "type",
                    "straatnaam",
                    "postcode",
                    "huisnummer",
                    "huisletter",
                    "huisnummertoevoeging",
                    "woonplaatsnaam",
                    "gemeentenaam",
                    "wijknaam",
                    "buurtnaam",
                    "afstand",
                    "bron",
                    "centroide_ll",
                ],
            }
            response = get(
                self.address_validation_url, 
                query_params, 
                headers=headers,

            )
        except RequestException as e:
            raise AddressValidationUnavailableException(e)

        wegen_en_buurten = response.json()["response"]["docs"]
        wegen = [weg_of_buurt for weg_of_buurt in wegen_en_buurten if weg_of_buurt["type"] == "weg"]
        buurten = [weg_of_buurt for weg_of_buurt in wegen_en_buurten if weg_of_buurt["type"] == "buurt"]
        if not buurten:
            return []
        wegen_bag = [weg for weg in wegen if "BAG" in weg["bron"]]
        wegen_bag_met_buurten_en_wijken = [
            {
                **weg_bag,
                **{
                    "buurtnaam": buurten[0]["buurtnaam"],
                    "wijknaam": buurten[0]["wijknaam"],
                }
            }
            for weg_bag in wegen_bag 
        ]
        return wegen_bag_met_buurten_en_wijken

    def search_free(self, lat, lon):
        url = (
            f'{os.environ.get("PDOK_API_URL", self.PDOK_API_URL)}/free'
        )
        try:
            query_params = {
                "lat": lat,
                "lon": lon,
                "rows": 10,
                "fq": [
                    f"gemeentecode:{self.gemeente_code}",
                    "type:weg",
                    "bron:BAG",
                ],
                "sort": "distance desc",
                "fl": "*",
            }
            response = get(
                url, 
                query_params, 
                headers={
                    "user-agent": urllib3.util.SKIP_HEADER,
                },
            )
            response.raise_for_status()

        except RequestException as e:
            raise AddressValidationUnavailableException(e)
        return response.json()["response"]["docs"]
class PDOKAddressValidation(BaseAddressValidation):
    PDOK_API_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1"

    def __init__(self):
        self.address_validation_url = (
            f'{os.environ.get("PDOK_API_URL", self.PDOK_API_URL)}/suggest'
        )

    def _search_result_to_address(self, result):
        mapping = {
            "straatnaam": "straatnaam",
            "postcode": "postcode",
            "huisnummer": "huisnummer",
            "huisletter": "huisletter",
            "huisnummertoevoeging": "huisnummer_toevoeging",
            "woonplaatsnaam": "woonplaats",
            "wijknaam": "wijknaam",
            "buurtnaam": "buurtnaam",
        }

        sia_address_dict = {}
        for PDOK_key, sia_key in mapping.items():
            sia_address_dict[sia_key] = result[PDOK_key] if PDOK_key in result else ""
        sia_address_dict["geometrie"] = result["centroide_ll"]
        return sia_address_dict

    def _pdok_request_query_params(self, address, lon=None, lat=None):
        query_dict = {}
        query_dict.update({"fl": "*"})
        query_dict.update({"rows": "5"})
        query_dict.update({"fq": ["type:adres", "bron:BAG"]})

        if "woonplaats" in address and address["woonplaats"].strip():
            query_dict["fq"].append(f'woonplaatsnaam:{address["woonplaats"].strip()}')
        else:
            cleaned_pdok_cities_list = filter(
                lambda item: item, map(str.strip, DEFAULT_PDOK_CITIES)
            )
            query_dict["fq"].append(
                f"""woonplaatsnaam:("{'" "'.join(cleaned_pdok_cities_list)}")"""
            )

        if "postcode" in address and address["postcode"].strip():
            query_dict["fq"].append(f'postcode:{address["postcode"].strip()}')

        # remove '', ' ' strings before formatting
        cleaned_pdok_list = filter(
            lambda item: item, map(str.strip, DEFAULT_PDOK_MUNICIPALITIES)
        )
        query_dict["fq"].append(f"""gemeentenaam:("{'" "'.join(cleaned_pdok_list)}")""")

        straatnaam = address["openbare_ruimte"].strip()
        huisnummer = str(address["huisnummer"]).strip()
        huisletter = (
            address["huisletter"].strip()
            if "huisletter" in address and address["huisletter"]
            else ""
        )
        toevoeging = (
            f'-{address["huisnummer_toevoeging"].strip()}'
            if "huisnummer_toevoeging" in address and address["huisnummer_toevoeging"]
            else ""
        )  # noqa

        if lon and lat:
            query_dict.update({"lon": lon, "lat": lat})

        query_dict.update({"q": f"{straatnaam} {huisnummer}{huisletter}{toevoeging}"})

        return query_dict

    def _search(self, address, lon=None, lat=None, *args, **kwargs):
        try:
            query_params = self._pdok_request_query_params(
                address=address, lon=lon, lat=lat
            )
            response = get(self.address_validation_url, query_params)
            # response_reverse = get(self.address_validation_reverse_url, {"lat": query_params.get("lat"), "lon": query_params.get("lon"), "fl": ["wijknaam", "straatnaam", "huisnummer", "huisletter", "toevoeging", "postcode", "buurtnaam", "geometrie"]})

            response.raise_for_status()
        except RequestException as e:
            raise AddressValidationUnavailableException(e)
        return response.json()["response"]["docs"]
