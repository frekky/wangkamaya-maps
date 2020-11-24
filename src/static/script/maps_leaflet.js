var map = null, loader = null, infodiv = null;
var isLoaded = false;

window.rbush = RBush;

// initialise the label engine
var labelRenderer = new L.LabelTextCollision({
        collisionFlg: true, // don't draw overlapping names
    });

var iconLayer = L.canvasIconLayer({
    pane: 'markerPane',
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
        layers: [satellite, borders, roads, iconLayer],
        //{ south: -54.1, west: 83.2, north: 9.3, east: 163.9 }
        center: new L.latLng(-22.68, 118.35),
        zoom: 7,
        maxBounds: L.latLngBounds(L.latLng(9.3, 163.9), L.latLng(-54.1, 83.2)),
        //renderer: labelRenderer,
    });

    reloadViewport();
    
    loader = $(".loader");
    infodiv = $("#infodiv").hide();
    
    map.on('zoomend moveend', reloadViewport);

    // ensure the markers & labels are shown above the streets overlay
    //map.getPane('overlayPane').style.zIndex = parseInt(map.getPane('esri-labels').style.zIndex) + 100;
    
    map.on('click', function () {
        openInfo(null);
    });

    iconLayer.addOnClickListener(function (e, layer) {
        console.log(layer);
        if (layer)
            openInfo(layer);
    });
    
    /*iconLayer.addOnHoverListener(function (e, layer) {
        if (!layer) return;
        layer.setStyle(getMarkerHoverStyle(layer.feature));
        console.log('mouseover: feature text=' + layer.options.text);
    });*/
    
    /*.on("mouseout", function (e, layer) {
        if (!layer) return;
        layer.setStyle(getMarkerStyle(layer.feature));
        console.log('mouseout: feature text=' + layer.options.text);
    });*/

});


function toCoords(latLng) {
    return "" + latLng.lng.toFixed(10) + "," + latLng.lat.toFixed(10); 
}

// returns text label for given Feature
function getLabel(marker) {
    var f = marker.feature;
    var names = "";
    for (var i = 0; i < f.properties.names.length; i++) {
        names += f.properties.names[i].name + " (" + f.properties.names[i].lang.name + ") ";
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

function getMarkerColour(feature) {
    var col = '#ccc';
    if (feature.properties.names.length > 0) {
        col = feature.properties.names[0].lang.colour;
    }
    return col;
}

function getMarkerStyle(feature) {
    var col = getMarkerColour(feature);
    return {
        stroke: true,
        weight: 3,
        color: col,
        fill: col,
        fillOpacity: 0.5,
        radius: 8,
    };
}

function getMarkerHoverStyle(feature) {
    var col = getMarkerColour(feature);
    var newCol = tinycolor(col).lighten(30).toString();
    return {
        stroke: true,
        weight: 3,
        color: newCol,
        fill: newCol,
        fillOpacity: 0.8,
        radius: 8,
    };
}

function getMarkerActiveStyle(feature) {
    var col = getMarkerColour(feature);
    var newCol = tinycolor(col).desaturate(40).complement().toString();
    return {
        stroke: true,
        weight: 4,
        color: newCol,
        fill: newCol,
        fillOpacity: 0.5,
        radius: 8,
    };
}


var infoLayer = null, infoMarker = null;
function openInfo(layer) {
    console.log(layer);
    console.log(infoMarker);
    if (infoMarker && infoMarker.layer != layer) {
        infoMarker.remove();
        window.infoMarker = null;
    }

    if (infoLayer) {
        infoLayer.setStyle(getMarkerStyle(infoLayer.feature));
    }
    infoLayer = layer;

    if (!layer) {
        infodiv.hide();
    } else {
        infodiv.text("Loading...");
        infoMarker = L.marker(layer.getLatLng(), {
            interactive: false,
        }).addTo(map);
        infoMarker.layer = layer;
        layer.setStyle(getMarkerActiveStyle(layer.feature));
        layer.bringToFront();

        $.ajax('/info/' + layer.feature.properties.id + "/", {
            success: function (data, status, jqxhr) {
                infodiv.html(data).show();
            },
            error: function (jqxhr, textStatus, error) {
                infodiv.text("Error retrieving info: " + textStatus).show();
            }
        });
    }
}

var iconsList = {};

function handleGeoJson(data, status, jqxhr) {
    // process data returned from the geojson web service (expects a FeatureCollection)
    if (geoJsonLayer) {
        geoJsonLayer.remove();
    }

    /* process icons and prepare them for use on the map */
    for (var iconName in data.metadata.icons) {
        if (iconName in iconsList)
            continue;
        iconsList[iconName] = L.icon({
            iconUrl: data.metadata.icons[iconName],
            iconSize: [32, 32],
            iconAnchor: [16, 15],
        });
    }

    var markers = [];
    geoJsonLayer = L.geoJSON(data, {
        pointToLayer: function (point, latLng) {
            const markerOpts = {
                keyboard: false,
            };
            /*return L.circleMarker(latLng, {
                bubblingMouseEvents: false,
                //interactive: true,
                //renderer: labelRenderer,
                //pane: 'markerPane',
            });*/

            return L.marker(latLng, markerOpts);
        },
        style: getMarkerStyle,
        onEachFeature: function (feature, layer) {
            var id = feature.properties.id;
            if (id in features) {
                features[id].remove();
            }
            features[feature.properties.id] = layer;
            layer.options.text = getLabel(layer);
            layer.options.icon = iconsList[feature.properties.icon];
            markers.push(layer);
        },
    });//.addTo(map);

    iconLayer.addLayers(markers);
    
    console.log("Added " + data.features.length + " features to map, total=" + Object.keys(features).length);
    console.log(data.metadata)

    if (!isLoaded) {
        isLoaded = true;
        loader.hide(200);
    }
}

function reloadViewport() {
    var bbox = map.getBounds();
    var url = "/data/" + toCoords(bbox.getSouthWest()) + "/" + toCoords(bbox.getNorthEast()) + "/";
    $.ajax(url, {
        cache: false,
        dataType: "json",
        success: handleGeoJson,
        error: function (jqxhr, textStatus, error) {
            // do something with error
        }
    });
}
