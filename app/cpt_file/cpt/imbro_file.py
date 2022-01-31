# pylint: disable=line-too-long, c-extension-no-member
from datetime import datetime
from pathlib import Path
from typing import List
from typing import Union

from lxml import etree
from munch import munchify
from viktor import File
from viktor.utils import render_jinja_template

from .cpt_data import CPTData
from .file_conversion import convert_xml_dict_to_cpt_dict
from .file_conversion import cpt_method
from .file_conversion import databloc_cols_def
from .file_conversion import replace_multiple
from .file_conversion import stop_criteria
from .file_conversion import undo_camelcase
from .file_conversion import xyid_codes
from .file_conversion import zid_codes



class IMBROFile:

    def __init__(self, file_content: bytes):
        self.file_content = file_content

    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> 'IMBROFile':
        """Instantiates the IMBROFile class from a file_path to an IMBRO xml file."""
        with Path(file_path).open('rb') as xml_file:
            file_content = xml_file.read()
        return cls(file_content=file_content)

    def parse(self, additional_columns: List[str], verbose: bool = False,
              return_gef_data_obj: bool = False) -> Union[dict, CPTData]:
        """Parses the xml file and returns either a cpt dictionary or a CPTData object"""
        xml_dict = self._parse_xml_file(self.file_content)
        cpt_dict = convert_xml_dict_to_cpt_dict(xml_dict)
        if return_gef_data_obj:
            return CPTData(cpt_dict=cpt_dict)
        return cpt_dict

    def _parse_xml_file(self, file_content: bytes) -> dict:
        return self._parse_xml_to_dict_recursively(etree.fromstring(file_content))

    @classmethod
    def _parse_xml_to_dict_recursively(cls, node):
        """Builds the data object from the xml structure passed, therefore preserving the structure and the values"""
        if not node.getchildren():
            return node.text

        grand_children = {}
        for child in node.getchildren():
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag == 'parameters':
                grand_children['parameters'] = [(sub_child.tag.split('}')[-1], sub_child.text in {'ja', 1})
                                                for sub_child in child]
            else:
                grand_children[tag] = cls._parse_xml_to_dict_recursively(child)
        return grand_children

    def convert_to_gef_file_content(self):
        cpt_data = munchify(self._parse_xml_file(self.file_content))
        # BUILD HEADERS
        cone_penetration_test = cpt_data.conePenetrometerSurvey.conePenetrationTest

        headers = {
            'FILEDATE': datetime.today().strftime('%Y, %m, %d'),
            'STARTDATE': cone_penetration_test.phenomenonTime.TimeInstant.timePosition[:10].replace('-', ', '),
            'STARTTIME': cone_penetration_test.phenomenonTime.TimeInstant.timePosition[11:19].replace(':', ', '),
            'TESTID': cpt_data.broId,
            'ZID': '{}, {}'.format(zid_codes[cpt_data.deliveredVerticalPosition.verticalDatum],
                                   cpt_data.deliveredVerticalPosition.offset),
            'XYID': '{}, {}, {}'.format(xyid_codes[cpt_data.standardizedLocation.coordinateTransformation],
                                        *cpt_data.deliveredLocation.location.pos.split(' ')),
            'MEASUREMENTTEXT': [
                '4, {}, conustype'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.conePenetrometerType),
                '5, {}, omschrijving sondeerapparaat'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.description),
                '6, {} / {}, sondeernorm en kwaliteitsklasse'.format(cpt_data.cptStandard,
                                                                     cpt_data.conePenetrometerSurvey.qualityClass),
                '9, {}, lokaal verticaal referentiepunt'.format(
                    cpt_data.deliveredVerticalPosition.localVerticalReferencePoint),
                # '20, {}, signaalbewerking uitgevoerd'.format(),   # Not found in xml
                '21, {}, bewerking onderbrekingen uitgevoerd'.format(
                    cpt_data.conePenetrometerSurvey.procedure.interruptionProcessingPerformed),
                '42, {}, methode verticale positiebepaling'.format(
                    cpt_data.deliveredVerticalPosition.verticalPositioningMethod),
                '43, {}, methode locatiebepaling'.format(
                    cpt_data.deliveredLocation.horizontalPositioningMethod),
                '101, bronhouder, {}, -'.format(cpt_data.deliveryAccountableParty),
                '103, {}, kader inwinning'.format(undo_camelcase(cpt_data.surveyPurpose)),
                '105, {}'.format(cpt_data.deliveredLocation.horizontalPositioningDate.date.replace('-', ', ')),
                '107, {}'.format(
                    cpt_data.deliveredVerticalPosition.verticalPositioningDate.date.replace('-', ', ')),
                '109, {}, dissipatietest uitgevoerd'.format(
                    cpt_data.conePenetrometerSurvey.dissipationTestPerformed),
                '110, {}, expertcorrectie uitgevoerd'.format(
                    cpt_data.conePenetrometerSurvey.procedure.expertCorrectionPerformed),
                '112, {}'.format(cpt_data.conePenetrometerSurvey.finalProcessingDate.date),
                '113, {}'.format(cpt_data.conePenetrometerSurvey.finalProcessingDate.date),
                '115, {}, kwaliteitsregime'.format(cpt_data.qualityRegime),
                '116, {}'.format(replace_multiple(cpt_data.registrationHistory.objectRegistrationTime[:19],
                                                  original_chars='-T:',
                                                  replace_char=', ')),
                '117, {}, registratiestatus'.format(cpt_data.registrationHistory.registrationStatus),
                '118, {}'.format(replace_multiple(cpt_data.registrationHistory.registrationCompletionTime[:19],
                                                  original_chars='-T:',
                                                  replace_char=', ')),
                '119, {}, gecorrigeerd'.format(cpt_data.registrationHistory.corrected),
                '121, {}, in onderzoek'.format(cpt_data.registrationHistory.underReview),
                '123, {}, uit registratie genomen'.format(cpt_data.registrationHistory.deregistered),
                '125, {}, weer in registratie genomen'.format(cpt_data.registrationHistory.reregistered),
                '127, 4258, {}'.format(cpt_data.standardizedLocation.location.pos.replace(' ', ', ')),
                '128, {}, toegepaste transformatie'.format(cpt_data.standardizedLocation.coordinateTransformation),
            ],
            'MEASUREMENTVAR': [
                '1, {}, mm2 (vierkante millimeter), oppervlakte conuspunt'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.coneSurfaceArea),
                '2, {}, mm2 (vierkante millimeter), oppervlakte kleefmantel'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.frictionSleeveSurfaceArea),
                '3, {}, geen, oppervlaktequotiënt conuspunt'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.coneSurfaceQuotient),
                '4, {}, geen, oppervlaktequotiënt kleefmantel'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.frictionSleeveSurfaceQuotient),
                '5, {}, mm (millimeter), afstand conus tot midden kleefmantel'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.coneToFrictionSleeveDistance),
                '12, {}, -, sondeermethode'.format(cpt_method[cpt_data.conePenetrometerSurvey.cptMethod]),
                '13, {}, m (meter), voorgeboord tot'.format(
                    cpt_data.conePenetrometerSurvey.trajectory.predrilledDepth),
                '16, {}, m (meter), einddiepte'.format(cpt_data.conePenetrometerSurvey.trajectory.finalDepth),
                '17, {}, -, stopcriterium'.format(
                    stop_criteria[cpt_data.conePenetrometerSurvey.stopCriterion]),
                '20, {}, MPa (megaPascal), conusweerstand vooraf'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.zeroLoadMeasurement.coneResistanceBefore),
                '21, {}, MPa (megaPascal), conusweerstand achteraf'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.zeroLoadMeasurement.coneResistanceAfter),
                '22, {}, MPa (megaPascal), plaatselijke wrijving vooraf'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.zeroLoadMeasurement.localFrictionBefore),
                '23, {}, MPa (megaPascal), plaatselijke wrijving achteraf'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.zeroLoadMeasurement.localFrictionAfter),
                # '24, -, MPa (megaPascal), waterspanning u1 vooraf'.format(),      # Not found in XML
                # '25, -, MPa (megaPascal), waterspanning u1 achteraf'.format(),    # Not found in XML
                '26, {}, MPa (megaPascal), waterspanning u2 vooraf'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.zeroLoadMeasurement.porePressureU2Before),
                '27, {}, MPa (megaPascal), waterspanning u2 achteraf'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.zeroLoadMeasurement.porePressureU2After),
                # '28, -, MPa (megaPascal), waterspanning u3 vooraf'.format(),      # Not found in XML
                # '29, -, MPa (megaPascal), waterspanning u3 achteraf'.format(),    # Not found in XML
                '30, {}, ° (graden), hellingresultante vooraf'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.zeroLoadMeasurement.inclinationResultantBefore),
                '31, {}, ° (graden), hellingresultante achteraf'.format(
                    cpt_data.conePenetrometerSurvey.conePenetrometer.zeroLoadMeasurement.inclinationResultantAfter),
            ]
        }

        # BUILD META
        meta = {}
        columns = []
        meta['COLUMNINFO'] = []
        for i, (tag, value) in enumerate(cpt_data.conePenetrometerSurvey.parameters):
            tag_spaces = undo_camelcase(tag)
            if value is True:
                columns.append(i)
                meta['COLUMNINFO'].append(
                    {**[w for w in databloc_cols_def if w['description'] == tag_spaces][0], 'colnum': len(columns)})
        meta['COLUMN'] = len(columns)

        # BUILD DATA
        token_separator = ','
        block_separator = ';'
        if cone_penetration_test.cptResult.encoding.TextEncoding:
            token_separator = cone_penetration_test.cptResult.encoding.TextEncoding.tokenSeparator
            block_separator = cone_penetration_test.cptResult.encoding.TextEncoding.blockSeparator

        data = ''
        data_rows = [row.split(token_separator) for row in
                     cone_penetration_test.cptResult['values'].split(
                         block_separator)[:-1]]
        data_rows = sorted(data_rows, key=lambda x: float(x[0]))

        for row in data_rows:
            data += ';'.join([str(row[column_idx]) for column_idx in columns]) + ';!\n'

        meta['LASTSCAN'] = len(data_rows)
        variables = dict(headers=headers, meta=meta, data=data)
        with open(Path(__file__).parent / 'template_gef.txt', 'rb') as template:
            result = render_jinja_template(template, variables)
        return result
