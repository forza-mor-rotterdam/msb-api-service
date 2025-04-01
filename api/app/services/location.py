import logging

from services.pdok import PDOKReverseRD
from services.rd_convert import rd_to_wgs

logger = logging.getLogger(__name__)


def get_validated_address(rd_x, rd_y):
    validated_address = None
    address_by_rd = PDOKReverseRD()

    try:
        validated_address = address_by_rd.search_address_with_distance(
            rd_x=rd_x,
            rd_y=rd_y,
        )
        if validated_address:
            return address_by_rd._search_result_to_address(validated_address[0])
    except Exception as e:
        logger.error(e)
    
    try:
        validated_address = address_by_rd.search_object_with_distance(
            rd_x=rd_x,
            rd_y=rd_y,
        )
        if validated_address:
            return address_by_rd._search_result_to_address(validated_address[0])
    except Exception as e:
        logger.error(e)

    return {}
