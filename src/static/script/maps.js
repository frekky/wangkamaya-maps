var map, infoWindow;

// callback when the map is loaded
function initMap() {
    map = new google.maps.Map(document.getElementById('gmap'), {
        center: {lat: -22.68, lng: 118.35},
        zoom: 7,
        mapTypeId: google.maps.MapTypeId.HYBRID,
        restriction: {
            //latLngBounds: { south: -54.1, west: 83.2, north: 9.3, east: 163.9 },
            strictBounds: false,
        },
    });

    infoWindow = new google.maps.InfoWindow({
        pixelOffset: new google.maps.Size(0, -27),
    });

    // construct widget to display lat lng coords of mouse pointer
    var latLngWidget = $('<div class="map-widget"/>');
    var latDisplay = $('<span>').appendTo(latLngWidget);
    var lngDisplay = $('<span>').appendTo(latLngWidget);
    console.log(latLngWidget);
    
    map.data.addListener('click', function(event) {
        console.log(event.feature);
        position = {}
        event.feature.getGeometry().forEachLatLng(function (l) { position = l; });
        infoWindow.setContent(getInfoContent(event.feature));
        infoWindow.setPosition(position);
        infoWindow.open(map);
    });

    map.addListener('mousemove', function(event) {
        var pos = event.latLng;
        latDisplay.text(pos.lat().toFixed(4));
        lngDisplay.text(pos.lng().toFixed(4));
    });
    
    var bounds_timer = null;
    map.addListener('bounds_changed', function(event) {
        if (bounds_timer != null)
            window.clearTimeout(bounds_timer);
        bounds_timer = window.setTimeout(function () {
            reloadViewport();
            bounds_timer = null;
        }, 100);
    });

    google.maps.event.addListenerOnce(map, 'tilesloaded', function () {
        reloadViewport();
        map.controls[google.maps.ControlPosition.TOP_RIGHT].push(latLngWidget[0]); 
    });
}

function toCoords(latLng) {
    return "" + latLng.lng().toFixed(10) + "," + latLng.lat().toFixed(10); 
}

function reloadViewport() {
    var bbox = map.getBounds();
    var url = "/data/" + toCoords(bbox.getSouthWest()) + "/" + toCoords(bbox.getNorthEast()) + "/";
    $.ajax(url, {
        cache: false,
        dataType: "json",
        success: function handleGeoDataAjax(data, status, jqxhr) {
            // process data returned from the geojson web service (expects a FeatureCollection)
            map.data.addGeoJson(data, {
                idPropertyName: "id",
            });
            console.log("Added " + data.features.length + " features to map");
        },
    });
}

function reloadData() {
    // clear features
    var numFeats = 0;
    map.data.forEach(function (feat) {
        map.data.remove(feat);
        numFeats++;
    });
    console.log("Removed " + numFeats + " features from map");

    // now reload data
    map.data.loadGeoJson("/data/");
    resetFilter();
}

// human readable names for feature properties
var propFriendlyNames = {
    "name": "", // use name as title where appropriate
    "name_eng": "English Name",
    "place_type": "Place Type",
    "lang": "Language",
    "source": "Data source",
    "desc": "Description",
}

// Formats Place data as html for the infoWindow
function getInfoContent(f) {
    var s = '<div class="place-info">';
    f.forEachProperty(function (val, prop) {
        var title = prop in propFriendlyNames ? propFriendlyNames[prop] : prop;
        if (title == "") {
             s += '<span class="title">' + (val == "" ? "(Unknown name)" : val) + '</span><br>';
        } else {
            s += '<span class="title">' + title + '</span><br>';
            s += '<span class="value">' + val + '</span><br>';
        }
    });
    s = s.slice(0, -4) + '</div>';
    return s;
}

function doFilter(prop, val) {
    filters[prop] = val;
    console.log("set filters: " + JSON.stringify(filters));
    map.data.setStyle(getFeatureStyle);
}

function resetFilter() {
    for (var prop in filters) {
        filters[prop] = '';
    }
    map.data.setStyle(getFeatureStyle);
}

var filters = {
    "lang": "",
}

function getFeatureStyle(feat) {

    for (var prop in filters) {
        if (filters[prop] == '')
            continue;

        var val = feat.getProperty(prop);
        if (val != filters[prop] || (val == '' && filters[prop] == "Unknown")) {
            return { visible: false };
        }
    }
    return {
        visible: true,
        title: feat.getProperty("name"),
    };
}
