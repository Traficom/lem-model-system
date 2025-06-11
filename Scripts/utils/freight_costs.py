import numpy
from typing import Dict
import utils.log as log
from parameters.marine_ship import port_draught_limit, ship_draught_speed


def calc_cost(mode: str, unit_costs: Dict[str, Dict],
              impedance: Dict[str, numpy.ndarray], model_category: str,
              origs: dict = None, dests: dict = None):
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
    origs : dict
        Origin border id (FIHEL/SESTO...) : str
            Centroid id : int
    dests : dict
        Destination border id (FIHEL/SESTO...) : str
            Centroid id : int

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
            else:
                return get_foreign_ship_cost(unit_costs, impedance, 
                                             model_category, origs, dests)
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
                   model_category: str,
                   draught_mask: numpy.ndarray = 1):
    """Calculates ship mode specific cost parts
    
    Parameters
    ----------
    unit_params : Dict[str, float]
        unit cost name : unit cost value
    impedance : Dict[str, numpy.ndarray]
        Type (time/dist/canal_cost) : numpy 2d matrix
    model_category : str
        'domestic' or 'foreign'
    draught_mask : numpy.ndarray, Optional
        marine ship eligibility to traverse at specific draught. By default 1
    
    Returns
    -------
    ship_cost : numpy.ndarray
        impedance type cost : numpy 2d matrix
    """
    ship_cost = (impedance["time"] * ship_params["time"] * draught_mask
                 + impedance["dist"] * ship_params["dist"] * draught_mask
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

def get_foreign_ship_cost(unit_costs: Dict[str, dict], impedance: Dict[str, dict], 
                          model_category: str, origs: dict, dests: dict):
    """Fetch smallest general cost for each marine ship in unit costs.
    
    Parameters
    ----------
    unit_costs : Dict[str, dict]
        Freight mode (truck/freight_train/ship) : mode
            Mode (other_dry_cargo...) : draught
                draught (4m...) : unit cost name
                    unit cost name : unit cost value
    impedance : Dict[str, dict]
        Sub ship mode (general_cargo/container_ship...) : attribute
            Type (dist) : numpy 2d matrix
    model_category : str
        purpose estimation category, domestic or foreign
    origs : dict
        Origin border id (FIHEL/SESTO...) : str
            Centroid id : int
    dests : dict
        Destination border id (FIHEL/SESTO...) : str
            Centroid id : int

    Returns
    -------
    dict
        Marine ship type (general_cargo/container ship...) : matrix
            Mtx type (cost/mode/draught) : numpy.ndarray
    """
    none_mtx = numpy.full((len(origs), len(dests)), None, dtype="float64")
    ship_info = {}
    for mode in unit_costs["ship"].keys():
        if mode == "domestic_vessel":
            continue
        ship_info[mode] = {
            "cost": none_mtx.copy(),
            "draught": none_mtx.astype("object")
        }
        for ship_draught, ship_params in unit_costs["ship"][mode].items():
            draught = int(ship_draught[:-1])
            impedance[mode]["time"] = (impedance[mode]["dist"] 
                                       / ship_draught_speed[mode][ship_draught]
                                       * 60)
            mask = evaluate_port_draught(draught, port_draught_limit[mode], 
                                         origs, dests)
            cost = calc_ship_cost(ship_params, impedance[mode], 
                                  model_category, draught_mask=mask)
            mask = minimize(ship_info[mode]["cost"], cost)
            ship_info[mode]["cost"][mask] = cost[mask]
            ship_info[mode]["draught"][mask] = ship_draught
    return ship_info

def evaluate_port_draught(draught: int, port_draught: dict, 
                          ext_origin: dict, ext_dest: dict) -> bool:
    """Evaluates whether a ship type can enter to a Finnish port within draught 
    restrictions. Uses ext zones to deduce whether evaluation should be done
    for origin or destination zones. Result matrix contains 1 for enable to 
    enter and np.inf for unable to enter.

    Parameters
    ----------
    ship_draught : int
        draught for marine ship type in unit costs
    port_draught : dict[str, int]
        Finnish port name id (FIHEL/FISKV...) : draught limit
    ext_origin : dict
        External origin name id (FIHEL/EETLL...) : emme centroid id
    ext_dest : dict
        External destination name id (FIHEL/EETLL...) : emme centroid id

    Returns
    -------
    numpy.ndarray
        Mask (1/np.inf)
    """
    mask = numpy.ones((len(ext_origin.values()), len(ext_dest.values())))
    if set(ext_origin.keys()).issubset(set(port_draught.keys())):
        origin_based = True
        fin_ports = list(ext_origin)
    else:
        origin_based = False
        fin_ports = list(ext_dest)
    for index, port in enumerate(fin_ports):
        if draught > port_draught[port]:
            mask[index][0:] = numpy.inf
    return mask if origin_based else mask.T

def minimize(current_cost: numpy.ndarray, calc_cost: numpy.ndarray):
    """Evaluate if calculated cost for ship type and draught can minimize
    costs while being finite.
    
    Parameters
    ----------
    current_cost : numpy.ndarray
        currently allocated cost for marine mode-draught
    calc_cost : numpy.ndarray
        calculated cost for marine mode-draught to compare

    Returns
    -------
    numpy.ndarray
        bool mask matrix
    """
    return (
        (~numpy.isfinite(current_cost) & (~numpy.isinf(calc_cost))) 
        | ((~numpy.isinf(calc_cost)) & (calc_cost < current_cost))
    )
