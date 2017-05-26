# Bike Network Analyzer

Map of 'bikeable' trips following likely routes based on infrastructure preferences model, using 2011 Transportation for Tomorrow Survey origin/destination pairs and OpenStreetMap (extracted March 5, 2017). 'Bikeable' trips are defined as 1-5 km with no passengers.
![Sample map](https://raw.githubusercontent.com/TriTAG/bike-network-analyzer/master/sample.png)

- ![](https://placehold.it/15/ff0000/000000?text=+) `greatest cycling demand`
- ![](https://placehold.it/15/00ff00/000000?text=+) `least cycling demand`

## Usage
```> python likely_routes.py --osm data/waterloo-17-03-05.pbf --zones data/tts.geojson --zoneid GTA06 --od data/bikeable_wr.txt -n 10000 --output bikeable.geojson```

## Preference model
For now, the analyzer considers a single 'shortest' path for each origin/destination pair. (Future work may consider a broader array of likely route alternatives.) Path lengths are weighted roughly by how desireable the underlying infrastructure is for cycling on:
- regular street 1.0
- quiet street 0.85
- busy street 1.7
- bike path 0.33
- unpaved path 0.67
- sidewalk 4.0
- sharrows 0.7
- conventional bike lane 0.5
- protected bike lane 0.4
Weights are cumulative, e.g. a bike lane on a busy street would give 0.5\*1.7 = 0.85. Weights are loosely based on the route preference models of Hood et al. and Transport for London. 

## References
- Transportation for Tomorrow Survey: (Data Management Group)[http://dmg.utoronto.ca]
- (Open Street Map)[http://openstreetmap.org]
- Hood et al., (A GPS-based bicycle route choice model for San Francisco, California)[http://www.sfcta.org/sites/default/files/content/IT/CycleTracks/BikeRouteChoiceModel.pdf]
- Transport for London, (Cycle route choice)[http://content.tfl.gov.uk/understanding-cycle-route-choice.pdf]
