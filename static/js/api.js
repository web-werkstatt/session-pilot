// Zentraler Fetch-Wrapper — alle API-Aufrufe laufen hierueber.
// Eingebunden in base.html VOR base.js und allen Seiten-Scripts.

var api = (function() {
    'use strict';

    /**
     * Kern-Funktion: fetch mit automatischem JSON-Parsing, Status-Check, Error-Handling.
     * @param {string} url
     * @param {object} [opts] - fetch init + extras:
     *   opts.body: bei Objekten automatisch JSON.stringify + Content-Type
     *   opts.raw: true → gibt Response statt JSON zurueck (fuer Downloads etc.)
     * @returns {Promise<any>} parsed JSON oder Response (bei raw)
     */
    async function request(url, opts) {
        opts = opts || {};
        var raw = opts.raw;
        delete opts.raw;

        // Body-Objekte automatisch als JSON serialisieren
        if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData) && !(opts.body instanceof Blob)) {
            opts.body = JSON.stringify(opts.body);
            opts.headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
        }

        var res;
        try {
            res = await fetch(url, opts);
        } catch (err) {
            throw new ApiError(0, null, 'Netzwerkfehler: ' + err.message);
        }

        if (raw) return res;

        // 204 No Content → null
        if (res.status === 204) return null;

        var data = null;
        try {
            data = await res.json();
        } catch (_) {
            if (!res.ok) throw new ApiError(res.status, null, 'HTTP ' + res.status);
            return null;
        }

        if (!res.ok) {
            var msg = (data && (data.error || data.message)) || 'HTTP ' + res.status;
            throw new ApiError(res.status, data, msg);
        }

        return data;
    }

    // Convenience-Methoden
    function get(url)           { return request(url); }
    function post(url, body)    { return request(url, { method: 'POST', body: body }); }
    function put(url, body)     { return request(url, { method: 'PUT', body: body }); }
    function patch(url, body)   { return request(url, { method: 'PATCH', body: body }); }
    function del(url, body)     { return request(url, { method: 'DELETE', body: body }); }

    // Fehlerklasse
    function ApiError(status, body, message) {
        this.name = 'ApiError';
        this.status = status;
        this.body = body;
        this.message = message || 'Request fehlgeschlagen';
    }
    ApiError.prototype = Object.create(Error.prototype);
    ApiError.prototype.constructor = ApiError;

    return {
        request: request,
        get: get,
        post: post,
        put: put,
        patch: patch,
        del: del,
        ApiError: ApiError
    };
})();
