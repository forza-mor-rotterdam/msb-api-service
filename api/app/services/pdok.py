# from django.http import QueryDict
from requests import get
from requests.exceptions import RequestException
import os
import logging
from services.rd_convert import rd_to_wgs
from geojson import Point


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
        raise NotImplementedError('The search functionality should be implemented derived class')

    def _address_by_rd_search(self, rd_x, rd_y, *args, **kwargs):
        raise NotImplementedError('The address_by_rd_search functionality should be implemented derived class')

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
        self.address_validation_url = f'{os.environ.get("PDOK_API_URL", self.PDOK_API_URL)}/reverse'

    def _search(self, rd_x=None, rd_y=None, *args, **kwargs):
        self.rd_x = rd_x
        self.rd_y = rd_y
        try:
            query_params = {"X": rd_x, "Y": rd_y, "fl": ["wijknaam", "straatnaam", "huisnummer", "huisletter", "toevoeging", "postcode", "buurtnaam", "woonplaatsnaam", "centroide_ll"]}
            logger.info(f"PDOK rd query_params: {query_params}")
            response = get(self.address_validation_url, query_params)

            logger.info("pdok reverse response text: %s", response.text)
            response.raise_for_status()
        except RequestException as e:
            raise AddressValidationUnavailableException(e)
        return response.json()["response"]["docs"]
    
    def _search_result_to_address(self, result):
        mapping = {
            'straatnaam': 'straatnaam',
            'postcode': 'postcode',
            'huisnummer': 'huisnummer',
            'huisletter': 'huisletter',
            'huisnummertoevoeging': 'huisnummer_toevoeging',
            'woonplaatsnaam': 'woonplaats',
            'wijknaam': 'wijknaam',
            'buurtnaam': 'buurtnaam',
        }

        sia_address_dict = {}
        for PDOK_key, sia_key in mapping.items():
            sia_address_dict[sia_key] = result[PDOK_key] if PDOK_key in result else ''
        lat, lon = rd_to_wgs(self.rd_x, self.rd_y)
        sia_address_dict["geometrie"] = Point((lon, lat)) 
        return sia_address_dict


class PDOKAddressValidation(BaseAddressValidation):
    PDOK_API_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1"

    def __init__(self):
        self.address_validation_url = f'{os.environ.get("PDOK_API_URL", self.PDOK_API_URL)}/suggest'

    def _search_result_to_address(self, result):
        mapping = {
            'straatnaam': 'straatnaam',
            'postcode': 'postcode',
            'huisnummer': 'huisnummer',
            'huisletter': 'huisletter',
            'huisnummertoevoeging': 'huisnummer_toevoeging',
            'woonplaatsnaam': 'woonplaats',
            'wijknaam': 'wijknaam',
            'buurtnaam': 'buurtnaam',
        }

        sia_address_dict = {}
        for PDOK_key, sia_key in mapping.items():
            sia_address_dict[sia_key] = result[PDOK_key] if PDOK_key in result else ''
        sia_address_dict["geometrie"] = result["centroide_ll"]
        return sia_address_dict

    def _pdok_request_query_params(self, address, lon=None, lat=None):
        query_dict = {}
        query_dict.update({'fl': '*'})
        query_dict.update({'rows': '5'})
        query_dict.update({'fq': ['type:adres', 'bron:BAG']})

        if 'woonplaats' in address and address['woonplaats'].strip():
            query_dict["fq"].append(f'woonplaatsnaam:{address["woonplaats"].strip()}')
        else:
            cleaned_pdok_cities_list = filter(lambda item: item, map(str.strip, DEFAULT_PDOK_CITIES))
            query_dict["fq"].append(f'''woonplaatsnaam:("{'" "'.join(cleaned_pdok_cities_list)}")''')

        if 'postcode' in address and address['postcode'].strip():
            query_dict["fq"].append(f'postcode:{address["postcode"].strip()}')

        # remove '', ' ' strings before formatting
        cleaned_pdok_list = filter(lambda item: item, map(str.strip, DEFAULT_PDOK_MUNICIPALITIES))
        query_dict["fq"].append(f'''gemeentenaam:("{'" "'.join(cleaned_pdok_list)}")''')

        straatnaam = address['openbare_ruimte'].strip()
        huisnummer = str(address['huisnummer']).strip()
        huisletter = address['huisletter'].strip() if 'huisletter' in address and address['huisletter'] else ''
        toevoeging = f'-{address["huisnummer_toevoeging"].strip()}' if 'huisnummer_toevoeging' in address and address['huisnummer_toevoeging'] else ''  # noqa

        if lon and lat:
            query_dict.update({'lon': lon, 'lat': lat})

        query_dict.update({'q': f'{straatnaam} {huisnummer}{huisletter}{toevoeging}'})

        return query_dict

    def _search(self, address, lon=None, lat=None, *args, **kwargs):
        try:
            query_params = self._pdok_request_query_params(address=address, lon=lon, lat=lat)
            logger.info(f"PDOK search query_params: {query_params}")
            response = get(self.address_validation_url, query_params)
            # response_reverse = get(self.address_validation_reverse_url, {"lat": query_params.get("lat"), "lon": query_params.get("lon"), "fl": ["wijknaam", "straatnaam", "huisnummer", "huisletter", "toevoeging", "postcode", "buurtnaam", "geometrie"]})

            logger.info("pdok response text: %s", response.text)
            response.raise_for_status()
        except RequestException as e:
            raise AddressValidationUnavailableException(e)
        return response.json()["response"]["docs"]
