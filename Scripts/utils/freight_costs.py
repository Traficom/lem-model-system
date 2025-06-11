import numpy
from typing import Dict
import utils.log as log


def calc_cost(mode: str, unit_costs: Dict[str, Dict],
              impedance: Dict[str, numpy.ndarray],
              model_category: str):
    """Calculate freight costs.

    Parameters
    ----------
    mode : str
        Freight mode (truck/freight_train/ship)
    unit_costs : Dict[str, Dict]
        Freight mode (truck/freight_train/ship) : mode
            Mode (truck/trailer_truck) : unit cost name
                unit cost name : unit cost value
    impedance : Dict[str, numpy.ndarray]
        Type (time/dist/toll_cost) : numpy 2d matrix
    model_category : str
        purpose modelling category, within Finland as 'domestic, 
        outside Finland as 'foreign'

    Returns
    ----------
    road_cost : numpy.ndarray
        impedance type cost : numpy 2d matrix
    """
    match mode:
        case "truck":
            return calc_road_cost(unit_costs, impedance, model_category)
        case "freight_train":
            return calc_rail_cost(unit_costs, impedance, model_category)
        case "ship":
            if model_category == "domestic":
                return get_domestic_ship_cost(unit_costs, impedance, model_category)
        case _:
            msg = f"Unknown mode {mode}"
            log.error(msg)
            raise ValueError(msg)

def calc_road_cost(unit_costs: Dict[str, Dict],
                   impedance: Dict[str, numpy.ndarray],
                   model_category: str):
    """Calculate freight road costs.

    Parameters
    ----------
    unit_costs : Dict[str, Dict]
        Freight mode (truck/freight_train/ship) : mode
            Mode (truck/trailer_truck) : unit cost name
                unit cost name : unit cost value
    impedance : Dict[str, numpy.ndarray]
        Type (time/dist/toll_cost) : numpy 2d matrix
    model_category : str
        'domestic' or 'foreign'

    Returns
    ----------
    road_cost : numpy.ndarray
        impedance type cost : numpy 2d matrix
    """
    mode_cost = {}
    for mode, params in unit_costs["truck"].items():
        mode_cost[mode] = ((sum(impedance[k] * params[k] for k in impedance) 
                           + params["terminal_cost"])
                           * params[f"{model_category}_distribution"])
    return sum(mode_cost.values())

def calc_rail_cost(unit_costs: Dict[str, Dict],
                   impedance: Dict[str, numpy.ndarray],
                   model_category: str):
    """Calculate freight rail based costs.

    Parameters
    ----------
    unit_costs : Dict[str, Dict]
        Freight mode (truck/freight_train/ship) : mode
            Mode (electric_train/diesel_train) : unit cost name
                unit cost name : unit cost value
    impedance : Dict[str, numpy.ndarray]
        Type (time/dist/toll_cost) : numpy 2d matrix
    model_category : str
        'domestic' or 'foreign'

    Returns
    ----------
    rail_cost : numpy.ndarray
        impedance type cost : numpy 2d matrix
    """
    mode_cost = {}
    for mode, params in unit_costs["freight_train"].items():
        mode_cost[mode] = (impedance["time"] * params["time"]
                           + impedance["dist"] * params["dist"]
                           + params["terminal_cost"])
    rail_cost = mode_cost["diesel_train"]
    rail_aux_cost = get_aux_cost(unit_costs, impedance, model_category)
    return rail_cost + rail_aux_cost

def get_domestic_ship_cost(unit_costs: Dict[str, Dict],
                           impedance: Dict[str, numpy.ndarray],
                           model_category: str):
    """Fetch domestic freight ship based costs. 

    Parameters
    ----------
    unit_costs : Dict[str, Dict]
        Freight mode (truck/freight_train/ship) : mode
            Mode (other_dry_cargo...) : draught
                draught (4m...) : unit cost name
                    unit cost name : unit cost value
    impedance : Dict[str, numpy.ndarray]
        Type (time/dist/toll_cost/canal_cost) : numpy 2d matrix
    model_category : str
        'domestic' or 'foreign'

    Returns
    ----------
    ship_cost : numpy.ndarray
        impedance type cost : numpy 2d matrix
    """
    ship_params = unit_costs["ship"]["domestic_vessel"]
    ship_cost = calc_ship_cost(ship_params, impedance, model_category)
    ship_aux_cost = get_aux_cost(unit_costs, impedance, model_category)
    return ship_cost + ship_aux_cost

def calc_ship_cost(ship_params: Dict[str, float], 
                   impedance: Dict[str, numpy.ndarray],
                   model_category: str):
    """Calculates ship mode specific cost parts
    
    Parameters
    ----------
    unit_params : Dict[str, float]
        unit cost name : unit cost value
    impedance : Dict[str, numpy.ndarray]
        Type (time/dist/canal_cost) : numpy 2d matrix
    model_category : str
        'domestic' or 'foreign'
    
    Returns
    -------
    ship_cost : numpy.ndarray
        impedance type cost : numpy 2d matrix
    """
    ship_cost = (impedance["time"] * ship_params["time"]
                 + impedance["dist"] * ship_params["dist"]
                 + ship_params["terminal_cost"])
    if model_category == "domestic":
        ship_cost += impedance["canal_cost"] * ship_params["canal_cost"]
    return ship_cost

def get_aux_cost(unit_costs: Dict[str, Dict],
                 impedance: Dict[str, numpy.ndarray],
                 model_category: str):
    """Checks whether auxiliary mode distance is over twice as long
    as main mode distance or if main mode mode has not been used 
    at all. In such cases, assigns inf for said OD pairs.
    Otherwise calculates actual auxiliary cost.

    Parameters
    ----------
    unit_costs : Dict[str, Dict]
        Freight mode (truck/freight_train/ship)
    impedance : Dict[str, numpy.ndarray]
        Type (time/dist/toll_cost) : numpy 2d matrix
    model_category : str
        'domestic' or 'foreign'

    Returns
    ----------
    auxiliary road cost : numpy.ndarray
        impedance type cost : numpy 2d matrix
    """
    impedance_aux = {
        "dist": impedance["aux_dist"],
        "time": impedance["aux_time"],
        "toll_cost": impedance["toll_cost"]
    }
    aux_cost = numpy.where(
        (impedance["aux_dist"] > (impedance["dist"]*2))
        | (impedance["dist"] == 0),
        numpy.inf,
        calc_road_cost(unit_costs, impedance_aux, model_category))
    return aux_cost
