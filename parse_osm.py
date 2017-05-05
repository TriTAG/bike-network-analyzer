__author__ = 'mboos'

from imposm.parser import OSMParser
from pyproj import Proj
import networkx as nx
from math import sqrt
from osmnx import simplify_graph
from progress.spinner import Spinner

proj = Proj(proj='utm', zone=17, ellps='WGS84')


class OSMloader(object):
    def __init__(self,):
        self.spinner = Spinner('Loading OSM ')
        self.coords = {}
        self.graph = nx.MultiDiGraph()
    def nodes(self, nodes):
        for osmid, x,y in nodes:
            if y < 45 and y > 42.83 and x < -77.9 and x > -80.9:
                self.coords[long(osmid)] = proj(x,y)
                self.spinner.next()

    def ways(self, ways):
        for osmid, tags, refs in ways:
            traffic = 'regular'
            bike_lane = 'none'
            oneway = False
            contraflow = False
            if 'highway' not in tags or tags['highway'] not in ['primary', 'secondary', 'tertiary', 'unclassified',
                                                                'residential', 'service', 'path', 'cycleway', 'footway']:
                continue
            if tags['highway'] in ['primary', 'secondary']:
                traffic = 'busy'
            elif tags['highway'] in ['residential']:
                traffic = 'quiet'
            elif tags['highway'] in ['path', 'cycleway']:
                traffic = 'path'
                if 'cycleway' in tags and tags['cycleway'] == 'no':
                    continue
                if 'surface' in tags and tags['surface'] != 'asphalt':
                    traffic = 'unpaved'
            elif tags['highway'] in ['footway']:
                if 'bicycles' in tags and (tags['bicycles'] == 'yes' or tags['bicycles'] == 'designated'):
                    traffic = 'path'
                else:
                    traffic = 'sidewalk'
            if 'cycleway' in tags and tags['highway'] != 'path':
                if tags['cycleway'] == 'shared_lane':
                    bike_lane = 'sharrows'
                elif tags['cycleway'] == 'track':
                    bike_lane = 'protected'
                elif tags['cycleway'] != 'no':
                    bike_lane = 'lane'
            if 'cycleway:left' in tags and tags['cycleway:left'] == 'opposite_lane':
                contraflow = True
            if 'oneway' in tags and tags['oneway'] == 'yes':
                oneway = True
            missing = False
            for node in refs:
                if long(node) not in self.coords:
                    missing = True
                    # if 'name' in tags and 'Weber' in tags['name']:
                    #     print osmid, node
                    break
            if missing or len(refs) < 2:
                # if 'name' in tags and 'Weber' in tags['name']:
                #     print osmid, missing, refs
                continue
            last_node = None
            for node in refs:
                node = long(node)
                self.graph.add_node(node, x=self.coords[node][0], y=self.coords[node][1])
                if last_node is not None:
                    distance = sqrt((self.coords[node][0] - self.coords[last_node][0])**2 + (self.coords[node][1] - self.coords[last_node][1])**2)
                    #print distance
                    self.graph.add_edge(last_node, node, length=distance, traffic=traffic, bike_lane=bike_lane, osmid=osmid)
                    if not oneway:
                        self.graph.add_edge(node, last_node, length=distance, traffic=traffic, bike_lane=bike_lane, osmid=osmid)
                    elif contraflow:
                        self.graph.add_edge(node, last_node, length=distance, traffic=traffic, bike_lane='lane', osmid=osmid)
                last_node = node
            self.spinner.next()

def get_graph(filename):
    grabber = OSMloader()
    p = OSMParser(concurrency=1, coords_callback=grabber.nodes, ways_callback=grabber.ways)
    p.parse(filename)
    grabber.spinner.finish()
    print ''

    print 'Simplifying graph... '
    graph = max(nx.strongly_connected_component_subgraphs(grabber.graph, copy=True), key=len)
    return nx.DiGraph(simplify_graph(graph, strict=False))
