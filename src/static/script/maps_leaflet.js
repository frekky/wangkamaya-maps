var map = null, loader = null;
var isLoaded = false;
var iconClickTimer = null;

// alias for leaflet.canvas-markers.js
window.rbush = RBush;

/* cache all the places we know about, only request the ones we don't already have
 * placeCache is populated with markers for each place, keyed by feature.properties.id */
var placeCache = {}, iconsList = {}, langCache = {};
var newPlaces = {
    iconMarkers: [],
    circleMarkers: [],
};

// initialise the label engine
var labelRenderer = new L.LabelTextCollision({
    collisionFlg: true, // don't draw overlapping names
    offset: {x: 10, y: 5}
});

var iconLayer = L.canvasIconLayer({
    pane: 'markerPane',
});


// list of icon markers which have yet to be added to the map, after geoJSON calls
var newIconMarkers = [];

// initialise geoJSON parser
var geoJsonLayer = L.geoJSON(null, {
    pointToLayer: function (point, latLng) {
        // draw a small dot for each place, complemented by the icon marker & place name
        // the labels plugin works with circleMarkers but not with icon marker plugin... :((
        const circleMarkerOpts = {
            bubblingMouseEvents: true,
            interactive: false,
            renderer: labelRenderer,
            pane: 'markerPane',
            radius: 5,
            stroke: true,
            color: '#fff',
            weight: 1,
            fill: true,
            fillColor: '#000',
            fillOpacity: 1.0,
        }
        return L.circleMarker(latLng, circleMarkerOpts);
    },
    style: function (feature) {
        return {
            fillColor: getMarkerColour(feature),
        };
    },
    filter: function (feature) {
        return !(feature.properties.id in placeCache);
    },
    onEachFeature: function (feature, layer) {
        /* skip this feature if it is already in the cache */
        var id = feature.properties.id;
        if (id in placeCache) {
            return;
        }

        // create marker with icon & store for later adding to map
        var iconMarker = L.marker(layer.getLatLng(), {
            keyboard: false,
            icon: iconsList[feature.properties.icon],
        });
        iconMarker.feature = feature;

        // add text to the circle marker to make the labes plugin work
        layer.options.text = getLabel(layer);
        
        // now update the cache
        newIconMarkers.push(iconMarker);
        placeCache[id] = {
            iconMarker: iconMarker,
            circleMarker: layer,
        };
    },
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
        layers: [satellite, borders, roads, iconLayer, geoJsonLayer],
        center: {lat: -21.571, lng: 118.716},
        zoom: 8,
        // equivalent to google.maps.LatLngBounds({ south: -54.1, west: 83.2, north: 9.3, east: 163.9 })
        maxBounds: L.latLngBounds(L.latLng(9.3, 163.9), L.latLng(-54.1, 83.2)),
        zoomControl: false,
    });

    L.control.scale({
        imperial: false,
        position: 'bottomright',
    }).addTo(map);

    L.control.zoom({
        position: 'topright',
    }).addTo(map);

    var infoControl = new InfoControl({
        position: 'topright',
    }).addTo(map);

    reloadViewport();
    
    loader = $(".loader");
    
    map.on('zoomend moveend', reloadViewport);

    // ensure the markers & labels are shown above the streets overlay
    map.getPane('overlayPane').style.zIndex = parseInt(map.getPane('esri-labels').style.zIndex) + 100;
    
    map.on('click', function () {
        // can't separate map clicks and iconLayer clicks, here is a timer-based hack to fix event firing twice
        if (iconClickTimer != null)
            return;
        openInfo(null);
    });

    iconLayer.addOnClickListener(function (e, markers) {
        L.DomEvent.stopPropagation(e);

        // here begins the true click-event timer hack
        if (iconClickTimer != null) {
            window.clearTimeout(iconClickTimer);
        }
        iconClickTimer = window.setTimeout(function () {
            console.log(markers);
            if (markers.data) {
                openInfo(markers.data);
            } else if (markers[0]) {
                openInfo(markers[0].data);
            }
            window.clearTimeout(iconClickTimer);
            iconClickTimer = null;
        }, 20);
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

    if (f.properties.names.length > 0) {
        return f.properties.names[0].name;
    } else {
        return "";
    }
}

function getMarkerColour(feature) {
    var col = '#ccc';
    if (feature.properties.names.length > 0) {
        col = feature.properties.names[0].lang.colour;
    }
    return col;
}

// infoLayer is the layer for which info is currently displayed
// infoMarker is the marker which appears at the same point, to make it more easily identifiable
var infoLayer = null, infoMarker = null, infoPopup = null, pendingXhr = null;
function openInfo(layer) {
    if (!layer) {
        console.log('hide info div');
    } else if (!layer.feature || !layer.feature.properties || !layer.feature.properties.id) {
        console.log('openInfo: layer is not valid feature');
        console.log(layer);
    } else {
        console.log('openInfo for feature id ' + layer.feature.properties.id);
    }
    if (infoMarker) {
        if (infoMarker.layer == layer) {
            // skip reload popup for same place
            return;
        }
        infoMarker.remove();
        infoMarker = null;
    }

    if (pendingXhr && infoLayer && infoLayer != layer) {
        // cancel pending info popup for different marker
        pendingXhr.abort('manual');
    }
    if ((infoPopup && layer && layer != infoLayer) || (infoPopup && !layer)) {
        infoPopup.remove();
    }
    infoLayer = layer;

    if (!layer) {
        return;
    }

    infoMarker = L.marker(layer.getLatLng(), {
        interactive: false,
        zIndexOffset: 1000,
    }).addTo(map);
    infoMarker.layer = layer;

    pendingXhr = $.ajax('/info/' + layer.feature.properties.id + "/", {
        success: function (data, status, jqxhr) {
            if (!infoLayer) return;
            var tempDiv = $("#tempdiv");
            var html = tempDiv.append($.parseHTML(data)).children();

            function doPopup() {
                html.detach();
                infoPopup = new MyPopup({
                    closeOnClick: false,
                    className: 'info-popup',
                    autoPanPadding: {x: 30, y: 30},
                    hasTip: false,
                    offset: {x: 30, y: 50},
                }, infoLayer).on("remove", function (e) {
                    openInfo(null); // make sure marker disappears when new layer is loaded
                }).setLatLng(infoLayer.getLatLng()).setContent(html[0]).openOn(map);
            }

            var imgs = $("img.media-external", html);
            if (imgs.length > 0) {
                var numLoaded = 0;
                imgs.on("load", function () {
                    console.log("imgs loaded: " + numLoaded);
                    if (++numLoaded == imgs.length) {
                        // open popup only after images are loaded
                        doPopup();
                    }
                });
            } else {
                // open popup immediately, nothing more to load
                doPopup();
            }

        },
        error: function (jqxhr, textStatus, error) {
            if (textStatus != 'manual')
                console.log("Error retrieving info: " + textStatus);
        }
    });
}

function handleGeoJson(data, status, jqxhr) {
    // process data returned from the geojson web service (expects a FeatureCollection)

    /* process icons and prepare them for use on the map */
    for (var iconName in data.metadata.icons) {
        if (iconName in iconsList)
            continue;
        iconsList[iconName] = L.icon({
            iconUrl: data.metadata.icons[iconName],
            iconSize: [32, 32],
            iconAnchor: [16, 31],
        });
    }

    for (var i = 0; i < data.metadata.langs.length; i++) {
        if (data.metadata.langs[i].id in langCache) {
            continue;
        }
        langCache[data.metadata.langs[i].id] = data.metadata.langs[i];
    }

    // process geoJson data
    geoJsonLayer.addData(data);
    
    console.log("Loaded " + data.features.length + " features: " + newIconMarkers.length + " new, " + Object.keys(placeCache).length + " total");

    // add the icon markers to the map
    iconLayer.addLayers(newIconMarkers);
    console.log(newIconMarkers);
    newIconMarkers = [];
    
    console.log(data.metadata);

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

var InfoControl = L.Control.extend({
    onAdd: function (map) {
        var self = this;
        self._div = L.DomUtil.create('div', 'info-control info-collapsed leaflet-bar');
        self._contentdiv = L.DomUtil.create('div', 'info-content', self._div);

        var icon_container = L.DomUtil.create('a', 'icon-topright', self._div);
        icon_container.href = '#close';
        self._icon = L.DomUtil.create('span', 'icon icon-info', icon_container);

        L.DomEvent.on(self._div, "click", function (e) {
            // toggle collapsed status
            if (L.DomUtil.hasClass(self._div, 'info-collapsed')) {
                L.DomUtil.removeClass(self._div, 'info-collapsed');
            } else {
                L.DomUtil.addClass(self._div, 'info-collapsed');
            }
        }).disableClickPropagation(self._div);
        return self._div;
    },
    onRemove: function (map) {
        // remove listeners here
    }
});

var MyPopup = L.ResponsivePopup.extend({
    _initLayout: function () {
        L.ResponsivePopup.prototype._initLayout.call(this);
        if (this._closeButton) {
            this._closeButton.innerHTML = '';
            L.DomUtil.removeClass(this._closeButton, 'leaflet-popup-close-button');
            L.DomUtil.addClass(this._closeButton, 'icon-topright');
            var closeIcon = L.DomUtil.create('span', 'icon icon-x-circle', this._closeButton);
        }
    },
});