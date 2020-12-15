var map = null, loaderControl = null, filterControl = null;
var isLoaded = false;
var iconClickTimer = null;

// alias for leaflet.canvas-markers.js
window.rbush = RBush;

/* cache all the places we know about, only request the ones we don't already have
 * placeCache is populated with markers for each place, keyed by feature.properties.id */
var placeCache = {}, iconsList = {}, langCache = {};

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
            feature: feature,
            visible: true,
        };
    },
});

function setFeatureVisibility(db_id, visible) {
    if (!db_id || !(db_id in placeCache)) return;

    var p = placeCache[db_id];
    if (p.visble == visible) return;
    
    if (visible) {
        // make marker visible: add to map
        geoJsonLayer.addLayer(p.circleMarker);
        iconLayer.addMarker(p.iconMarker);
        p.visible = true;
    } else {
        if (infoMarker && infoMarker.layer == p.iconMarker) {
            openInfo(null); // close popup if it is over this marker
        }
        geoJsonLayer.removeLayer(p.circleMarker);
        iconLayer.removeMarker(p.iconMarker);
        p.visible = false;
    }
}

function forceRedraw() {
    iconLayer.redraw();
    //labelRenderer._reset();
    map.fire('viewreset');
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
        if (data.metadata.langs[i].id in langCache)
            continue;
        var lang = data.metadata.langs[i];
        langCache[lang.id] = lang;
        filterControl.addRow(lang.name, lang.colour, function (status) {
            console.log('toggle lang id=' + this.id + ' name=' + this.name + ' state=' + status);
            for (var id in placeCache) {
                var props = placeCache[id].feature.properties;
                // TODO: handle multiple langs properly
                /*var show = props.names.length;
                for (var n = 0; n < props.names.length; n++) {
                    if (props.names[n].lang.id == this.id)
                        show--;
                }*/
                //setFeatureVisibility(id, show > 0);

                for (var n = 0; n < props.names.length; n++) {
                    if (props.names[n].lang.id == this.id) {
                        setFeatureVisibility(id, status);
                        break;
                    }
                }
            }
            forceRedraw();
        }, lang);
    }

    if (data.features.length == 0) {
        console.log("No features returned from server");
        loaderControl.setState('okay');
        return;
    }

    // process geoJson data
    geoJsonLayer.addData(data);
    
    var text = "Loaded " + data.features.length + " features: " + newIconMarkers.length + " new, " + Object.keys(placeCache).length + " total";
    console.log(text);
    loaderControl.setState('okay', text);

    // add the icon markers to the map, use array for optimal performance
    iconLayer.addLayers(newIconMarkers);
    console.log(newIconMarkers);
    newIconMarkers = [];
    
    console.log(data.metadata);
}

function cleanReloadViewport() {
    iconLayer.clearLayers();
    geoJsonLayer.clearLayers();
    openInfo(null);
    placeCache = {};
    newIconMarkers = [];
    filterControl.clearRows();
    langCache = {};
    iconsList = {};
    forceRedraw();

    reloadViewport();
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');

function reloadViewport() {
    var bbox = map.getBounds();
    var url = "/data/";
    loaderControl.setState('loading');

    var data = {
        // tell server not to send us IDs of 
        alreadyLoaded: Object.keys(placeCache),
        bounds: {
            ne: bbox.getNorthEast(),
            sw: bbox.getSouthWest(),
        },
    };
    $.ajax(url, {
        cache: false,
        method: 'POST',
        headers: {'X-CSRFToken': csrftoken},
        data: JSON.stringify(data),
        dataType: "json",
        success: handleGeoJson,
        error: function (jqxhr, textStatus, error) {
            console.log(jqxhr);
            loaderControl.setState('error', textStatus);
        }
    });
}

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

var LoadingControl = L.Control.extend({
    options: {
        loadingIconClass: 'icon-loading-anim',
        okayIconClass: 'icon-check2',
        errorIconClass: 'icon-exclamation-triangle',
        onClick: null,
    },
    onAdd: function (map) {
        this._div = L.DomUtil.create('div', 'loading-control leaflet-bar');
        this._iconContainer = L.DomUtil.create('div', 'icon-topright', this._div);
        this._icon = L.DomUtil.create('span', 'icon ' + this.options.okayIconClass, this._iconContainer);
        if (this.options.onClick) {
            L.DomEvent.on(this._div, 'click', this.options.onClick);
        }
        L.DomEvent.disableClickPropagation(this._div);
        return this._div;
    },
    setState: function (state, titleText) {
        var newClass = '' + state + 'IconClass';
        if (!(newClass in this.options))
            return;
        L.DomUtil.removeClass(this._icon, this.options.loadingIconClass);
        L.DomUtil.removeClass(this._icon, this.options.okayIconClass);
        L.DomUtil.removeClass(this._icon, this.options.errorIconClass);
        L.DomUtil.addClass(this._icon, this.options[newClass]);
        if (titleText) {
            this._div.title = titleText;
        } else {
            this._div.title = '';
        }
        return this;
    }
});

var InfoControl = L.Control.extend({
    options: {
        btnIconClass: 'icon-info',
        closeIconClass: 'icon-x-circle',
        loadUrl: null,
    },
    onAdd: function (map) {
        var self = this;
        self._div = L.DomUtil.create('div', 'info-control info-collapsed leaflet-bar');
        self._contentdiv = L.DomUtil.create('div', 'info-content', self._div);

        self._iconContainer = L.DomUtil.create('a', 'icon-topright', self._div);
        self._iconContainer.href = '#close';
        self._icon = L.DomUtil.create('span', 'icon ' + self.options.btnIconClass, self._iconContainer);

        L.DomEvent.on(self._iconContainer, "click", function (e) {
            // toggle collapsed status
            if (L.DomUtil.hasClass(self._div, 'info-collapsed')) {
                L.DomUtil.removeClass(self._div, 'info-collapsed');
                L.DomUtil.removeClass(self._icon, self.options.btnIconClass);
                L.DomUtil.addClass(self._icon, self.options.closeIconClass);
            } else {
                L.DomUtil.addClass(self._div, 'info-collapsed');
                L.DomUtil.removeClass(self._icon, self.options.closeIconClass);
                L.DomUtil.addClass(self._icon, self.options.btnIconClass);
            }
        }).disableClickPropagation(self._div);

        if (self.options.loadUrl) {
            $.ajax(self.options.loadUrl, {
                success: function (data) {
                    self._contentdiv.innerHTML = data;
                }
            });
        }
        return self._div;
    },
    onRemove: function (map) {
        // remove listeners here
    },
});

var MyPopup = L.ResponsivePopup.extend({
    _initLayout: function () {
        L.ResponsivePopup.prototype._initLayout.call(this);
        if (this._closeButton) {
            this._closeButton.innerHTML = '';
            L.DomUtil.removeClass(this._closeButton, 'leaflet-popup-close-button');
            L.DomUtil.addClass(this._closeButton, 'icon-topright');
            L.DomUtil.create('span', 'icon icon-x-circle', this._closeButton);
        }
    },
});

var FilterControl = InfoControl.extend({
    onAdd: function (map) {
        InfoControl.prototype.onAdd.call(this, map);
        this.rows = [];
        return this._div;
    },
    /* onToggle is callback with argument of checkbox status (true/false) */
    addRow: function (text, colour, onToggle, context) {
        var container = $('<div class="filter-row">').appendTo(this._contentdiv);

        var checkbox = $('<input type="checkbox">').prop('checked', true).appendTo(container);
        var label = $('<span class="filter-text">').appendTo(container).text(text);
        var circle = $('<span class="map-colour">').appendTo(container).css('background-color', colour);

        var rowData = {
            rowDiv: container,
            checkbox: checkbox,
            onToggle: onToggle,
            status: true,
            context: context,
        };

        container.on("click", function (e) {
            checkbox.prop('checked', (rowData.status = !rowData.status));
            console.log(rowData);
            onToggle.call(rowData.context, rowData.status);
            //e.preventDefault();
        });

        this.rows.push(rowData);
        return this;
    },
    clearRows: function () {
        this._contentdiv.innerHTML = "";
        this.rows = [];
    },
    onRemove: function (map) {
        InfoControl.prototype.onRemove.call(this, map);
    },
});

$(function () {  
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

    loaderControl = new LoadingControl({
        position: 'topright',
        onClick: cleanReloadViewport,
    }).addTo(map).setState('loading');
    
    filterControl = new FilterControl({
        position: 'topright',
        btnIconClass: 'icon-filter',
    }).addTo(map);

    var aboutControl = new InfoControl({
        position: 'topright',
        btnIconClass: 'icon-question',
        loadUrl: '/about/',
    }).addTo(map);

    reloadViewport();
    
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
});
