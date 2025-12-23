import xmltodict


def xml_to_json(xml_string: str):
    return xmltodict.parse(xml_string)
