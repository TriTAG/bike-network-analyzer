#import osmnx as ox
import parse_osm
import argparse
import json
import re
import random
import networkx as nx
from rtree import index
from shapely.geometry import Point, asShape
from progress.bar import Bar
from shapely.ops import transform
from shapely.geometry import LineString
from functools import partial
import pyproj
from itertools import groupby
import math


def sample_nodes_by_zone(zone_file, graph, zond_id_property):
    num_zones = len(zone_file['features'])
    bar = Bar('Sorting graph nodes by zone',
              suffix='%(percent)d%% - %(eta_td)s', max=num_zones)
    nodeIdx = index.Index()
    for nid, data in graph.nodes_iter(data=True):
        data['point'] = Point(data['x'], data['y'])
        nodeIdx.insert(nid, data['point'].bounds)

    nodes = {}

    for feature in zone_file['features']:
        zone_id = str(int(feature['properties'][zond_id_property]))
        nodes[zone_id] = []

        shape = asShape(feature['geometry'])
        minx, miny, maxx, maxy = shape.bounds

        while len(nodes[zone_id]) < 500:
            pt = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
            if shape.intersects(pt):
                nodes[zone_id] += list(nodeIdx.nearest((minx, miny,
                                                        maxx, maxy)))
        bar.next()
    bar.finish()

    return nodes


def weight_graph(graph):
    bar = Bar('Adding weights to graph',
              suffix='%(percent)d%% - %(eta_td)s', max=graph.size())
    for u, v, d in graph.edges_iter(data=True):
        weight = 1
        if d['traffic'] == 'quiet':
            weight *= 0.85
        elif d['traffic'] == 'busy':
            weight *= 1.7
        elif d['traffic'] == 'path':
            weight *= 0.33
        elif d['traffic'] == 'unpaved':
            weight *= 0.67
        elif d['traffic'] == 'sidewalk':
            weight *= 4
        if d['bike_lane'] == 'sharrows':
            weight *= 0.7
        elif d['bike_lane'] == 'protected':
            weight *= 0.4
        elif d['bike_lane'] == 'lane':
            weight *= 0.5

        d['weight'] = weight * d['length']
        bar.next()
    bar.finish()


def get_od_pairs(pairsfile):
    pairs = []
    with open(pairsfile) as fp:
        dataPattern = re.compile(r'\s+(\d+)\s+(\d+)\s+(\d+)')
        for line in fp:
            m = dataPattern.match(line)
            if m:
                data = map(int, line.split())
                pairs += [(data[0], data[1])] * data[2]
    return pairs


def get_paths(pairs, num_samples, graph, nodes_by_zone):
    def dist(a, b):
        x1 = graph.node[a]['x']
        y1 = graph.node[a]['y']
        x2 = graph.node[b]['x']
        y2 = graph.node[b]['y']
        return (((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5) * 0.33

    segments = []
    bar = Bar('Finding paths', suffix='%(percent)d%% - %(eta_td)s',
              max=num_samples)
    for source, target in random.sample(pairs, num_samples):
        try:
            snode = random.choice(nodes_by_zone[str(source)])
            tnode = random.choice(nodes_by_zone[str(target)])
            path = nx.astar_path(graph, snode, tnode, dist)

            segments += list(zip(path[:-1], path[1:]))
        except Exception as e:
            print e
            print 'Cannot get from {0} to {1}'.format(source, target)
        bar.next()
    bar.finish()
    return segments


def categorize_paths(segments, graph):
    unique = [(k, len(list(g)))
              for k, g in groupby(sorted(segments, key=sorted), sorted)]
    biggest = max(zip(*unique)[1])

    def second(x):
        return round(math.sqrt(x[1]/float(biggest))*8.0)/10.0 + .2

    grouped = groupby(sorted(unique, key=second), second)

    colours = {
        10: '#ff0000',
        9: '#cf1f00',
        8: '#af3f00',
        7: '#9f5f00',
        6: '#7f7f00',
        5: '#5f9f00',
        4: '#3faf00',
        3: '#1fcf00',
        2: '#00ff00',
    }
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    utm17 = pyproj.Proj(proj='utm', zone=17, ellps='WGS84')
    google = pyproj.Proj(init='epsg:4326')
    project = partial(pyproj.transform, utm17, google)

    undirected_graph = nx.Graph(graph)
    for number, pairs in grouped:
        pairs = zip(*pairs)[0]

        feat = {"type": "Feature",
                "properties": {"stroke-opacity": number,
                               "stroke-color": colours[round(number*10)],
                               "stroke-width": number*5.0},
                "geometry": {"type": "MultiLineString", "coordinates": []}}

        for pair in pairs:
            data = undirected_graph.get_edge_data(*pair)
            if 'geometry' in data:
                line = transform(project, data['geometry'])
            else:
                line = LineString([(graph.node[pair[0]]['x'],
                                    graph.node[pair[0]]['y']),
                                   (graph.node[pair[1]]['x'],
                                    graph.node[pair[1]]['y'])])
                line = transform(project, line)
            feat['geometry']['coordinates'].append(line.coords[:])

        geojson['features'].append(feat)
    geojson['features'] = geojson['features'][1:]
    return geojson

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Bike trips')
    # parser.add_argument('integers', metavar='N', type=int, nargs='+',
    #                     help='an integer for the accumulator')
    parser.add_argument('--osm', dest='osm_file',
                        help='OSM file (pbf or xml)')
    parser.add_argument('--zones', dest='zones',
                        help='Zone shape file (geojson)')
    parser.add_argument('--zoneid', dest='zone_id',
                        help='Zone file id property', default='GTA06')
    parser.add_argument('--od', dest='odpairs',
                        help='Origin/desitnation pairs file')
    parser.add_argument('-n', dest='num_samples',
                        help='Number of trips to sample', type=int)
    parser.add_argument('--output', dest='outfile',
                        help='Output geojson file')

    args = parser.parse_args()

    # G = ox.graph_from_place(args.location)
    # G_projected = ox.project_graph(G)
    G = parse_osm.get_graph(args.osm_file)
    weight_graph(G)

    print 'Loading zone file...'
    with open(args.zones) as fp:
        zone_file = json.load(fp)

    nodes_by_zone = sample_nodes_by_zone(zone_file, G, args.zone_id)

    pairs = get_od_pairs(args.odpairs)

    segments = get_paths(pairs, args.num_samples, G, nodes_by_zone)
    geojson = categorize_paths(segments, G)

    with open(args.outfile, 'w') as fp:
        json.dump(geojson, fp)
