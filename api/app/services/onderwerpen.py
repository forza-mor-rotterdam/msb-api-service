import logging
import os

from services.main import BaseService

logger = logging.getLogger(__name__)


class OnderwerpenService(BaseService):
    _v = "v1"
    _api_path: str = f"/api/{_v}"

    class MeerdereOnderwerpenGevonden(Exception):
        ...
    class OnderwerpNietGevonden(Exception):
        ...

    def _get_url(self, url):
        return f"{self._api_base_url}{self._relatieve_url(url)}"

    def __init__(self, *args, **kwargs: dict):
        self._api_base_url = os.environ.get("ONDERWERPEN_URL")
        super().__init__(*args, **kwargs)

    def get_category_url(self, meldr_onderwerp):
        response = self._do_request(
            f"{self._api_path}/category/?name={meldr_onderwerp}",
        )
        if response.status_code == 200:
            return self._to_json(response)
        logentry = f"get_category_url: Verwacht status code 200, kreeg status code '{response.status_code}', text: {response.text}"
        logger.error(logentry)
        raise OnderwerpenService.DataOphalenFout(logentry)
