# Bike Network Analyzer

```> python likely_routes.py --osm data/waterloo-17-03-05.pbf --zones data/tts.geojson --zoneid GTA06 --od data/bikeable_wr.txt -n 10000 --output bikeable.geojson```

![Sample map](https://raw.githubusercontent.com/TriTAG/bike-network-analyzer/master/sample.png)
Map of 'bikeable' trips following likely routes based on infrastructure preferences model, using 2011 Transportation for Tomorrow Survey origin/destination pairs and OpenStreetMap (extracted March 5, 2017). 'Bikeable' trips are defined as 1-5 km with no passengers.

```diff
+ Green = least cycling demand
- Red = greatest cycling demand
```
