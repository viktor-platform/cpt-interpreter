from viktor.geo import GEFData as SDKGEFData


class CPTData(SDKGEFData):

    def __init__(self, cpt_dict: dict):
        super().__init__(gef_dict=cpt_dict)
