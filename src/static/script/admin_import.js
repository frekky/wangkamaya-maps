function displayColMap(mapping_name) {
    var table = $("#colmap").html("");
    var row1 = $('<tr><th>Spreadsheet:</th></tr>'), row2 = $("<tr><th>Database:</th></tr>");
    table.append(row1, row2);
    var colmap = inv_colmaps[mapping_name], mcols = misc_cols[mapping_name];

    if (!colmap) return;

    for (var col in colmap) {
        var th = $("<td>").append($('<span class="colmap-src">').text(col)), td = $("<td>");
        for (var i = 0; i < colmap[col].length; i++) {
            td.append($('<span class="colmap-path">').text(colmap[col][i]));
            if (i != colmap[col].length - 1) td.append($('<span>').text(' --> '));
        }
        row1.append(th);
        row2.append(td);
    }

    table = $("#colmap-misc").html("");
    var row1 = $("<tr>").append($('<th>').text('Database:')), row2 = $('<tr>').append($('<th>').text('From:'));
    table.append(row1, row2);
    for (var path in mcols) {
        row1.append($('<td>').text(path));
        row2.append($('<td>').html(mcols[path]));
    }
    if (!mcols) {
        table.hide();
    } else {
        table.show();
    }
}

$(function () {
    var colmap_sel = $("#id_map_base");
    colmap_sel.on("change", function (e) {
        console.log(colmap_sel.val());
        displayColMap(colmap_sel.val());
    });
    displayColMap(colmap_sel.val());
});