from typing import Iterable, Union, Tuple
from shapely import Point, LineString

from utils.calc_noise import NoiseModel


class NODE:
    geom_type = "Point"

    def __new__(cls, node):
        return Point(node.x, node.y)


class LINK:
    geom_type = "LineString"

    def __new__(cls, link):
        return LineString(link.shape)


def geometries(scenario,
               objects: Iterable,
               geom_type: Union[NODE, LINK]) -> Tuple[Iterable, dict]:
    """Turn EMME network objects into GeoJSON records.

    Parameters
    ----------
    scenario : inro.emme.database.scenario.Scenario
        Scenario for which extra attributes are exported
    objects : Iterable
        Iterator over network objects (links or nodes)
    geom_type : NODE or LINK
        NODE or LINK geometry type

    Returns
    -------
    Iterable
        Iterator of GeoJSON records
    dict
        Fiona schema of record types
    """
    attr_names = [attr.name for attr in scenario.extra_attributes()
        if attr.type == geom_type.__name__]
    recs = ({
        "geometry": geom_type(obj),
        "properties": {attr: float(obj[attr]) for attr in attr_names}
    } for obj in objects)
    schema = {
        "geometry": geom_type.geom_type,
        "properties": {attr: "float" for attr in attr_names}
    }
    return recs, schema


def print_links(network, resultdata):
    """Dump link attributes with wkt coordinates to file.

    Includes noise calculation (works well only when morning peak hour
    is assigned in the same EMME skenario). Noise calculation could be
    removed from here if noise extra attribute would be added.

    Parameters
    ----------
    network : inro.emme.network.Network
        Network where whole-day results are stored
    """
    attr_names = network.attributes("LINK")
    resultdata.print_line(
        "Link\tnode_i\tnode_j" + "\t".join(attr_names) + "\tNoise_zone_width", "links")
    noisemodel = NoiseModel(
        network, ("@car_work_vrk", "@car_leisure_vrk", "@van_vrk"),
        ("@truck_vrk", "@trailer_truck_vrk"))
    for link in network.links():
        wkt = LineString(link.shape).wkt
        attrs = "\t".join([str(link[attr]) for attr in attr_names])
        noise_zone_width = noisemodel.calc_noise(link)
        resultdata.print_line(
            wkt + "\t" + str(link.i_node.id) + "\t" + str(link.j_node.id) + "\t" + attrs + "\t" + str(noise_zone_width), "links")
    resultdata.flush()
