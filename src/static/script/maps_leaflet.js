var map = null, loader = null, infodiv = null;

var labelRenderer = new L.LabelTextCollision({
        collisionFlg: true,
    });

$(function () {

    /*var osmUrl = 'http://tile.openstreetmap.jp/{z}/{x}/{y}.png'
    var osmAttrib = 'Map data  <a href="http://openstreetmap.jp">OpenStreetMap</a> contributors';
    var osm = new L.TileLayer(
            osmUrl, {
                maxZoom : 18,
                attribution : osmAttrib
            });*/
    
    // use the free ESRI imagery layers and labels    
    var satellite = L.esri.basemapLayer("Imagery"),//("ImageryClarity"),
        borders = L.esri.basemapLayer("ImageryLabels"),
        roads = L.esri.basemapLayer("ImageryTransportation");
    
    map = L.map('mapdiv', {
        layers: [satellite, borders, roads],
        //{ south: -54.1, west: 83.2, north: 9.3, east: 163.9 }
        center: new L.latLng(-22.68, 118.35),
        zoom: 7,
        maxBounds: L.latLngBounds(L.latLng(9.3, 163.9), L.latLng(-54.1, 83.2)),
        renderer: labelRenderer,
    });

    reloadViewport();
    
    loader = $(".loader").hide(200);
    infodiv = $("#infodiv").hide();
    
    map.on('zoomend moveend', reloadViewport);
    
    map.on('click', function () {
        if (infodiv)
            infodiv.hide();
    });
});


function toCoords(latLng) {
    return "" + latLng.lng.toFixed(10) + "," + latLng.lat.toFixed(10); 
}

// returns text label for given Feature
function getLabel(marker) {
    var f = marker.feature;
    var names = "";
    for (var i = 0; i < f.properties.names.length; i++) {
        names += f.properties.names[i].name + " (" + f.properties.names[i].lang[1] + ")\n";
    }
    return names.slice(0, -1);
}

// Formats Place data as html for the infoWindow
function getInfoContent(layer) {
    var f = layer.feature.properties;
    var s = '<div class="place-info">';
    s += '<span class="title">' + getLabel(layer) + '</span><br><br>';
    for (var prop in f) {
        var val = f[prop]; 
        s += '<span class="title">' + prop + '</span><br>';
        if (val == null || typeof val != "object") {
          s += '<span class="value">' + val + '</span><br>';
        } else {
          for (var vp in val) {
            s += '<span class="value">' + vp + ': ' + val[vp] + '</span><br>';
          }
        }
    }
    s = s.slice(0, -4) + '</div>';
    return s;
}

// keep track of all loaded features in the form {id: geoJsonObject}
var features = {};

var geoJsonLayer = null;

function reloadViewport() {
    var bbox = map.getBounds();
    var url = "/data/" + toCoords(bbox.getSouthWest()) + "/" + toCoords(bbox.getNorthEast()) + "/";
    $.ajax(url, {
        cache: false,
        dataType: "json",
        success: function handleGeoDataAjax(data, status, jqxhr) {
            // process data returned from the geojson web service (expects a FeatureCollection)
            if (geoJsonLayer) {
                geoJsonLayer.remove();
            }
            var markers = [];
            geoJsonLayer = L.geoJSON(data, {
                pointToLayer: function (point, latLng) {
                    return L.circleMarker(latLng, {
                        radius: 5,
                    });
                    //return L.marker(latLng);
                },
                style: function getPathOptions(feature) {
                    return {
                        stroke: true,
                        color: '#ff6',//'#6af',//'#f63',
                        weight: 3,
                        fill: '#ffffff',
                        fillOpacity: 0.5,
                    };
                },
                onEachFeature: function (feature, layer) {
                    const tooltipOptions = {
                        // tooltip options
                        direction: 'left',
                        permanent: true,
                        //sticky: false,
                        interactive: true,
                        className: 'place-name-tooltip',
                    };
                    var id = feature.properties.id;
                    if (id in features) {
                        features[id].remove();
                    }
                    features[feature.properties.id] = layer;
                    layer.options.text = getLabel(layer);
                    //layer.bindTooltip(getLabel(layer), tooltipOptions);
                    //L.tooltipLayout.resetMarker(layer);
                    markers.push(layer);
                },
            }).bindPopup(function (layer) {
                // layer is a feature??
                console.log(layer);
                return getInfoContent(layer);
            }).addTo(map).on("click", function (evt) {
                console.log(evt.layer);
                if (infodiv) {
                    infodiv.html(getInfoContent(evt.layer)).show();
                }
            });
            console.log(markers);
            //L.tooltipLayout.initialize(map, markers, null); 
            
            /*function onPolylineCreated(pl) {
                //ply.remove();
            });*/
            console.log("Added " + data.features.length + " features to map, total=" + Object.keys(features).length);
        },
    });
}
