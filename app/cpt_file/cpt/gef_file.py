# pylint: disable=line-too-long, c-extension-no-member
from collections import OrderedDict
from copy import copy
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Union

import numpy as np
from lxml import etree
from munch import Munch
from munch import munchify
from viktor import UserException
from viktor.geo import GEFFile as SDKGEFFile

from ..constants import ADDITIONAL_COLUMNS


def _yes_no(key: str, cpt_dict) -> str:
    return 'ja' if key in cpt_dict['measurement_data'].keys() else 'nee'


class GEFFile(SDKGEFFile):
    """This class is created to add the :function: `convert_to_imbro_file_content` to the GEFFile class"""
    MISSING_VALUE_STR = "MISSING_VALUE"
    NO_DEFAULT_STR = "NO_DEFAULT"

    def convert_to_imbro_file_content(self) -> bytes:
        """Converts the GEFFile data to an IMBRO XML file."""
        cpt_dict = munchify(self.parse(additional_columns=ADDITIONAL_COLUMNS, return_gef_data_obj=False))
        time_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z')
        try:
            data = {
                "broId": cpt_dict.headers.name,
                "researchReportDate": {"date": cpt_dict.headers.gef_file_date},
                "deliveredVerticalPosition": {
                    "verticalDatum": cpt_dict.headers.height_system,
                    "localVerticalReferencePoint": cpt_dict.headers.fixed_horizontal_level,
                    "offset": cpt_dict.headers.ground_level_wrt_reference_m,
                    "verticalPositioningDate": {"date": cpt_dict.headers.gef_file_date}
                },
                "conePenetrometerSurvey": {
                    "conePenetrometer": {
                        "conePenetrometerType": cpt_dict.headers.cone_type,
                        "coneSurfaceArea": cpt_dict.headers.cone_tip_area,
                        "frictionSleeveSurfaceArea": cpt_dict.headers.friction_sleeve_area,
                        "coneSurfaceQuotient": cpt_dict.headers.surface_area_quotient_tip,
                        "frictionSleeveSurfaceQuotient": cpt_dict.headers.surface_area_quotient_friction_sleeve,
                        "coneToFrictionSleeveDistance": cpt_dict.headers.distance_cone_to_centre_friction_sleeve,
                    },
                    "trajectory": {
                        "predrilledDepth": cpt_dict.headers.excavation_depth,
                        "finalDepth": cpt_dict.headers.corrected_depth * 0.001,
                    },
                    "parameters": {
                        "depth": 'ja',
                        "penetrationLength": 'ja',
                        "inclinationResultant": _yes_no('inclination', cpt_dict),
                        "localFriction": _yes_no('fs', cpt_dict),
                        "frictionRatio": _yes_no('Rf', cpt_dict),
                        "coneResistance": _yes_no('qc', cpt_dict)
                    },
                    "finalProcessingDate": {"date": cpt_dict.headers.gef_file_date},
                    "conePenetrationTest": {
                        "cptResult": {"values": ''},
                    },
                },
                "deliveredLocation": {
                    "location": {"pos": ' '.join(map(str, cpt_dict.headers.x_y_coordinates))},
                    "horizontalPositioningDate": {"date": cpt_dict.headers.gef_file_date}
                },
                "registrationHistory": {
                    "objectRegistrationTime": time_str[:-2] + ':' + time_str[-2:],  # Fixes format of strftime for timezone
                    "registrationStatus": 'voltooid',
                    "registrationCompletionTime": time_str[:-2] + ':' + time_str[-2:]
                }
            }
        except AttributeError as ae:
            raise UserException(f'Could not convert to xml format, missing parameter {ae}')

        if 'measurement_standard' in cpt_dict.headers.keys():
            ms = cpt_dict.headers.measurement_standard
            if '/' in ms:
                standard, quality_class = ms.split('/')
                data["cptStandard"] = standard.strip()
                data["conePenetrometerSurvey"]["qualityClass"] = quality_class.strip()

        # data points
        data_len = len(cpt_dict.measurement_data.fs)
        values = np.full((25, data_len), np.nan)
        values[0, :] = np.linspace(0, cpt_dict.headers.depth * 0.001, data_len)  # penetration_length
        values[1, :] = np.linspace(0, cpt_dict.headers.corrected_depth * 0.001, data_len)  # depth
        if 'qc' in cpt_dict['measurement_data'].keys():
            values[3, :] = cpt_dict['measurement_data']['qc']  # coneResistance
        if 'inclination' in cpt_dict['measurement_data'].keys():
            values[15, :] = cpt_dict['measurement_data']['inclination']  # inclination
        if 'fs' in cpt_dict['measurement_data'].keys():
            values[18, :] = cpt_dict['measurement_data']['fs']  # localFriction
        if 'Rf' in cpt_dict['measurement_data'].keys():
            values[24, :] = [Rf * 100 if Rf else Rf for Rf in cpt_dict['measurement_data']['Rf']]  # frictionRatio

        result_str = ''
        for row in list(values.T):
            result_str += ','.join(['-999999' if np.isnan(num) else '{:.3f}'.format(num) for num in row]) + ';'
        data["conePenetrometerSurvey"]["conePenetrationTest"]["cptResult"]['values'] = result_str

        formatted_data = self._reformat_using_template(data, self.template)
        root = self._build_xml(formatted_data)

        return etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True, standalone=True)

    @classmethod
    def _build_xml(cls, templated_data: dict, parent: Union[etree.Element, etree.SubElement] = None):
        """Builds an xml tree from the templated data."""
        base_element = None
        for tag, element_data in templated_data.items():
            if parent is None:
                elem = etree.Element(tag, nsmap=element_data['nsmap'], attrib=element_data['attributes'])
                base_element = elem
            else:
                elem = etree.SubElement(parent, tag, nsmap=element_data['nsmap'], attrib=element_data['attributes'])
            if isinstance(element_data['value'], OrderedDict):
                cls._build_xml(templated_data=element_data['value'], parent=elem)
            else:
                elem.text = '' if element_data['value'] is None else str(element_data['value'])
        return base_element

    @classmethod
    def _reformat_using_template(cls, data: Munch, template: dict, skip_root: bool = True):
        """Takes a data object and fills in the values in the template structure."""
        filled_template = deepcopy(template)
        if skip_root:
            root_tag = list(template.keys())[0]
            filled_template[root_tag]['value'] = cls._reformat_using_template(data, template[root_tag]['value'],
                                                                              skip_root=False)
        else:
            for tag, value in data.items():
                tag_in_template = None
                for template_tag in template.keys():
                    temp_tag = copy(template_tag)
                    if '}' in temp_tag:
                        temp_tag = temp_tag.split('}')[-1]
                    if tag == temp_tag:
                        tag_in_template = template_tag
                        break
                if tag_in_template is None:
                    print(f"ERROR: tag {tag} not found in template IMBRO XML")
                    continue

                if isinstance(value, dict):
                    filled_template[tag_in_template]['value'] = \
                        cls._reformat_using_template(value, template[tag_in_template]['value'], skip_root=False)
                else:
                    filled_template[tag_in_template]['value'] = value
        return filled_template

    @property
    def template(self) -> dict:
        """Loads a template xml file, from which it extracts structure, namespaces, attributes and default values."""
        template_file = Path(__file__).parent / 'template_imbro.xml'
        with open(template_file, 'r') as f:
            content = f.read().encode('utf-8')

        return self._parse_xml_template(etree.fromstring(content))

    def _parse_xml_template(self, node: etree.Element, parent_nsmap: dict = None) -> dict:
        """Loads template into dictionary that preserves fields, structure, namespaces, attributes and default values.

        The `OrderedDict` ensures that the output xml follows the same order as the template."""
        structure = OrderedDict()
        structure['attributes'] = node.attrib or {}
        structure['default'] = node.text

        # Add nsmap based on nsmap of node and nsmap of parent node
        structure['nsmap'] = parent_nsmap or node.nsmap
        if node.nsmap and parent_nsmap and node.nsmap != parent_nsmap:
            structure['nsmap'] = {key: node.nsmap[key] for key in node.nsmap.keys() - parent_nsmap.keys()}

        # Add child element in an ordered dictionary, if no child elements, only provide node content (text)
        structure['value'] = node.text
        if node.getchildren():
            structure['value'] = OrderedDict()
            for child in node.getchildren():
                structure['value'][child.tag] = self._parse_xml_template(child, parent_nsmap=structure['nsmap'])

        # If not root node, return the structure OrderedDict
        if node.getparent():
            return structure

        # If root node, manually add default namespace and return main dictionary
        structure['nsmap'][None] = 'http://www.broservices.nl/xsd/dscpt/1.1'
        return {node.tag: structure}

    # TODO: Figure out whether the code below can be re-used
    # def get_missing_fields(self, data=None):
    #     """
    #     Checks which data fields have not been filled.
    #     :param data: data structure with field values. By default uses the data managed by the object itself (recommended approach)
    #     :return: a list with the paths of the missing fields of the xml (excluding namespace information)
    #     """
    #     data = data or self._data
    #     data = unmunchify(data)
    #     formatted_data = self._reformat_using_template(data, self._template)
    #     root = self._build_xml(formatted_data)
    #     tree = etree.ElementTree(root)
    #     tree = self._strip_namespaces(tree)
    #     missing = []
    #     for el in root.iter():
    #         if el.text == self.MISSING_VALUE_STR:
    #             path = tree.getpath(el)[1:]
    #             missing.append(path)
    #     return missing
    #
    # def fill_missing_fields_with_defaults(self, data=None):
    #     """
    #     Fills all the fields which have not been filled and for which a default exists in the template
    #     :param data: data structure with field values. By default uses the data managed by the object itself
    #     (recommended approach)
    #     :return: the data structure with newly filled fields when applicable
    #     """
    #     data = data or self._data
    #     data = unmunchify(data)
    #     templated_data = self._reformat_using_template(data, self._template)
    #     templated_data = self._fill_missing_fields_with_defaults_templated(templated_data=templated_data)
    #     self._data = self._parse_xml_to_dict(self._build_xml(templated_data))
    #     return self._data
    #
    # @classmethod
    # def _fill_missing_fields_with_defaults_templated(cls, templated_data=None, skip_root=True):
    #     """
    #     Helper method for :func:`fill_missing_fields_with_defaults`
    #     :param templated_data: data in the template structure (i.e. passed to :func:`_reformat_using_template` before)
    #     :param skip_root: Whether to skip the root node (used internally for recursive calls, no need to use externally)
    #     :return: the templated data with missing values replaced with defaults when a default exists for them.
    #     """
    #     if skip_root:
    #         root_tag = list(templated_data.keys())[0]
    #         templated_data[root_tag]['value'] = cls._fill_missing_fields_with_defaults_templated(
    #             templated_data=templated_data[root_tag]['value'], skip_root=False)
    #     else:
    #         for node_data in templated_data.values():
    #             if isinstance(node_data['value'], OrderedDict):
    #                 node_data['value'] = cls._fill_missing_fields_with_defaults_templated(
    #                     templated_data=node_data['value'], skip_root=False)
    #             else:
    #                 if node_data['value'] == cls.MISSING_VALUE_STR and not node_data['default'] == cls.NO_DEFAULT_STR:
    #                     node_data['value'] = node_data['default']
    #     return templated_data
    #
    # @staticmethod
    # def _strip_namespaces(tree):
    #     """
    #     Removes namespaces from the tags of an xml tree. This is useful to declutter the structure for display.
    #     :param tree: an xml tree object (etree.ElementTree)
    #     :return: the same tree object but with namespaces removed
    #     """
    #     # xpath query for selecting all element nodes in namespace
    #     query = "descendant-or-self::*[namespace-uri()!='']"
    #     # for each element returned by the above xpath query...
    #     for element in tree.xpath(query):
    #         # replace element name with its local name
    #         element.tag = etree.QName(element).localname
    #     return tree
