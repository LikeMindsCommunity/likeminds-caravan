;(function($){
    'use strict';
    
    $.view = {
      intent: function(url){
        var joinBy = "&", baseURL = window.location.pathname + window.location.search, redirectURL = window.location.host + url.replace('ajax=true', '');
        if(redirectURL.indexOf('?') === -1){
          joinBy = "?";
        };
        redirectURL = redirectURL + joinBy + 'fb_redirect=true&fb_ruid=' + $.readCookie('_ruid') + '&fb_uuid=' + $.readCookie('uuid') + "&fb_visit_id="  + window.visit_id + "&magicURL=" + $.encodeURIComponent(baseURL);
        window.location.href = "intent://" + redirectURL + "#Intent;scheme=https;action=android.intent.action.VIEW;end;";
        $.anConstants.gestureRedirectFB = !1;
      },
      getVenderScripts: function(scriptsArray){
        var vendorScripts = scriptsArray || [],
            _getVenderScripts = function(){
              window.requestAnimationFrame(function(){
                for(var i = 0; i < vendorScripts.length; i++){
                  if($('.an-'+ vendorScripts[i] + '-js').length > 0){
                    try{
                      $.view.blobScripts($('.an-'+ vendorScripts[i] + '-js').html());
                    }catch(e){
                      // console.log(e);
                      // console.log($('.an-'+ vendorScripts[i] + '-js').html());
                    }
                  }
                }
              });
            };
        // if ('requestIdleCallback' in window) {
        //   window.requestIdleCallback(function(){
        //     getVenderScripts();
        //   });
        // }else{
          _getVenderScripts();
        // }
      },
      fillView: function(data, event) {
        window.requestAnimationFrame(function(){
          if(data && data.view) {
            $('body').html(data.view);
            if($('#authCon')[0].style.display == 'block'){
              $.anConstants.pseudoBack += 1;
              $('#authCon').hide();
            }
            var viewOverlay = false;
            if($('.viewOverlay').length > 0){
              $('.viewOverlay').each(function(){
                if(this.style.display == 'block'){
                  viewOverlay = true;
                  this.style.display = 'none';
                }
              });
            }
            if(viewOverlay){
              $.anConstants.pseudoBack += 1;
            }
            $.utilities.default.scrollDOM(data.scroll);
            $('#an-info').hide();
            $('.an-lma').each(function(){
              $(this).attr('an-ok', 'true');
            });
            $('.an-js').each(function(){
              $(this).attr('data-done', ' ');
            });
            $('.an-load-js').each(function(){
              $(this).attr('data-done', ' ');
            });
            if(window.speechSynthesis){
              window.speechSynthesis.cancel();
            }
            $.view.replaceView();
            window.requestAnimationFrame(function(){
              $.view.evalScripts();
              $.utilities.lazyLoad.init({image: true, pagination: true, video: true});
            });
          }else{
            window.location = window.location;
          }
        });
      },
      pseudoBack: function(){
        $.anConstants.pseudoBack += 1;
      },
      back: function(){
        if(window.history && window.history.back) {
          window.history.back();
        }
        $.utilities.default.loader(!1);
      },
      forward: function(){
        if(window.history && window.history.forward){
          window.history.forward();
        }
        $.utilities.default.loader(!1);
      },
      pushView: function(href, loader) {
        window.requestAnimationFrame(function(){
          var urlV = href || document.location.href;
          if(loader){
            $.utilities.default.loader(!1, loader);
          }else{
            $.utilities.default.loader(!1);
          }
          $('#an-info').hide();
          if(window.history && window.history.pushState){
            var viewHTML = $('body').html(),
                // viewTheme = $('.theCo').attr('content'),
                // viewTitle = document.title,
                staobj = {view: viewHTML, scroll: 1/*, title: viewTitle, theme: viewTheme*/};// rank: viewRank};
            try{
              window.history.pushState(staobj, !1, urlV);
            }catch(e){
              staobj.view = null;
              window.history.pushState(staobj, !1, urlV);
            }
          }
        });
      },
      replaceView: function(href, loader) {
        window.requestAnimationFrame(function(){
          var scrollState,
              urlV = href || document.location.href;
          if($.anConstants.touch == 'true'){
            scrollState = (document.body.scrollTop || document.documentElement.scrollTop) || 1;
          }else{
            if($('.AN-scrlEle')[0]){
              scrollState = $('.AN-scrlEle')[0].scrollTop || 1;
            }else{
              scrollState = $('.conn')[0].scrollTop || 1;
            }
          }
          if(loader){
            $.utilities.default.loader(!1, loader);
          }else{
            $.utilities.default.loader(!1);
          }
          if(window.history && window.history.replaceState) {
            var viewHTML = $('body').html(),
                // viewTheme = $('.theCo').attr('content'),
                // viewTitle = document.title,
                staobj = {view: viewHTML, scroll: scrollState/*, title: viewTitle, theme: viewTheme*/};// rank: viewRank};
            try{
              window.history.replaceState(staobj, !1, urlV);
            }catch(e){
              staobj.view = null;
              window.history.replaceState(staobj, !1, urlV);
            }
          }
        });
      },
      blobScripts: function(scripts, callback){
        // var blob = new Blob([scripts], {type: 'text/javascript'});
        // var urlCreator = window.URL || window.webkitURL;
        // var url = urlCreator.createObjectURL( blob );
        // function loadScript(url, callback){
        //   var head = document.getElementsByTagName('head')[0];
        //   var script = document.createElement('script');
        //   script.async = true;
        //   script.type = 'text/javascript';
        //   script.src = url;
        //   // if(callback){
        //   // script.onreadystatechange = callback;
        //   // script.onload = callback;
        //   // }
        //   head.appendChild(script);
        // }
        // loadScript(url, callback);
        // window.requestAnimationFrame(function(){
          eval(scripts);
        // });
      },
      evalScripts: function(){
        var scripts = "";
        $('.an-js-rm').each(function(){
          scripts += $(this).html();
        }).remove();
        $('.an-js').each(function(){
          if(!$(this).attr('data-done')){
            $(this).attr('data-done', 'true');
            scripts += $(this).html();
          }
        });
        $('.an-load-js').each(function(){
          if(!$(this).attr('data-done')){
            $(this).attr('data-done', 'true');
            scripts += $(this).html();
          }
        });
        $.view.blobScripts(scripts);
      },
      setMagicView: function(){
        var magic = true, 
          pathname = document.location.pathname, 
          whiteList = "".split(" ");
        for(var i = 0; i < whiteList.length; i++){
          if(pathname.indexOf(whiteList[i]) > -1){
            magic = false;
            break;
          }
        }
        if(magic && !$.anConstants.app){
          var landingURL = document.location.href, pseudoURL = landingURL;
          if($('#noBackView').length == 0){
            if(landingURL.indexOf('?') > -1){
              pseudoURL = landingURL + "&magic=true"
            }else{
              pseudoURL = landingURL + "?magic=true"
            }
          }
          $.view.replaceView(pseudoURL);
          $.view.pushView(landingURL);
        }
      },
      /*pageCached: function(data, dataObj){
        $.cached = $.cached || {};
        $.cached[id] = data;
        $('#'+dataObj.extra.id).removeClass("an-precache").attr('data-obj', '{"href":"'+dataObj.extra.attr.href+'","click":"cached","vi":1,"data":"'+dataObj.extra.id+'"}');
      },*/
      /*cache: function(){
        for(var i = 0, l = $.anConstants.cacheImageList.length; i < l; i++){
          $.worker.list.push({
            type: "image",
            url: $.anConstants.cacheImageList[i],
            protocol: $.anConstants.protocol
          })
        }
        //$.view.cacheDynamic();
      },*/
      /*cacheDynamic: function(){
        $('.an-precache').each(function(){
          var attributes = $.utilities.default.anAttr($(this)), id = this.id;
          $.worker.list.push({
            type: "html",
            init: "pageCached",
            extra: {
              attr: attributes,
              id: id
            },
            url: attributes.api,
            protocol: $.anConstants.protocol
          });
        });
      },*/
      setDialogue: function(){
        try {
          var SpeechRecognition = window.SpeechRecognition || (window.webkitSpeechRecognition || window.mozSpeechRecognition || window.msSpeechRecognition || window.oSpeechRecognition);
          var recognition = new SpeechRecognition();
          $.getPermissionStatus('microphone', function(){
            if (this.state != 'denied') {
              $.getScript($.anConstants.scripts.voice, true);
            }else if ('speechSynthesis' in window) {
              $.getScript($.anConstants.scripts.voice);
            }
          });
        }catch(e) {
          if ('speechSynthesis' in window) {
            $.getScript($.anConstants.scripts.voice);
          }
        }
      },
      setBasic: function(){
        $.cookie('deviceWidth', $.anConstants.deviceWidth);
        $.cookie('deviceHeight', $.anConstants.deviceHeight);
        if($.anConstants.app || $.UA.isIOS() || $.UA.isSafari() || $.UA.isUCBrowser() || $.UA.isFBinApp() || $.UA.isSamsungBrowser()){
          $.anConstants.autoplayVDO = false;
        }else{
          $.anConstants.autoplayVDO = true;
        }
        if($.UA.isPhonepeAndroid()){
          $.cookie('ppewv', 'a');
        }
        if($.UA.isPhonepeIos()){
          $.cookie('ppewv', 'i');
        }
      },
      setFBview: function(){
        if($.UA.isFBinApp()){
          $('#sty').html($('#sty').html() + $('#FBstyle').html());
          $('.theCo').each(function(){
            $(this).attr("content", "#3B5998");
          });
        }
      },
      // userInteracted: function(type){
      //   if($.anConstants.userInteracted) return;
      //   // $.view.cache();
      //   $.anConstants.userInteracted = true;
      //   $.utilities.lazyLoad.init({image: true, pagination: true, video: true, ads: true});
      // },
      init: function(){
        $.network();
        $.utilities.lazyLoad.init({image: "strict"});
        for(var i = 0, l = $.anConstants.defferedTrackList.length; i < l; i++){
          $.log.event($.anConstants.defferedTrackList[i][0], $.anConstants.defferedTrackList[i][1], $.anConstants.defferedTrackList[i][2]);
        }
        function _init(){
          $.utilities.lazyLoad.init({video: true, ads: true});
          $.view.getVenderScripts(['gtm', 'heatmaps']);
          $.view.setDialogue();
          // for(var i = 0, l = $.anConstants.cacheImageList.length; i < l; i++){
          //   $.worker.image.list.push($.anConstants.cacheImageList[i]);
          // }
        }
        window.requestAnimationFrame(function(){
          if ('serviceWorker' in navigator) {
            $.getScript($.anConstants.scripts.sw, true);
          }
          if ($.anConstants.getDUID && !$.readCookie('duid')){
            $.getScript($.anConstants.scripts.fingerPrint, true);
          }
          $.view.evalScripts();
          $.utilities.lazyLoad.init({pagination: "strict"});
          if ('requestIdleCallback' in window) {
            window.requestIdleCallback(function(){
              _init();
            })
          }else{
            window.requestAnimationFrame(function(){
              _init();
            })
          }
        });
      }
    }
  })(window.mahaDev);
  
  
  
  
  