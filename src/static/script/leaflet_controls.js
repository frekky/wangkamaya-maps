// TODO: refactor LoadingControl, InfoControl, MyPopup to use jQuery
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
        emptyText: 'Loading...',
    },
    onAdd: function (map) {
        var self = this;
        self._div = L.DomUtil.create('div', 'info-control info-collapsed');
        self._contentdiv = L.DomUtil.create('div', 'info-content', self._div);

        self._iconContainer = L.DomUtil.create('a', 'icon-topright', self._div);
        self._iconContainer.href = '#';
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
            self._contentdiv.innerHTML = self.options.emptyText;

            $.ajax(self.options.loadUrl, {
                success: function (data) {
                    self._contentdiv.innerHTML = data;
                },
                error: function () {
                    self._contentdiv.innerHTML = "<code>Error loading content :-(</code>";
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
        this.filters = {};
        return InfoControl.prototype.onAdd.call(this, map);
    },
    addSection: function (sectionId, title) {
        var container = $('<div class="filter-section">').appendTo(this._contentdiv);
        var title = $('<span class="filter-title">')
            .text(title)
            .appendTo(container);

        var rowContainer = $('<div class="filter-rows">')
            .html(this.options.emptyText)
            .appendTo(container);

        this.filters[sectionId] = {
            title: title,
            container: container,
            rowContainer: rowContainer,
            rows: {},
        };
        return this;
    },
    /* onToggle is callback with argument of checkbox status (true/false) */
    addRow: function (sectionId, rowId, text, colour, onToggle, context) {
        if (!(sectionId in this.filters)) {
            console.log("bad filter section id=" + sectionId);
            return;
        }
        var section = this.filters[sectionId];
        if (rowId in section.rows) {
            console.log("already added rowId=" + rowId);
            this.removeRow(sectionId, rowId); // remove row first before re-adding
        } else if (Object.keys(section.rows).length == 0) {
            // remove emptyText
            section.rowContainer.html('');
        }
        var container = $('<div class="filter-row">')
            .appendTo(section.rowContainer);

        var checkbox = $('<input type="checkbox">')
            .prop('checked', true)
            .appendTo(container);
        var label = $('<span class="filter-text">')
            .appendTo(container)
            .text(text);

        if (colour) {
            var circle = $('<span class="map-colour">')
                .appendTo(container)
                .css('background-color', colour);
        }

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

        section.rows[rowId] = rowData;
        return this;
    },
    removeRow: function (sectionId, rowId) {
        if (!(sectionId in this.filters) || !(rowId in this.filters[sectionId])) {
            console.log("bad rowId=" + rowId)
            return this; // don't do anything if row doesn't exist
        }
        var s = this.filters[sectionId];
        s.rows[rowId].container.off().remove();
        delete s.rows[rowId];
        if (Object.keys(s.rows).length == 0) {
            s.rowContainer.html(this.options.emptyText);
        }
        return this;
    },
    clearRows: function () {
        for (var sid in this.filters) {
            var s = this.filters[sid];
            for (var id in s.rows) {
                this.removeRow(sid, id);
            }    
        }
    },
    getRowStatus: function (sectionId) {
        var section = this.filters[sectionId];
        var s = {};
        for (var id in section.rows) {
            s[id] = section.rows[id].status;
        }
        return s;
    },
    onRemove: function (map) {
        this.clearRows();
        InfoControl.prototype.onRemove.call(this, map);
    },
});