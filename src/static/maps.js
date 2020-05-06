var GMAP;

// callback when the map is loaded
function initMap() {
    GMAP = new google.maps.Map(document.getElementById('gmap'), {
        center: {lat: -22.68, lng: 118.35},
        zoom: 7
    });
    GMAP.data.loadGeoJson("/data/");
}

function jsonp_callback(data) {

}
