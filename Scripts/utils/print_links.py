from typing import Iterable, Tuple
from shapely.geometry import Point, LineString

from utils.calc_noise import NoiseModel


class GeometryType:
    name: str
    geom_type: str
    def __new__(cls, obj):
        pass


class Node(GeometryType):
    name = "NODE"
    geom_type = "Point"

    def __new__(cls, node):
        return Point(node.x, node.y)


class Link(GeometryType):
    name = "LINK"
    geom_type = "LineString"

    def __new__(cls, link):
        return LineString(link.shape)


def geometries(attr_names: Iterable[str],
               objects: Iterable,
               geom_type: GeometryType) -> Tuple[Iterable, dict]:
    """Turn EMME network objects into GeoJSON records.

    Parameters
    ----------
    attr_names : List of str
        List of extra attributes in network objects
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
    recs = ({
        "geometry": geom_type(obj),
        "properties": {
            "id": obj.id,
            **{attr[1:]: obj[attr] for attr in attr_names},
        }
    } for obj in objects)
    schema = {
        "geometry": geom_type.geom_type,
        "properties": {
            "id": "str",
            **{attr[1:]: "float" for attr in attr_names}
        }
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
