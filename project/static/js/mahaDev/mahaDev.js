var mahaDev = (function() {
    'use strict';
  
    var MD = {}, $$;
  
    function md(elements, selector) {
      /*jshint validthis: true */
      var i = 0, length = (elements && elements[0]) ? elements.length : 0;
      for (; i < length; i++) this[i] = elements[i];
      this.length = length;
      this.selector = selector ? $$.trim(selector) : '';
    }
  
    MD.md = function(elements, selector) {
      return new md(elements, selector);
    };
  
    MD.isMD = function(object) {
      return object instanceof MD.md;
    };
  
    MD.selector = function(selector, context){
      if(!selector) return [];
      var elements = [],
          parent = context || document,
          _selector = $$.trim(selector);
      if(_selector.split(' ').length > 1 || _selector.indexOf(',') > -1){
        elements = parent.querySelectorAll(_selector);
      }else{
        if(_selector[0] == '#'){
          elements = [document.getElementById(_selector.substr(1))];
        }else if(_selector[0] == '.'){
          elements = parent.getElementsByClassName(_selector.substr(1));
        }else if(_selector.indexOf('[') > -1){
          elements = parent.querySelectorAll(_selector);
        }else{
          elements = parent.getElementsByTagName(_selector);
        }
      }
      return elements;
    };
  
    MD.init = function(selector, parent) {
      if(!selector) return MD.md();
      if(MD.isMD(selector)){
        return selector;
      }
      var elements = [];
      if(typeof selector == 'string'){
        elements = MD.selector(selector, parent);
      }else{
        if(selector instanceof Array){
          elements = selector;
        }else{
          elements = [selector];
        }
      }
      return MD.md(elements, selector);
    };
  
    $$ = function(selector, context){
      return MD.init(selector, context);
    };
  
    $$.regexp = function(name, type) {
      var regexp = "";
      switch(type){
        case "className":
          regexp = "(\\s|^)" + name + "(\\s|$)";
          break;
        case "url":
          regexp = "/(?:\\b|_)(?:" + name + ")(?:\\b|_)/i"
          break;
      }
      return new RegExp(regexp);
    };
  
    $$.trim = function(string){
      return (string && string.trim ? string.trim() : '');
    };
  
    $$.createElement = function(tagName){
      return $$(document.createElement(tagName));
    };
  
    $$.parseJSON = JSON.parse;
    $$.stringifyJSON = JSON.stringify;
    $$.decodeURI = window.decodeURI;
    $$.decodeURIComponent = window.decodeURIComponent;
    $$.encodeURI = window.encodeURI;
    $$.encodeURIComponent = window.encodeURIComponent;
    $$.parseInt = window.parseInt;
    $$.parseFloat = window.parseFloat;
    $$.extend = Object.assign || function (target) { // extend object
      for (var i = 1; i < arguments.length; i++) { 
        var source = arguments[i]; 
        for (var key in source) { 
          if (Object.prototype.hasOwnProperty.call(source, key)) { 
            target[key] = source[key]; 
          } 
        } 
      } 
      return target; 
    };
    
  
    $$.fn = {
      constructor: MD.md,
      length: 0,
      // l: function(){
      //   return this.length;
      // },
      remove: function(){
        return this.each(function(){
          if (this.parentNode !== null) this.parentNode.removeChild(this);
        });
      },
      each: function(callback, maxElements){
        var i = 0, elements = this, length = maxElements ? Math.min(maxElements, elements.length) : elements.length;
        for(; i < length; i++){
          callback.call(elements[i]);
        }
        return elements;
      },
      show: function(value){
        return this.each(function(){
          this.style.display = (value ? value : 'block' );
        });
      },
      hide: function(){
        return this.each(function(){
          this.style.display = "none";
        });
      },
      hasClass: function(className) {
        return $$.regexp(className, "className").test(this[0].className);
      },
      addClass: function(className) {
        return this.each(function(){
          if(!$$.regexp(className, "className").test(this.className)){
            this.className = $$.trim(this.className + " " + className);
          }
        });
      },
      removeClass: function(className) {
        return this.each(function(){
          if($$.regexp(className, "className").test(this.className)){
            this.className = $$.trim(this.className.replace(className, ""));
          }
        });
      },
      attr: function(attributeName, attributeValue){
        if(attributeName){
          if(attributeValue){
            if(attributeValue == ' '){
              this[0].removeAttribute(attributeName);
            }else{
              this[0].setAttribute(attributeName, attributeValue);
            }
          }else{
            return this[0].getAttribute(attributeName);
          }
        }
        return this;
      },
      ie: function(htmlString, beforebegin) {
        if(htmlString){
          this[0].insertAdjacentHTML((beforebegin ? 'beforebegin' : 'beforeend'), htmlString);
        }
        return this;
      },
      ia: function(element, htmlString) {
        element.insertAdjacentHTML('beforeend', htmlString);
      },
      ae: function (element, prepend) {
        if(element){
          if(prepend){
            this[0].insertBefore(element, this[0].firstChild);
          }else{
            this[0].appendChild(element);
          }
          return $$(element);
        }
        return this;
      },
      next: function() {
        var element = this[0];
        do { element = element.nextElementSibling || false; }
        while (element && element.nodeType !== 1);
        return $$(element);
      },
      nextAll: function(element){
        var nextElements = [];
        var nextElement = this[0];
  
        while (nextElement.nextElementSibling) {
          nextElements.push(nextElement.nextElementSibling);
          nextElement = nextElement.nextElementSibling;
        }
        return $$(nextElements);
      },
      // prev: function() {
      //   var element = this[0];
      //   do { element = element.previousElementSibling || []; }
      //   while (element.nodeType !== 1);
      //   return $$(element);
      // },
      html: function(string) {
        if (!this[0]) {
          return "";
        }
        if (string) { 
          this[0].innerHTML = string;
          return this;
        }else { 
          return this[0].innerHTML;
        }
      },
      children: function(){
        return $$(this[0].children);
      },
      parent: function(){
        return $$(this[0].parentElement);
      },
      parents: function(selectorClass, notSame){
        var elem = this, notsame = notSame || false;
        while (elem[0]) {
          if (!notsame && elem.hasClass(selectorClass)) {return elem;}
          else {notsame = false; elem = elem.parent();}
        }
        return null;
      },
      inView: function() {
        var element = this[0],
            elementRect = element.getBoundingClientRect(),
            eHeight = elementRect.height,
            eWidth = elementRect.width,
            dHeight = $$.mdConstants.deviceHeight,
            dWidth = $$.mdConstants.deviceWidth;
            
        return {
          complete: (
                      elementRect.top >= (0 - 48) &&
                      elementRect.left >= (0 - 48) &&
                      elementRect.bottom <= (eHeight + dHeight) &&
                      elementRect.right <= (eWidth + dWidth)
                    ), 
          partial:  (
                      elementRect.top >= (0 - eHeight - dHeight) &&
                      elementRect.left >= (0 - eWidth - dWidth) &&
                      elementRect.bottom <= (eHeight + 2*dHeight) &&
                      elementRect.right <= (eWidth + 2*dWidth)
                    )
        };
      }
    };
    MD.md.prototype = md.prototype = $$.fn;
    return $$;
  })();
  
  window.mahaDev = mahaDev;
  window.$$ = mahaDev;
  window.$$.mdConstants = window.mdConstants || {};
  
  
  
  