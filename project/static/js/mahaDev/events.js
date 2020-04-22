;(function($){  
    'use strict';
  
    $.event = function(element, eventName, eventHandler) {
      if (element.addEventListener) {
        element.addEventListener(eventName, eventHandler);
      } else if (element.attachEvent) {
        element.attachEvent('on' + eventName, function(){
          eventHandler.call(element);
        });
      }
    };
  
    $.event.variables = {};
  
    $.event.eventObjects = {};
  
    $.event.stop = function(event){
      var event = event || window.event;
      event.stopPropagation();
      event.stopImmediatePropagation();
      event.preventDefault();
      return false;
    };
  
    function _globalEvents(eventName){
      if(!eventName){
        return !1;
      }
      
      $[eventName] = function(target, event){
        // window.PerformanceObserver && performance.measure('event - '+eventName);
        var _event = event, targetElement = $(target),
          attributes = $.utilities.default.anAttr(targetElement);
        if(targetElement.hasClass('anSelect') || (attributes.evi && $.anConstants.eview)){
          return !1;
        }
        if(!attributes.go && _event) $.event.stop(_event);
        if(attributes.imp) $.stop();
        if(targetElement.hasClass('ANretry')){
          attributes.vi = attributes.evi = 0;
        }
        if(attributes.vi || attributes.evi) {
          // if(attributes.vi){
          //   $.anConstants.cleanView = true;
          // }
          if(attributes.evi){
            $.anConstants.eview = true;
          }
          $.view.replaceView();
          // var scrollElement = ($.anConstants.touch == "true") ? $('body') : $('.conn');
          // scrollElement.attr('data-scrolled') && scrollElement.attr('data-scrolled', ' ');
        }
        if(attributes.iscrl){
          $.view.internalScroll = $(attributes.iscrl)[0].scrollTop;
        }
        if(attributes.tr){
          var trP = targetElement.attr("data-tr"),tr;
          if(trP){
            tr = $.parseJSON(trP);
          }
          if(tr && typeof(tr) == "object"){
            $.log.event({"name":tr.name, "dest": tr.dest},{"type":tr.dotype, "id":tr.doid,"extra":tr.doextra},{"type":tr.dftype,"id":tr.dfid,"extra":tr.dfextra});
          }
        }
        if($.event.variables[eventName]){
          window.cancelAnimationFrame($.event.variables[eventName]);
        }
        $.event.variables[eventName] = window.requestAnimationFrame(function(){
          var clickEventHandler = attributes[eventName] ? attributes[eventName].split(',')[0] : !1, utilityModule = attributes[eventName] ? (attributes[eventName].split(',')[1] || 'default') : !1;
          if(clickEventHandler && utilityModule) {
            if($.utilities[utilityModule] && $.utilities[utilityModule][clickEventHandler]){
              $.utilities[utilityModule][clickEventHandler].call(targetElement, event, attributes);
            }
          }
        });
        // !$.anConstants.userInteracted && $.view.userInteracted(eventName);
      };
    }
  
    for(
        var i = 0, 
          eventNames = "click input touchend mouseup load change blur keyup submit focus".split(" ");
          i < eventNames.length; 
          i++
      )
    {
      _globalEvents(eventNames[i]);
    }
    
    $.scroll = function(target, event){
      if($.event.variables.scroll){
        clearTimeout($.event.variables.scroll);
      }
      $.event.variables.scroll = setTimeout(function(){
        if($.event.variables.scrollFrame){
          window.cancelAnimationFrame($.event.variables.scroll);
        }
        $.event.variables.scrollFrame = window.requestAnimationFrame(function(){
          var targetElement = $(target), scrollElement = ($.anConstants.touch == "true") ? $('body') : $('.conn');
          if(targetElement[0] !== window){
            scrollElement = targetElement;
          }
          $.anConstants.scrollPosition = $.anConstants.scrollValue || 400;
          var scrollPosition = ($.anConstants.touch == "true") ? (window.pageYOffset || document.documentElement.scrollTop) : (scrollElement[0].pageYOffset || scrollElement[0].scrollTop);
          if (scrollPosition > $.anConstants.scrollPosition){
            // scrollElement.removeClass('scrollUp').addClass('scrollDown');
            if($.event.scrollDown){
              $.event.scrollDown();
            }
          } else {
            // scrollElement.removeClass('scrollDown').addClass('scrollUp');
            if($.event.scrollUp){
              $.event.scrollUp();
            }
          }
          // if(scrollPosition <= 400){
          //   $.anConstants.scrollValue = 400;
          //   scrollElement.attr('data-scrolled') && scrollElement.attr('data-scrolled', ' ');
          // }else{
          //   $.anConstants.scrollValue = scrollPosition;
          //   !scrollElement.attr('data-scrolled') && scrollElement.attr('data-scrolled', 'true');
          // }
          $.utilities.lazyLoad.init({image: true, pagination: true, video: true, ads: true});
        });
        // !$.anConstants.userInteracted && $.view.userInteracted("scroll");
      },10);
    };
  
    $.event(window, 'popstate', function(event, state){
      if(event.state){
        window.clearInterval($.utilities.default.smoothScrollTimer);
        $.stop();
        $.log.event({'name':"backButtonClicked"},{"type":""},{}); // will log menu, search, filter open clicks
        if($('#noBackView').length > 0){
          if ($('#noBackView').hasClass('dN')){
            $('#noBackView').removeClass('dN');
          }else{
            $('#noBackView').addClass('dN');
          }
          $.view.pushView($('#noBackView').attr('data-url'));
        }else{
          if(!$.anConstants.pseudoBack){
            if(!$.anConstants.app && document.location.search.indexOf('magic=true') > -1){ 
              $.utilities.default.loader(!0);
              var pseudoLandingURL = "/", fetchURL;
              if($.anConstants.magicURL){
                pseudoLandingURL = $.anConstants.magicURL;
                if(pseudoLandingURL.indexOf('?') == -1){
                  fetchURL = pseudoLandingURL + "?ajax=true";
                }else{
                  fetchURL = pseudoLandingURL + "&ajax=true";
                }
              }else{
                if(document.location.pathname == '/'){
                  pseudoLandingURL = "/shopping-offers";
                }
                fetchURL = pseudoLandingURL + "?ajax=true";
                if($.anConstants.webReferral){
                  fetchURL = fetchURL + "&webReferral=true";
                }else{
                  if($.anConstants.giveBounceDiscount && !$.anConstants.scratched && !(document.location.search.indexOf('rewards=true') > -1)){
                    fetchURL = fetchURL + "&rewards=true";
                  }
                }
              }
              setTimeout(function(){
                var ax = $.xhr();
                ax.get(fetchURL)
                .success(function(data){
                  $.utilities.default.scrollDOM();
                  $.utilities.default.updateDOM.call($, !1, data, $('.an-main'), true);
                  $.utilities.lazyLoad.init({image: true, pagination: true, video: true, ads: true});
                  $.view.replaceView(pseudoLandingURL);
                }).error(function(data){
                  $.utilities.default.loader(!1);
                });
              },200);
              return;
            }
  
            // if( typeof($.shareLoveCount_love) != "undefined" || typeof($.shareLoveCount_share) != "undefined" ){
            //     if(!!$("#beatingHeart").length){
            //       var loveShareDiv = $.createElement("div");
            //       loveShareDiv.attr("onclick","$.click(this,event)").attr("data-obj",'{"qry":"/lovesharewin/game_info?ajax=true&popstate=true","nscrl":1,"click":"pagination","con":".love_share","rplc":1,"ildr":"in"}').attr("an-lma","true").attr("an-ok","true").addClass("an-lma bgFB brp50 hp100 l0 pA t0 wp100");
            //       $("#beatingHeart").ae(loveShareDiv[0]);
            //       loveShareDiv[0].click();
            //     }  
            // }
            var noOverlay = true;
  
            if($('.viewOverlay').length > 0){
              $('.viewOverlay').each(function(){
                if(this.style.display == 'block'){
                  noOverlay = false;
                  this.style.display = 'none';
                }
              });
            }
  
            if(noOverlay){
              if(new RegExp((" ").split(' ').join("|")).test(document.location.href)){
                $.utilities.default.loader('in');
                setTimeout(function(){
                  var ax = $.xhr(), url;
                  if(window.location.search.indexOf('?') > -1){
                    url = "&ajax=true&forcereload=true";
                  }else{
                    url = "?ajax=true&forcereload=true";
                  }
                  ax.get(window.location.pathname + window.location.search + url)
                  .success(function(data){
                    $.utilities.default.updateDOM.call($, !1, data, $('.an-main'), true);
                    $.utilities.default.loader(!1);
                    $.utilities.lazyLoad.init({image: true, pagination: true, video: true, ads: true});
                  }).error(function(data){
                    $.utilities.default.loader(!1);
                  });
                },200);
              }else{
                // $.stop();
                $.view.fillView(event.state, event);
              }
            }
          }else{
            window.history.go(-1*$.anConstants.pseudoBack)
            $.anConstants.pseudoBack  = 0;
          }
        }
      }
    });
  
    $.event(window, 'error', function(err){
      var lin = !err.lineno ? '' : 'At line: ' + err.lineno;
      var colum = !err.colno ? '' : ' in column: ' + err.colno;
      var stack = !err.error ? '' : (!err.error.stack ? '' : err.error.stack.substr(0, 5000));
      var msg = !err.error ? (!err.message ? '' : err.message.substr(0, 5000)) : (!err.error.message ? '' : err.error.message.substr(0, 5000));
      if($.anConstants.test && msg !== 'Script error.'){
        alert("JS Error " + msg);
        console.log("JS Error " + msg + '\n' + lin + colum + '\nStack Trace - ' + stack);
      }
      if(err.lineno && msg.trim().length>0){
        $.log.event({"name": "jsError", "cat": "perf"}, {"type": msg, "id": lin+colum, "extra": stack} );
      }
      var suppressErrorAlert = true;
      return suppressErrorAlert;
    });
  
    $.event(window, 'beforeinstallprompt', function(e){
      e.preventDefault();
      $.anConstants.deferredPrompt = e;
      if(!$.anConstants.pwa){
        $('#vSt').addClass('a2hs');
      }
      // $('#a2hs').show();
      // return false;
    });
  
    $.event(window, 'appinstalled', function(e){
      // e.preventDefault();
      $('#vSt').removeClass('a2hs');
      $.log.event({'name': 'a2hsInstalled'},{},{},true);
      // return false;
    });
  
    // $.event(window, 'beforeunload', function(e){
    //   if(!$.anConstants.letUnload && $.anConstants.giveBounceDiscount && !$.anConstants.scratched){
    //     $.log.event({'name': 'beforeunloadFired'},{},{},true);
    //     e.preventDefault();
    //     e.returnValue = '';
    //     $.utilities.default.loader(!1);
    //     if($("#scratchCard").length == 0){
    //       var currentURL = document.location.href,
    //           fetchURL = currentURL,
    //           joinBy = "&";
    //       if(currentURL.indexOf('?') == -1){
    //         joinBy = "?";
    //       }
    //       fetchURL = currentURL + joinBy + "ajax=true&rewards=true";
    //       var ax = $.xhr();
    //       ax.get(fetchURL)
    //       .success(function(data){
    //         $.utilities.default.loader(!1);
    //         if(data && data.trim().length > 0){
    //           $('.conW').ie(data);
    //         }
    //       }).error(function(data){
    //         $.utilities.default.loader(!1);
    //       });
    //     }
    //   }else{
    //     $.anConstants.letUnload = false;
    //     delete e['returnValue'];
    //   }
    // });
  
    // $.event(window, 'hashchange', function(e){
    //   Raygun.trackEvent('pageView', {
    //     path: '/' + location.hash
    //   });
    // });
  
    // if(anConstants.touch == "false"){
    //   $.event(window, 'mousemove', function(err){
    //     // log for non bot
    //     $.log.event({'name':'isHuman'}, {"cat": "perf"});
    //   })
    // }
  
    // window.onresize = function(event){
    //   if(window.innerWidth < 1024){
    //     if(anConstants.touch == "false"){
    //       $$('#ldr').show();
    //       if(window.location.href.indexOf('?') == -1){
    //         window.location += "?is_touch=true"
    //       }else{
    //         window.location += "&is_touch=true"
    //       }
    //     }
    //   }else{
    //     if(anConstants.touch == "true" || window.location.href.indexOf('is_touch=true') > 0){
    //       $$('#ldr').show();
    //       window.location = window.location.href.replace('is_touch=true', '')
    //     }
    //   }
    // };
    // window.onresize();
  
  })(window.mahaDev);
  