import xmltodict
import uuid


def validate_mor_melding_aanmaken_response(response_text):
    d = xmltodict.parse(response_text)
    response_root = d.get("s:Envelope", {}).get("s:Body", {}).get("AanmakenMeldingResponse", {}).get("AanmakenMeldingResult", {})
    r = {}
    def iteritems_recursive(dd):
        for k,v in dd.items():
            k = k.split(":")[1]
            if isinstance(v, dict):
                v = {k2: v2 for k2, v2 in v.items() if not k2.startswith("@")}
                if not r.get(k) and v:
                    r[k] = {}
                else:
                    r[k] = None
                for k1,v1 in iteritems_recursive(v):
                    r[k][k1] = v1
                    yield k1, v1
            else:
                yield k,v

    [o for o in iteritems_recursive(response_root)]
    return r


def generate_message_identification():
    return str(uuid.uuid4())