import xmltodict
import uuid
import lxml
from lxml import etree


def strip_ns_prefix(tree):
    #xpath query for selecting all element nodes in namespace
    query = "descendant-or-self::*[namespace-uri()!='']"
    #for each element returned by the above xpath query...
    for element in tree.xpath(query):
        #replace element name with its local name
        element.tag = etree.QName(element).localname
    return tree


def parse_mor_melding_aanmaken_response(response_text):
    response_root_tag_name = "AanmakenMeldingResult"
    root = etree.XML(response_text)
    root_without_ns_prefix = strip_ns_prefix(root)
    etree.cleanup_namespaces(root_without_ns_prefix)
    for tag in root_without_ns_prefix.iter():
        for k in tag.attrib.keys():
            del tag.attrib[k]
    etree.cleanup_namespaces(root_without_ns_prefix)
    new_root = root_without_ns_prefix.find(f".//{response_root_tag_name}")
    dd = xmltodict.parse(etree.tostring(new_root))
    return dd.get(response_root_tag_name, {})


def generate_message_identification():
    return str(uuid.uuid4())