
import pandas as pd
import geopandas as gpd

from data_explorer.scenario_data import ScenarioData

class ScenarioComparison(object):
    def __init__(self, scenario0: ScenarioData, scenario1: ScenarioData):
        """Scenario comparison container. 
        Accessed via notebook or other results explorers.

        Args:
            scenario0 : Scenario results of do-nothing scenario.
            scenario1 : Scenario results of project scenario.
        """
        self.scenario0 = scenario0
        self.scenario1 = scenario1
        self.zones = scenario0.zones
        self.zone_ids = scenario0.zone_ids

    def accessibility(self, tour_type, mode = None):
        """
        Get accessibility values of tour type (and mode).

        Return : Series for tour type or mode.
        """

    def travel_times(self, time_period, mtx_type, ass_class, origin_zone, geometry = False):
        data1 = self.scenario1.costs_from(time_period, mtx_type, ass_class, origin_zone)
        data0 = self.scenario0.costs_from(time_period, mtx_type, ass_class, origin_zone)
        data = data0.merge(data1, on = "zone_id", suffixes=('0', '1'))
        data["difference"] = data["cost1"] - data["cost0"]
        if geometry:
            data = self.zones.merge(data, on='zone_id', how='left')
        return data
    