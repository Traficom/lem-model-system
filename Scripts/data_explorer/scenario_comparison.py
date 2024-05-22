
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


    def accessibility(self, tour_type, mode = None):
        """
        Get accessibility values of tour type (and mode).

        Return : Series for tour type or mode.
        """

        
    def travel_times(self, time_period, mtx_type, ass_class, origin_zone):
        return (self.scenario1.get_costs_from(time_period, mtx_type, ass_class, origin_zone) 
                - self.scenario0.get_costs_from(time_period, mtx_type, ass_class, origin_zone))
    
    def demand(self):
        return


    def mode_shares(self):
        return


    def export_comparison(self, cols = list):
        """self.zones join cols
        geopandas write to file to results_path"""
        return
