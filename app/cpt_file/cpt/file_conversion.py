import re
from collections import defaultdict

from munch import munchify
from viktor import UserException

databloc_cols_def = [
    {
        'id': 1,
        'description': 'penetration length',
        'units': 'm'},
    {
        'id': 2,
        'description': 'cone resistance',
        'units': 'MPa'},
    {
        'id': 3,
        'description': 'local friction',
        'units': 'MPa'},
    {
        'id': 4,
        'description': 'friction ratio',
        'units': '-'},
    {
        'id': 5,
        'description': 'pore pressure u1',
        'units': 'MPa'},
    {
        'id': 6,
        'description': 'pore pressure u2',
        'units': 'MPa'},
    {
        'id': 7,
        'description': 'pore pressure u3',
        'units': 'MPa'},
    {
        'id': 8,
        'description': 'inclination resultant',
        'units': 'degrees'},
    {
        'id': 9,
        'description': 'inclination ns',
        'units': 'degrees'},
    {
        'id': 10,
        'description': 'inclination ew',
        'units': 'degrees'},
    {
        'id': 11,
        'description': 'depth',
        'units': 'm'},
    {
        'id': 12,
        'description': 'elapsed time',
        'units': 's'},
    {
        'id': 13,
        'description': 'corrected cone resistance',
        'units': 'MPa'},
    {
        'id': 14,
        'description': 'net cone resistance',
        'units': 'MPa'},
    {
        'id': 15,
        'description': 'pore ratio',
        'units': '-'},
    {
        'id': 21,
        'description': 'inclination x',
        'units': 'degrees'},
    {
        'id': 22,
        'description': 'inclination y',
        'units': 'degrees'},
    {
        'id': 23,
        'description': 'electrical conductivity',
        'units': 'S/m'},
    {
        'id': 31,
        'description': 'magnetic field strength x',
        'units': 'nT'},
    {
        'id': 32,
        'description': 'magnetic field strength y',
        'units': 'nT'},
    {
        'id': 33,
        'description': 'magnetic field strength z',
        'units': 'nT'},
    {
        'id': 34,
        'description': 'magnetic field strength total',
        'units': 'nT'},
    {
        'id': 35,
        'description': 'magnetic inclination',
        'units': 'degrees'},
    {
        'id': 36,
        'description': 'magnetic declination',
        'units': 'degrees'}
]

# TODO: this will silence parsing of unknown ZID codes, check if it is the desired behaviour
zid_codes = defaultdict(lambda: '-', {
    'Low Low Water Spring': '00001',
    'NAP': '31000',
    'Ostend Level': '32000',
    'TAW': '32001',
    'Normal Null': '49000'
})

# TODO: this will silence parsing of unknown stop criteria codes, check if it is the desired behaviour
stop_criteria = defaultdict(lambda: '-', {
    'wegdrukkracht': '1',
    'obstakel': '6',
    'storing': '8',
    'einddiepte': '0',
    'bezwijkrisico': '7'
})

# TODO: this will silence parsing of unknown cone penetration test method codes, check if it is the desired behaviour
cpt_method = defaultdict(lambda: '-', {
    'elektrischContinu': '4',
    'elektrisch': '0'
})

# TODO: this will silence parsing of unknown XYID codes, check if it is the desired behaviour
xyid_codes = defaultdict(lambda: '-', {
    'Geographic Coordinate System': '00001',
    'SPCS': '01000',
    'RD': '31000',
    'RDNAPTRANS2008': '31000',
    'UTM-3N': '31001',
    'UTM-9N': '31002',
    'Belgian Bessel': '32000',
    'Gauss-Krüger': '49000'
})

GEF_XML_MAPPING = {
    'Rf': 'frictionRatio',
    'fs': 'localFriction',
    'qc': 'coneResistance',
    'elevation': 'depth',
    'corrected_depth': 'depth'
}


def convert_xml_dict_to_cpt_dict(xml_dict):
    xml_data = munchify(xml_dict).dispatchDocument.CPT_O
    measurement_data = {
        'Rf': [],
        'fs': [],
        'qc': [],
        'elevation': [],
        'corrected_depth': []}
    elevation_offset = int(float(xml_data.deliveredVerticalPosition.offset) * 1000)
    mapping = {}
    for i, (tag, value) in enumerate(xml_data.conePenetrometerSurvey.parameters):
        for key, label in GEF_XML_MAPPING.items():
            if tag == label and value is True:
                try:
                    mapping[key] = i
                except KeyError:
                    raise UserException(f'Missing "{key}" in XML data')

    token_separator = ','
    block_separator = ';'
    if xml_data.conePenetrometerSurvey.conePenetrationTest.cptResult.encoding.TextEncoding:
        x_ = xml_data
        token_separator = x_.conePenetrometerSurvey.conePenetrationTest.cptResult.encoding.TextEncoding.tokenSeparator
        block_separator = x_.conePenetrometerSurvey.conePenetrationTest.cptResult.encoding.TextEncoding.blockSeparator

    data_rows = [row.split(token_separator)
                 for row in
                 xml_data.conePenetrometerSurvey.conePenetrationTest.cptResult['values'].split(block_separator)[:-1]]

    # For some reason, in some xml files the rows are scrambled, so we need to sort them by penetration length
    try:
        sorted_data = sorted(data_rows, key=lambda x: float(x[mapping['elevation']]))
    except KeyError:
        raise UserException('Missing "elevation" in XML data')

    for data in sorted_data:
        for key, col_index in mapping.items():
            data_value = float(data[col_index])
            if data_value == float(-999999):
                measurement_data[key].append(None)
            else:
                if key == 'elevation':
                    data_point = elevation_offset - int(data_value * 1000)
                elif key == 'corrected_depth':
                    data_point = int(data_value * 1e3)
                elif key == 'Rf':
                    data_point = data_value / 100
                else:
                    data_point = data_value
                measurement_data[key].append(data_point)

    if not measurement_data['Rf']:  # If Rf is not provided in xml file, then calculate it
        measurement_data['Rf'] = [fs / qc for qc, fs in zip(measurement_data['qc'], measurement_data['fs'])]

    coneSurfaceQuotient = float(xml_data.conePenetrometerSurvey.conePenetrometer.coneSurfaceQuotient) \
        if 'coneSurfaceQuotient' in xml_data.keys() else None

    frictionSleeveSurfaceQuotient = float(xml_data.conePenetrometerSurvey.conePenetrometer.coneSurfaceQuotient) \
        if 'frictionSleeveSurfaceQuotient' in xml_data.keys() else None

    coneToFrictionSleeveDistance = float(
        xml_data.conePenetrometerSurvey.conePenetrometer.coneToFrictionSleeveDistance) \
        if 'coneToFrictionSleeveDistance' in xml_data.keys() else None

    coneSurfaceArea = float(xml_data.conePenetrometerSurvey.conePenetrometer.coneSurfaceArea) \
        if 'coneSurfaceArea' in xml_data.keys() else None

    frictionSleeveSurfaceArea = float(xml_data.conePenetrometerSurvey.conePenetrometer.frictionSleeveSurfaceArea) \
        if 'frictionSleeveSurfaceArea' in xml_data.keys() else None

    return {
        'headers': {
            'name': xml_data.broId,
            'gef_file_date': xml_data.researchReportDate.date,
            'height_system': xml_data.deliveredVerticalPosition.verticalDatum,
            'fixed_horizontal_level': xml_data.deliveredVerticalPosition.localVerticalReferencePoint,
            'cone_type': xml_data.conePenetrometerSurvey.conePenetrometer.conePenetrometerType,
            'cone_tip_area': coneSurfaceArea,
            'friction_sleeve_area': frictionSleeveSurfaceArea,
            'surface_area_quotient_tip': coneSurfaceQuotient,
            'surface_area_quotient_friction_sleeve': frictionSleeveSurfaceQuotient,
            'distance_cone_to_centre_friction_sleeve': coneToFrictionSleeveDistance,
            'excavation_depth': xml_data.conePenetrometerSurvey.trajectory.predrilledDepth,
            'corrected_depth': float(xml_data.conePenetrometerSurvey.trajectory.finalDepth) * 1000,
            'x_y_coordinates': list(map(float, xml_data.deliveredLocation.location.pos.split(' '))),
            'ground_level_wrt_reference_m': float(xml_data.deliveredVerticalPosition.offset),
            'ground_level_wrt_reference': float(xml_data.deliveredVerticalPosition.offset) * 1000,
        },
        'measurement_data': measurement_data
    }


def undo_camelcase(string):
    return re.sub("([a-z])([A-Z])", r"\g<1> \g<2>", string).lower()


def replace_multiple(string, original_chars, replace_char):
    for original_char in original_chars:
        string = string.replace(original_char, replace_char)
    return string
