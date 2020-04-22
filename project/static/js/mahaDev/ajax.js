;(function($){
    'use strict';
  
    $.xhr = function() {
      function parse(req) {
        var result;
        try {
          result = $.parseJSON(req.responseText);
        } catch (e) {
          result = req.responseText;
        }
        return [result, req];
      }
  
      function xhr (type, api, contentType, data, pageName) {
        if(type == "GET" && api && api.length > 1700){
          type = "POST";
          var apiSplit = api.split('?');
          api = apiSplit[0];
          data = apiSplit[1];
        }
        var _type = type, _api = api, methods = {
          success: function () {},
          error: function () {
            $.utilities.default.loader(!1);
          },
          always: function () {},
          abort: function() {}
        };
        var ActiveXObject = ActiveXObject || false,
            XHR = XMLHttpRequest || ActiveXObject,
            request = new XHR('MSXML2.XMLHTTP.3.0'),
            timeAtStart = new Date().getTime(),
            availableContentTypes = {
              default: 'application/x-www-form-urlencoded',
              j: 'application/json',
              f: 'multipart/form-data',
              none: undefined
            },
            _contentType = availableContentTypes.default;
        if(contentType){
          _contentType = availableContentTypes[contentType];
        }
        $.connections(!0);
        request.open(_type, _api, true);
        if(_contentType){
          request.setRequestHeader('Content-type', _contentType);
        }
        request.onreadystatechange = function () {
          var req, tnow;
          if (request.readyState === 4) {
            req = parse(request);
            if (request.status >= 200 && request.status < 300) {
              $.connections(!1);
              tnow = $.anConstants.date();
              $.log.event({"name":"loadTime","cat": "perf","ev_val_int": (tnow - timeAtStart)}, {"type": pageName || "page", "id" : $.encodeURIComponent(api.split('?')[0]), "extra" : $.encodeURIComponent(api.split('?')[1] || "") }, {"type": 'page', "id": 'success'});
              methods.success.apply(methods, req);
            } else {
              $.connections(!1);
              tnow = $.anConstants.date();
              $.log.event({"name":"loadTime","cat": "perf","ev_val_int": (tnow - timeAtStart)}, {"type": pageName || "page", "id" : $.encodeURIComponent(api.split('?')[0]), "extra" : $.encodeURIComponent(api.split('?')[1] || "") }, {"type": 'page', "id": 'error'});
              $.anConstants.letUnload = true;
              methods.error.apply(methods, req);
            }
          }
          // if (request.status === 0) {
            // abort
          // }
        };
        request.send(data);
        var anXHR = {
          success: function (callback) {
            if(callback){
              methods.success = callback;
            }
            return anXHR;
          },
          error: function (callback) {
            if(callback){
              methods.error = callback;
            }
            return anXHR;
          },
          always: function (callback) {
            if(callback){
              methods.always = callback;
            }
            return anXHR;
          },
          abort: function() { 
            request.abort();
          }
        };
        return anXHR;
      }
  
      function get (api, data, contentType, pageName) {
        return xhr('GET', api, contentType, data, pageName);
      }
  
      function post (api, data, contentType, pageName) {
        return xhr('POST', api, contentType, data, pageName);
      }
  
      $.anConstants.xhrList = $.anConstants.xhrList || [];
  
      return {
        get: get, 
        post: post, 
        GET: get, 
        POST: post
      };
    };
  })(window.mahaDev);
  