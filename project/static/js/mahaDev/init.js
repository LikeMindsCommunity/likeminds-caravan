;(function($){
	'use strict';
  
  function addListners(){
    window.addEventListener('DOMContentLoaded', function(){
      interactiveCalls();
    });
    window.addEventListener('load', function() {
      completeLoadCalls();
    });
  }
  function interactiveCalls(addLoadEvent){
    $.svg();
    // if($.anConstants.magicPage){
      $.view.setMagicView();
    // }
    $.view.setBasic();
    // $.view.setFBview();
    if(addLoadEvent){
      window.addEventListener('load', function() {
        completeLoadCalls();
      });
    }
    if(window.matchMedia('(display-mode: standalone)').matches || (window.navigator && window.navigator.standalone === true)) {
      $.anConstants.pwa = true;
      $.anConstants.defferedTrackList.push([{"name":"PWAlaunched"},{"type":"", "id":"", "extra":""},{"type":"", "id":"", "extra":""}]);
    }
    if(window.performance){
      var timing = window.performance.timing;
      if (timing && timing.domContentLoadedEventEnd && timing.navigationStart){
        var userTime = timing.domContentLoadedEventEnd - timing.navigationStart;
        $.anConstants.defferedTrackList.push([{"name":"loadHTML", "cat": "perf", "ev_val_int": userTime},{"id":$.encodeURIComponent(location.href.split('?')[0]), "extra":$.encodeURIComponent(location.href.split('?')[1] || "")},{"type":"", "id":"", "extra":""}]);
      }
    }
  }
  function completeLoadCalls(){
    $.view.init();
    // if ('requestIdleCallback' in window) {
    //   window.requestIdleCallback(function(){
    //     $.view.init();
    //   });
    // }else{
    //   $.view.init();
    // }
  }
	if (document.readyState == 'loading'){
    addListners();
	} else {
    if(document.readyState == 'complete'){
      interactiveCalls();
      completeLoadCalls();
    }else{
      interactiveCalls(true);
    }
  }
})(window.mahaDev);

