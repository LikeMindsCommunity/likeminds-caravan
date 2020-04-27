;(function($){
    'use strict';
  
    $.utilities = $.utilities || {};
    $.utilities.main = {
      v: "0.2.8"
    };
  
    $.utilities.default = {
      uuidv4: function(){
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
          var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
          return v.toString(16);
        });
      },
      signinbasic:function(ldrr,attributes,overlay){
        var target = this, ldrr = ldrr || !1;
        // if(ldrr){
          $.utilities.default.loader(!1, ldrr);
        // }
        if(!target.hasClass("skpv")){
          $.signinBefore = {};
          $.signinBefore.data = $("body").html();
          if($.anConstants.touch == 'true'){
            $.signinBefore.scrollState = (document.body.scrollTop || document.documentElement.scrollTop) || 1;
          }else{
            if($('.AN-scrlEle')[0]){
              $.signinBefore.scrollState = $('.AN-scrlEle')[0].scrollTop || 1;
            }else{
              $.signinBefore.scrollState = $('.conn')[0].scrollTop || 1;
            }
          }
          $.signinBefore.ttcrt = (target.hasClass("skpTrSngUp")) ? !0 : !1;
          $.signinBefore.target = ($.signinBefore.ttcrt || (target[0].href && (target[0].href.indexOf("auth/login") > -1))) ? !1 : target;
          $.signinBefore.location = window.location.href;
        }
        if(!overlay){
          if(attributes.con){
            attributes.con = !1;
          }
          if(attributes.evi){
            attributes.vi = !0;
          }
          attributes.href = "/auth/login";
        }
      },
      authOverlay: function(target, attributes, event, data){
        attributes.con = "#authCon";
        attributes.xsrl = !0;
        // attributes.vi = !1;
        $.utilities.default.signinbasic.call(target,false,attributes,true);
        $.utilities.default.updateView.call(target, event, data, attributes, false, true);
        // $(attributes.con).show();
      },
      ajax: function(event, anAttributes) {
        var target = this, 
            _event = event, 
            attributes = anAttributes, 
            method = 'get', 
            postData = '', 
            headerType = !1, 
            ldrr, fill;
        if(!attributes.nld) {
          if($.anConstants.touch == "true" && attributes.ldrt && $('#ldr-' + attributes.ldrt).length > 0){
            var loadr;
            switch(attributes.ldrt){
              
            }
          }
          if(loadr){
            if(!$.anConstants.app && ($.anConstants.touch == "true") && $.anConstants.gestureRedirectFB && $.UA.isFBinApp() && !$.UA.isOppoBrowser() && !$.UA.isVivoBrowser() && !$.UA.isIOS() && attributes.api.length < 1700){
              $.view.intent(attributes.api);
              return !1;
            }
            $('#views').ie(loadr);
          }else{
            if(attributes.ldr){
              ldrr = $(attributes.ldr);
              fill = !0;
            }
            $.utilities.default.loader((attributes.ildr || !0), ldrr, fill);
          }
        }
        if(attributes.sp) $.utilities.default.updateLayout.call(target, _event, attributes, !0);
        if(attributes.post){
          method = 'post';
          if(attributes.val){
            postData = attributes.val;
          }else{
            postData = attributes.data;
          }
        }
        if(attributes.hdr) headerType = attributes.hdr;
        var pageName = target.attr('data-pgn');
        var ax = $.xhr();
        ax[method](attributes.api, postData, headerType, pageName)
        .success(function(data){
          $.utilities.default.updateView.call(target, _event, data, attributes, ldrr);
        }).error(function(data,req){
          if((attributes.evi && req.status == attributes.evi) || req.status == "409"){
            if(target.attr('overlay') == 'true'){
              $.utilities.default.authOverlay(target, attributes, _event, data);
            }else{
              $.utilities.default.signinbasic.call(target,ldrr,attributes);
              $.utilities.default.updateView.call(target, _event, data, attributes, ldrr);
            }
          }else if(!attributes.ldrt || $.anConstants.touch == "false"){
            if(attributes.ldr){
              $(attributes.ldr).hide();
            }else{
              $.utilities.default.loader(!1);
            }
          }else if(loadr && attributes.ldrt){
            $('#vldr-' + attributes.ldrt).remove();
          }
        });
      },
      accordion: function(event, anAttributes) {
        var target = this, _event = event, attributes = anAttributes;
        if(target.hasClass('open') && !attributes.open){
          target.removeClass('open');
          if(attributes.con){
            $(attributes.con).hide();
          }else{
            target.next().hide();
          }
          if(attributes.save) target.attr('an-call', ' ');
        }else{
          if(!target.hasClass('ANretry')){
            var parent;
            if(attributes.cls ){
              parent = target.parents('accd', !0)[0] || target.parent();
            }
            if(attributes.con){
              if(attributes.cls){
                if(attributes.clsc) $(attributes.clsc).hide();
                if($(".open", parent)[0] && ($(".open", parent).hasClass("has-sub") || $(".open", parent).hasClass("tab"))) {
                  $(".open", parent).removeClass('open');
                }
              }
              target.addClass('open');
              $(attributes.con).show();
            }else{
              if(attributes.cls){
                if($(".open", parent)[0] && ($(".open", parent).hasClass("has-sub") || $(".open", parent).hasClass("tab"))) {
                  $(".open", parent).removeClass('open').each(function(){
                    $(this).next().hide();
                  });
                }
              }
              target.addClass('open').next().show();
            }
          }
          var ldrr, fill;
          if(attributes.ldr){
            ldrr = $(attributes.ldr);
            fill = !0;
          }
          if(attributes.call){
            
            if(!attributes.nld) $.utilities.default.loader(!0, ldrr, fill);
            var ax = $.xhr();
            ax.get(attributes.api)
            .success(function(data){
              if(!target.hasClass('ANretry')){
                attributes.con = attributes.con || 'next';
                $.utilities.default.updateView.call(target, _event, data, attributes, ldrr, true);
              }
              if(attributes.scrl){
                var field = $(attributes.con)[0], scrollingDiv = attributes.scrlc ? $(attributes.scrlc)[0] : !1, shake = attributes.shk ? $(attributes.shk)[0] : !1;
                $.utilities.default.st(!1, !1, field, !1, 10, !1, 10, scrollingDiv, !0, shake);
              }
              // delete attributes.call;
              // target.attr("data-obj", $.stringifyJSON(attributes));
            }).error(function(data){
              $.utilities.default.loader(!1, ldrr, fill);
              if(!target.hasClass('ANretry') && !attributes.open){
                target.removeClass('open');
                if(attributes.con){
                  $(attributes.con).hide();
                }else{
                  target.next().hide();
                }
              }
            });
          }else{
            if(attributes.sp){
              $.utilities.default.updateLayout.call(target, _event, attributes, !0);
            }
            if(attributes.scrl){
              var field = $(attributes.con)[0], scrollingDiv = attributes.scrlc ? $(attributes.scrlc)[0] : !1, shake = attributes.shk ? $(attributes.shk)[0] : !1;
              $.utilities.default.st(!1, !1, field, !1, 10, !1, 10, scrollingDiv, !0, shake);
            }
            attributes.href = attributes.href || "";
            $.utilities.default.pushReplaceView(attributes.vi, attributes.href, ldrr, !0);
          }
        }
      },
      backgroundLayer: function(elementID, state){
        if(state){
          $('#'+elementID).remove();
          $('#'+elementID+'T').ie($('#'+elementID+'T').html(), !0);
        }else{
          $('#'+elementID).removeClass('fadeIn').addClass('fadeOut');
          setTimeout(function(){
            $('#'+elementID).remove();
          }, 200)
        }
      },
      updateLayout: function(event, anAttributes, ishistory){
        var target = this, attributes = anAttributes || $.utilities.default.anAttr(target), _ishistory = ishistory;
        if(attributes.sp == "true"){
          $.log.event({'name':attributes.spdata+"OpenClick"},{"type":"","id":"","extra":""},{}); // will log menu, search, filter open clicks
          $.utilities.default.backgroundLayer(attributes.spdata+'BG', !0);
          $('#'+attributes.spdata).removeClass(attributes.trns).addClass('trns0');
          // if(attributes.spdata == "filtrD" && target[0].id == "srtV") $.click($('#anSort'));
          if(attributes.spdata == "srch") $('.srcInpu')[0].focus();
          if((attributes.spdata == "menu" && $.anConstants.navData)){
            $('#nav').html($.anConstants.navData);
            $.anConstants.navData = null;
          }
          if(!_ishistory) {
            $.utilities.default.pushReplaceView(attributes.vi, !1, !1, !0);
          }
          $.utilities.lazyLoad.init({image: true});
        }else{
          $('#'+attributes.spdata).removeClass('trns0').addClass(attributes.trns);
          if(attributes.spdata == "srch") $('.srcInpu')[0].blur();
          $.utilities.default.backgroundLayer(attributes.spdata+'BG', !1);
        }
        $('#vSt').attr('data-'+attributes.spdata, attributes.sp);
      },
      pagination: function(event, anAttributes){
        var target = this,
            attributes = anAttributes || $.utilities.default.anAttr(target);
            $('.lmaI', target[0]).show();
        if (attributes.qry && (target.attr('an-ok') == 'true' || target.hasClass('ANretry'))){
          var pageName = target.attr('an-ok', 'false').attr('data-pgn'),
              xr = $.xhr();
          xr.get(attributes.qry, !1, !1, pageName)
          .success(function(data, xhr){
            target.hide();
            if(!attributes.part){
              attributes.con = attributes.con || '.conW';
              attributes.noViewPush = !0;
              $.utilities.default.updateView.call(target, event, data, attributes);
            }else{
              $(attributes.con).ie(data, 1);
              var scripts = "";
              $('.an-js-part').each(function(){
                scripts += $(this).html();
              }).remove();
              $.view.blobScripts(scripts);
              // $.utilities.lazyLoad.init({image: !0});
            }
            target.remove();
          })
          .error(function(error){
            if(target) target.attr('an-ok', 'true');
            // $('.lmaI', target[0]).hide();
          });
        }
      },
      updateView: function(_event, viewData, anAttributes, ldr, keepURL){
        var target = this, keepurl = keepURL, 
            attributes = anAttributes || $.utilities.default.anAttr(target), 
            event = _event, data = viewData, ldrr = ldr;
        if(attributes.sel){
          $.utilities.default.tabSelection.call(target, event, attributes);
        }
        if(attributes.nav) $.utilities.default.resetCategoryNavigation();
  
        if(!attributes.xsrl){
          $.utilities.default.scrollDOM();
        }
        if(attributes.iscrl && $.view.internalScroll && $(attributes.iscrl).length > 0){
          $(attributes.iscrl)[0].scrollTop = $.view.internalScroll;
          $.view.internalScroll = !1;
        }
        
        var h1text = "";
        if($('.htextt').length > 0){
          h1text = $('.htextt').html();
        }
        $.utilities.default.updateDOM.call(target, event, data, (attributes.con ? (attributes.con == 'next' ? target.next() : $(attributes.con)) : $('.an-main')), (attributes.rplc || !1), (attributes.pre || !1));
        if(($('.htextt').length > 0) && ($('.htextt').html().trim() === '')){
          // $('#vHdr')[0].remove();
          $('.htextt').html(h1text);
        }
        $.utilities.lazyLoad.init({image: true, pagination: true, video: true, ads: true});
        if(!attributes.noViewPush) $.utilities.default.pushReplaceView(attributes.vi,attributes.href,ldrr,keepurl);
        $.anConstants.eview = !1;
      },
      scrollDOM: function(scrollValue){
        if($.anConstants.touch == 'true'){
          document.documentElement.scrollTop = scrollValue || 1;
          if(!document.documentElement.scrollTop){
            document.body.scrollTop = scrollValue || 1;
          }
        }else{
          if($('.AN-scrlEle')[0]){
            $('.AN-scrlEle')[0].scrollTop = scrollValue || 1;
          }else{
            if($('.conn').length > 0){
              $('.conn')[0].scrollTop = scrollValue || 1;
            }
          }
        }
      },
      updateDOM: function(event, data, container, replace, prepend){ // updateDOM
        var target = this, targetAttr = (target == $) ? !1 : target.attr('data-obj');
        if(data && ((target[0] && target.parent().length > 0) || !targetAttr)){
          if(replace){
            container.html(data);
          }else{
            container.ie(data, prepend);
          }
        }
        if(data && $('.ANretry', container[0])[0] && targetAttr){
          var retryCon = $('.ANretry', container[0]);
          retryCon.attr('data-obj', targetAttr).attr('onclick', '$$.click(this,event)').attr('data-href', target.attr('data-href') || " ").attr('href', target.attr('href') || " ");
        }else{
          $.view.evalScripts();
        }
      },
      anAttr: function(element){
        var eventAttr = element.attr('data-obj'),
            anObject = $.event.eventObjects[eventAttr] || ($.parseJSON(eventAttr) || {}),
            saveCall = anObject.save || !1,
            closeOthers = anObject.cls || !1,
            closeOtherCon = anObject.clsc || !1,
            forceOpen = anObject.open || !1,
            callback = anObject.call || !1,
            immediateAction = anObject.act || !1,
            queryString = (anObject.href || (element.attr('href') || element.attr('data-href'))) || !1,
            queryStringPage = anObject.qry || !1,
            queryStringOther = anObject.ohref || !1,
            queryStringPartial = anObject.phref || !1,
            stopOtherCalls = anObject.imp || !1,
            // filterUrl = anObject.fltn || !1,
            transitionClass = anObject.trns || !1,
            dataContainer = anObject.con || !1,
            dataReplace = anObject.rplc || !1,
            resetNav = anObject.nav || !1,
            // animateElement = anObject.ani || !1,
            keepUrl = anObject.url || !1,
            isNewView = anObject.vi || !1,
            ErrorisNewView = anObject.evi || !1,
            noLoader = anObject.nld || !1,
            loader = anObject.ldr || !1,
            loaderType = anObject.ldrt || !1,
            internalloader = anObject.ildr || !1,
            internalscrl = anObject.iscrl || !1,
            inter = anObject.inter || !1,
            postRequest = anObject.post || !1,
            postData = (anObject.data || element[0].value) || !1,
            spdata = anObject.spdata || !1,
            headerType = anObject.hdr || !1,
            isSelectType = anObject.chg || !1,
            isSidePane = anObject.sp || !1,
            scroll = anObject.scrl || !1,
            scrollCon = anObject.scrlc || !1,
            doNotScroll = anObject.nscrl || !1,
            shake = anObject.shk || !1,
            selectTab = anObject.sel || !1,
            click = anObject.click || !1,
            input = anObject.input || !1,
            touchend = anObject.touchend || !1,
            mouseup = anObject.mouseup || !1,
            focus = anObject.focus || !1,
            keyup = anObject.keyup || !1,
            load = anObject.load || !1,
            change = anObject.change || !1,
            blur = anObject.blur || !1,
            go = anObject.go || !1,
            track = anObject.tr || !1,
            formValidation = anObject.vf || !1,
            utilityModule = anObject.ut || 'default',
            selectValue = !1,
            vdo = anObject.vdo || !1,
            part = anObject.part || !1,
            prepend = anObject.pre || !1,
            url = '', urlstart = "", urlend = "";
  
        if(queryString){
          if(queryString.indexOf('?') > -1) {
            urlstart = queryString.split('?')[0];
            urlend = queryString.split('?')[1];
            if(urlend.indexOf('#') > -1){
              url = urlstart + '?' + urlend.split('#')[0] + '&' + urlend.split('#')[1];
            }else if(urlend){
              url = urlstart + '?' + urlend;
            }
          }else {
            if(queryString.indexOf('#') > -1){
              url = queryString.split('#')[0] + '?' + queryString.split('#')[1];
            }
          }
          if(url){
            queryString = url;
          }else{
            url = queryString;
          }
          if(keepUrl) (queryString = "");
          if(url.indexOf('?') == -1) {
            url += "?ajax=true";
          }else{
            url += "&ajax=true";
          }
          if(inter){
            url += "&inter=true";
          }
          if(vdo){
            url += "&vdo=true";
          }
          if($.anConstants.forceTouch && url.indexOf('is_touch=true') == -1){
            url += "&is_touch=true";
          }
        }else if(queryStringOther){
          url = $(queryStringOther).attr('an-qry');
          if(queryStringPartial){
            url = url + queryStringPartial;
          }
        }
        if(isSelectType){
          selectValue = element[0].value;
        }
        return {
          save: saveCall,
          cls: closeOthers,
          clsc: closeOtherCon,
          open: forceOpen,
          call: callback,
          act: immediateAction,
          href: queryString,
          qry: queryStringPage,
          imp: stopOtherCalls,
          trns: transitionClass,
          con: dataContainer,
          rplc: dataReplace,
          kurl: keepUrl,
          vi:  isNewView,
          evi: ErrorisNewView,
          nld: noLoader,
          ldr: loader,
          ldrt: loaderType,
          ildr: internalloader,
          iscrl : internalscrl,
          inter: inter,
          post: postRequest,
          data: postData,
          spdata: spdata,
          hdr: headerType,
          sp: isSidePane,
          val: selectValue,
          scrl: scroll,
          scrlc :scrollCon,
          shk: shake,
          xsrl: doNotScroll,
          nav: resetNav,
          sel: selectTab,
          click: click,
          input: input,
          touchend: touchend,
          mouseup: mouseup,
          keyup: keyup,
          focus: focus,
          load: load,
          change: change,
          blur: blur,
          ut: utilityModule,
          go: go,
          tr: track,
          vdo: vdo,
          vf: formValidation,
          pre: prepend,
          part: part,
          api: url
        };
      },
      loader: function(flag, loader, fill, loaderText, error, internal) {
        var ldr = loader || $('#ldr'),
            ldrT = $('.ldrT', ldr[0]);
        if(flag){
          ldr.removeClass('err');
          if(ldrT.length) ldrT.html(loaderText || "");
          if(loader && fill){
            $('.lmaI', ldr[0]).html($('.lmaI', $('#ldr')[0]).html());
          }
          if(flag == 'in'){
            // debugger;
            ldr.addClass('internal');
          }
          ldr.show();
        }else{
          if(error){
            ldr.addClass('err');
            if(ldrT.length > 0) ldrT.html("Error !");
          }else{}
          ldr.removeClass('internal').hide();
        }
      },
      smoothScrollTimer: !1,
      st: function(target, event, element, direction, speed, distance, step, scrollingDiv, noBuffer, shake){
        window.clearInterval($.utilities.default.smoothScrollTimer);
        var scrollAmount = 0, _shake = shake || !1;
        element = element || $('.an-srlx', $(target).parent()[0])[0];
        if(element == window){
          element = $('.conW')[0];
        }
        var psuedodistance = distance || element.getBoundingClientRect().top, _distance = distance || (Math.abs(psuedodistance) - 120), _scrollingDiv = (scrollingDiv ? $(scrollingDiv) : !1);
        if(noBuffer ){
          if(psuedodistance < 0){
            _distance = _distance + 120 + 240;
          }else{
            _distance = _distance - 240;
          }
        }
        $.utilities.default.smoothScrollTimer = setInterval(function(){
          // if ($.anConstants.touch != 'true'){
          //   document.documentElement.style = "pointer-events:none";
          // }
          var statusLeft = element.scrollLeft;
          if(direction){
            if(direction == 'l'){
              element.scrollLeft -= step;
            } else if(direction == 'r') {
              element.scrollLeft += step;
            }
            if((direction == 'l' || direction == 'r') && (statusLeft == element.scrollLeft)) {
              $('.o2', $(target).parent()[0]).removeClass('o2');
              $(target).addClass('o2');
            }
            if(direction == 't'){
              element.scrollTop -= step;
            } else if(direction == 'b'){
              element.scrollTop += step;
            }
          }else{
            // if(element && (Math.abs(element.getBoundingClientRect().top) < step) && Math.abs(psuedodistance - element.getBoundingClientRect().top)%step){
            //   window.clearInterval($.utilities.default.smoothScrollTimer);
            //   return
            // }
            if(psuedodistance < 0){
              if($.anConstants.touch == 'true'){
                if(_scrollingDiv[0]){
                  _scrollingDiv[0].scrollTop -= step;
                }else{
                  document.documentElement.scrollTop -= step;
                  if(!document.documentElement.scrollTop){
                    document.body.scrollTop -= step;
                  }
                }
              }else{
                if(_scrollingDiv[0]){
                  _scrollingDiv[0].scrollTop -= step;
                }else{
                  $('.conn')[0].scrollTop -= step;
                }
              }
            }else{
              if($.anConstants.touch == 'true'){
                if(_scrollingDiv[0]){
                  _scrollingDiv[0].scrollTop += step;
                }else{
                  document.documentElement.scrollTop += step;
                  if(!document.documentElement.scrollTop){
                    document.body.scrollTop += step;
                  }
                }
              }else{
                if(_scrollingDiv[0]){
                  _scrollingDiv[0].scrollTop += step;
                }else{
                  $('.conn')[0].scrollTop += step;
                }
              }
            }
          }
          scrollAmount += step;
          if(scrollAmount >= _distance){
            // if ($.anConstants.touch != 'true'){
            //   document.documentElement.style = "pointer-events:auto";
            // }
            if(_shake) $(element).addClass('an-shk');
            window.clearInterval($.utilities.default.smoothScrollTimer);
          }
        }, speed);
      },
      // fullScreenInfo: function(text){
      //   $("#an-fullInfo-text").html(text);
      //   $("#an-fullInfo-init")[0].click();
      //   $.anConstants.fullInfo = null;
      // },
      globalInfo: function(state, info){
        if(state){
          $('#err-I').hide();
          $('#succ-I').show();
        }else{
          $('#succ-I').hide();
          $('#err-I').show();
        }
        $('#an-sucm').html(info);
        $('#an-info').show();
        setTimeout(function(){
          $('#an-info').hide();
        }, 3000);
      },
      cached: function(event, anAttributes){
        var target = this, _event = event, attributes = anAttributes;
        var container = attributes.con ? $(attributes.con) : $('.conn');
        if(attributes.sp){
          $.utilities.default.updateLayout.call(target, _event, attributes, !0);
        }
        var ldrr;
        if(attributes.ldr){
          ldrr = $(attributes.ldr);
        }
        $.utilities.default.updateDOM.call(target, _event, $.cachedInpage[attributes.data], container, !0);
        $.utilities.lazyLoad.init({image: true, pagination: true, video: true, ads: true});
        $.utilities.default.pushReplaceView(attributes.vi,attributes.href,ldrr);
      },
      timeKeeper: function(newKey, value){
        if(newKey && value){
          $.anConstants.timeKeeper[newKey] = value;
        }
        function manageTime() {
          for (var key in $.anConstants.timeKeeper) {
            if ($.anConstants.timeKeeper.hasOwnProperty(key)){
              $.anConstants.timeKeeper[key] = $.anConstants.timeKeeper[key] - 1;
            }
          }
        }
        $.anConstants.timeKeep && clearInterval($.anConstants.timeKeep)
        $.anConstants.timeKeep = setInterval(manageTime, 1000);
        // function stopManageTime() {
        //   clearInterval(timeKeeper);
        // }
      },
      globalTimer: function(timerEleId, bySec){
        if(!timerEleId || (timerEleId && $('#'+timerEleId).length == 0)) return !1;
        function getTimeRemaining(endtime, bySec) {
          if(bySec){
            var t = endtime;
            var seconds = Math.floor(t % 60),
                minutes = Math.floor(t % 3600 / 60),
                hours = Math.floor(t % (3600*24) / 3600),
                days = Math.floor(t / (3600*24));
  
          }else{
            var t = endtime - Date.parse(new Date());
            var seconds = Math.floor((t / 1000) % 60),
                minutes = Math.floor((t / 1000 / 60) % 60),
                hours = Math.floor((t / (1000 * 60 * 60)) % 24),
                days = Math.floor(t / (1000 * 60 * 60 * 24));
          }
          return {
            'total': t,
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds
          };
        }
        function initializeClock(id, bySec) {
          var clock = $('#'+id);
          function updateClock() {
            if(!$('#'+timerEleId).length){
              clearInterval(timeinterval);
              return;
            }
            var endtime, dataTime = clock.attr('data-time');
            if(dataTime.indexOf('timeKeeper') == 0){
              endtime = $.parseInt($.anConstants.timeKeeper[dataTime.split(',')[1]]);
            }else{
              endtime = $.parseInt($('#'+timerEleId).attr('data-time'));
            }
            var t = getTimeRemaining(endtime, bySec);
            if (t.total <= 0) {
              clearInterval(timeinterval);
              clock.html(" ");
            }else{
              var arr = {'tDay': ('0' + t.days).slice(-2),
                'tHour': ('0' + t.hours).slice(-2),
                'tMin': ('0' + t.minutes).slice(-2),
                'tSec': ('0' + t.seconds).slice(-2)
              };
              for(var key in arr){
                if (!arr.hasOwnProperty(key)) continue;
                $('.'+key, clock[0]).html(arr[key]);
                if(arr[key] < 1 && key == "tDay"){
                  $('.'+key+'d', clock[0]).hide();
                }
              }
              // if($.parseInt(arr.tDay) <= 0){
              //   $('.tDayd', clock[0]).hide();
              // }
            }
          }
          updateClock();
          var timeinterval = setInterval(updateClock, 1000);
        }
        initializeClock(timerEleId, bySec);
      
      },
      delayPushPerm: function(pageName, time){
        if($.requestPermission && !$.anConstants.pushPopShown){
          $.anConstants.notifDelay && clearTimeout($.anConstants.notifDelay);
          var time = time || 10000;
          function _delayPush(){
            $.requestPermission(pageName || "");
          };
          $.anConstants.notifDelay = setTimeout(_delayPush, time);
        }
      },
      // installAPP: function(event, anAttributes){
      //   if(!$.anConstants.pwa && $.anConstants.deferredPrompt){
      //     var img = new Image();
      //     img.src = anAttributes.href;
      //     $.utilities.sw.initATHS(anAttributes.data);
      //   }else{
      //     setTimeout(function(){
      //       window.location = anAttributes.href;
      //     }, 200);
      //   }
      // },
      uiSearch: function(event, anAttributes, strict) {
        var target = this, attr = anAttributes, filter, ul, a, labelEle;
        filter = target[0].value.toUpperCase();
        ul = $(attr.con);
        if($('.moreDiv', ul[0]).length > 0){
          $('.moreDiv', ul[0]).show();
          $('.has-sub', ul[0]).hide();
        }
        $('.srchan', ul[0]).each(function() {
          labelEle = $(this);
          a = $('.srchann', labelEle[0]);
          if(strict){
            if (a.html().toUpperCase().replace(/&AMP;/g, '&').indexOf(filter) == 0) {
              labelEle.show();
            } else {
              labelEle.hide();
            }
          }else{
            if (a.html().toUpperCase().replace(/&AMP;/g, '&').indexOf(filter) > -1) {
              labelEle.show();
            } else {
              labelEle.hide();
            }
          }
        });
      },
      srchQuery: function(form){
        if($('.srcInpu', form[0])[0].value.trim().length > 2){
          var actionn = '/search/' + $('.srcInpu', form[0])[0].value.trim() + '/' + form.attr('data-urlp');
          if(form.attr('action').indexOf('voices') > -1){
            actionn = actionn + '/' + form.attr('data-urlp') + '&voiceSearch=true';
          }
          form.attr('action', actionn);
        }else{
          $('.srcInpu', form[0])[0].value = "";
          return !1;
        }
      },
      srchSuccess: function(target, form, data, attributes, event){
        if(attributes.sp) $.utilities.default.updateLayout.call(target, event, attributes, !0);
        var newurl = form.attr('action').split('/?ajax')[0];
        form.attr('action', '/search');
        attributes.href = newurl;
        $.utilities.default.updateView.call(target, event, data, attributes);
      },
      validateForm: function (event, anAttributes) {
        var form = (this.nodeName == "FORM") ? this : (this[0].form || this[0]), attributes = anAttributes, _event = event,
            f, field, formvalid = !0;
        for (f = 0; f < form.elements.length; f++) {
          field = $(form.elements[f]);
          formvalid = $.utilities.default.iv.call(field, _event, attributes);
          if(!formvalid){
            break;
          }
        }
        return formvalid;
      },
      legacyValidation: function() {
        var
          field = this,
          valid = !0,
          val = field[0].value.trim(),
          type = field.attr("type"),
          chkbox = (type === "checkbox" || type === "radio"),
          required = field.attr("required"),
          minlength = field.attr("minlength"),
          maxlength = field.attr("maxlength"),
          minvalue = field.attr("min"),
          maxvalue = field.attr("max"),
          pattern = field.attr("pattern");
        if (field[0].disabled || !required) return valid;
        valid = valid && (
          (chkbox && field[0].checked) ||
          (!chkbox && val !== "")
        );
        valid = valid && (chkbox || (
          (!minlength || val.length >= minlength) &&
          (!maxlength || val.length <= maxlength) &&
          (!minvalue || val >= minvalue) &&
          (!maxvalue || val <= maxvalue)
        ));
        if (valid && pattern) {
          pattern = new RegExp(pattern);
          valid = pattern.test(val);
        }
        return valid;
      },
      checkIFSC: function(event, anAttributes){
        var target = this;
        var val = target[0].value;
        if($.utilities.default.iv.call(this, event, anAttributes)){
          var ax = $.xhr();
          ax.get('/get_ifsc_details?q='+val, !1, 'j')
          .success(function(data){
            if(data.status){
              target.addClass('inSuc').removeClass('inErr');
              $.bankIFSC = !0;
            }else{
              target.addClass('inErr').removeClass('inSuc');
              $.bankIFSC = !1;
            }
          })
          .error(function(data){});
        }else{
          return !1;
        }
      },
      iv: function(event, anAttributes, notSilent){
        var _event = event, anfield = this, field = this[0], valid = !0, attributes = anAttributes, 
            _notSilent = notSilent || this.attr('data-silc');
        if (!(field.nodeName !== "INPUT" && field.nodeName !== "TEXTAREA" && field.nodeName !== "SELECT")) {
          // if (typeof field.willValidate !== "undefined") {
          //   if (field.nodeName === "INPUT" && field.type !== field.getAttribute("type")) {
          //     field.setCustomValidity(anfield.legacyValidation() ? "" : "error");
          //   }
          //   field.checkValidity();
          // }else {
            // field.validity = field.validity || {};
            // field.validity.valid = $.utilities.default.legacyValidation.call(anfield);
          // }
          if(anfield.attr('doextra')){
            var dataa = anfield.attr('doextra').split(',');
            if(dataa[0] == "match" && $(dataa[1])[0].value != field.value){
              valid = !1;
            }
          }else{
            valid = $.utilities.default.legacyValidation.call(anfield);
          }
          if (valid) {
            anfield.removeClass('inErr').addClass('inSuc');
            if(attributes.vf){
              var vfun = attributes.vf.split(',')[0],
                  utS = attributes.vf.split(',')[1] || this.attr('data-ut');
              attributes.vf = !1;
              var validForm = $.utilities.default.validateForm.call(field.form, _event, attributes, !0);
              if(validForm && vfun && utS){
                $.utilities[utS][vfun].call(field,_event,attributes);
              }
            }
            return !0;
          }else {
            anfield.removeClass('inSuc').addClass('inErr');
            if(_notSilent) {
              var _field = $(attributes.con)[0] || window, scrollingDiv = attributes.scrlc ? $(attributes.scrlc)[0] : !1;
                  // ,shake = attributes.shk ? $(attributes.shk)[0] : !1;
              $.utilities.default.st(!1, !1, _field, !1, 10, !1, 4, scrollingDiv, !0);
            // attributes.vot && 
              $.vo(!1, 'Please fill valid values.');
              anfield.parent().addClass('an-shk');
            }
            return !1;
          }
        }
      },
      serializeForm: function(form){
        var s = [];
        if (form && form.nodeName == "FORM") {
          var len = form.elements.length, field;
          for (var i=0; i<len; i++) {
            field = form.elements[i];
            if (field.name && !field.disabled && field.type != 'file' && field.type != 'reset' && field.type != 'submit' && field.type != 'button') {
              if ((field.type != 'checkbox' && field.type != 'radio') || field.checked) {
                s[s.length] = $.encodeURIComponent(field.name) + "=" + $.encodeURIComponent(field.value);
              }
            }
          }
        }
        return s.join('&').replace(/%20/g, '+');
      },
      submitForm: function(event, anAttributes){
        var _event = event, target = this, form = $(this[0].form || this.parents('subForm')), xr, data, attributes = anAttributes, type = attributes.data, method = form.attr('method') || 'post';
        if(type == 'helpdesk'){
          $("#oridlb", form[0]).attr("required",' ');
          if(["Cancellation"].indexOf($('#cancelOpt')[0].value)>=0){
            $("#oridlb", form[0]).attr("required", !0);
          }
        }
        if(!$.utilities.default.validateForm.call(form, _event, attributes)){
          return !1;
        }
        if(type == 'bankT' && !$.bankIFSC){
          return !1;
        }
        $.utilities.default.loader((attributes.ildr || !0));
        data = $.utilities.default.serializeForm(form[0]);
        if(type == 'srch'){
          $.utilities.default.srchQuery(form);
        }
        xr = $.xhr();
        xr[method](form.attr('action'), data)
        .success(function(data){
          
            if($('.sbErr', form[0])[0]) $('.sbErr', form[0]).hide();
            if($('.sbSuc', form[0])[0]) $('.sbSuc', form[0]).show();

          $.utilities.default.loader(!1);
          
        })
        .error(function(data){
          
            if($('.sbSuc', form[0])[0]) $('.sbSuc', form[0]).hide();
            if($('.sbErr', form[0])[0]) $('.sbErr', form[0]).show();

          $.utilities.default.loader(!1);
        });
      },
      // autofillInput: function(){
      //   $('[autocomplete]').each(function(){
      //     for(var ids in $.validatedInputvalues){
      //       if($('#'+ids)[0]){
      //         switch($('#'+ids)[0].type){
      //           case 'text':
      //           case 'number':
      //           case 'email':
      //           case 'select-one':
      //             $('#'+ids).value = $.validatedInputvalues[ids];
      //             break;
      //           case 'checkbox':
      //           case 'radio':
      //             $('#'+ids).checked = $.validatedInputvalues[ids];
      //         }
      //       }
      //     }
      //   });
      // },
      // saveToAutoFill: function(field){
      //   (field || $('[autocomplete]')).each(function(){
      //     if(!this.hidden && $(this).attr('autocomplete')) {
      //       switch(this.type){
      //         case 'text':
      //         case 'number':
      //         case 'email':
      //         case 'select-one':
      //           $.validatedInputvalues[this.id] = this.value;
      //           break;
      //         case 'checkbox':
      //         case 'radio':
      //           if (this.checked) {
      //             $.validatedInputvalues[this.id] = !0;
      //           }
      //           else {
      //             $.validatedInputvalues[this.id] = !1;
      //           }
      //       }
      //     }
      //   });
      // },
      tabSelection: function(event, anAttributes, _className){
        var element = this, className = _className || 'anSelect';
        $('.'+className, $('.'+className).parent()[0]).removeClass(className);
        element.addClass(className);
      },
      pushReplaceView: function(vi,href,ldrr,keepurl){
        var viAttr = vi, sHref = href || !1, lodrr = ldrr;
        if(keepurl) sHref = !1;
        if(viAttr){
          $.view.pushView(sHref, lodrr);
        }else{
          $.view.replaceView(sHref, lodrr);
        }
      },
      whatsapp: function(event, anAttributes){
        $.worker.init();
        $('#_wal').remove();
        var message = anAttributes.data || '', psuedoLink = $.createElement('a');
        message = (this.attr("data-loc"))? "( " + window.location.pathname + " )" + message  : message;
        psuedoLink.attr('href', 'https://api.whatsapp.com/send?phone=' + (this.attr("data-number") || $.anConstants.whatsapp) + '&text=' + (message || "")).attr('target', '_blank').attr('id', '_wal');
        $('#views').ae(psuedoLink[0]);
        setTimeout(function(){
          $('#_wal')[0].click();
        }, 10);
        // window.parent.location.href = 'https://api.whatsapp.com/send?phone=' + $.anConstants.whatsapp + '&text=' + (message || "Sign me into Limeroad.");
      }
    };
  
    $.share = function(target,event) {
      var anTar = $(target);
      var shareHref = document.location.href;
      if(anTar.attr('data-href')){
        shareHref = "https://" + document.location.hostname + anTar.attr('data-href');
      }else if(anTar.attr('data-appShare')){
        shareHref = anTar.attr('data-appShare');
      }
      if (navigator.share === undefined) {
        var shareURL = "//www.facebook.com/sharer/sharer.php?u="+shareHref;
        if($.anConstants.touch == 'true'){
          shareURL = "whatsapp://send?text="+shareHref;
        }
        window.open(shareURL,'_blank');
        return;
      }else{
        // $.utilities.default.loader('in');
        var _url = anTar.attr('data-href') || (anTar.attr('data-appShare') || document.location.href),
            _text = anTar.attr('data-text') || "Limeroad Share\n",
            _title = anTar.attr('data-title') || document.title;
        try {
          navigator.share({
            title : _title,
            text : _text,
            url : _url
          });
          // var shareid = anTar.attr("data-id"),type = anTar.attr("data-type");
          // $.log.event({'name':'incrShare'}, {"type": type , "id": shareid, "extra": "share"}, {});
          // $.utilities.default.loader(!1);
        } catch (error) {
          $.utilities.default.loader(!1);
          var shareURL = "//www.facebook.com/sharer/sharer.php?u="+shareHref;
          if($.anConstants.touch == 'true'){
            shareURL = "whatsapp://send?text="+shareHref;
          }
          window.open(shareURL,'_blank');
          return;
        }
      }
    };
  
    $.postQuery = function(obj, prefix, isDisplayURL) {
      var str = [], p;
      for(p in obj) {
        if (obj.hasOwnProperty(p)) {
          var k;
          if(isDisplayURL && !isNaN(p)){
            k = prefix ? prefix + "[]" : p;
          }else{
            k = prefix ? prefix + "[" + p + "]" : p;
          }
          var v = obj[p];
          str.push((v !== null && typeof v === "object") ?
            $.postQuery(v,k,isDisplayURL) :
            $.encodeURIComponent(k) + "=" + $.encodeURIComponent(v));
        }
      }
      return str.join("&");
    };
  
    $.getScript = function(scriptObject, callback){
      if(
          ($.anConstants.loadingScripts.indexOf(scriptObject.src) != -1) || 
          (scriptObject.module && scriptObject.version && $.utilities[scriptObject.module] && ($.utilities[scriptObject.module].v == scriptObject.version))
        ){
        if(callback && scriptObject.module && $.utilities[scriptObject.module] && $.utilities[scriptObject.module].init){
          $.utilities[scriptObject.module].init();
        }
        return false;
      }else if (callback && scriptObject.module && $.utilities[scriptObject.module] && $.utilities[scriptObject.module].init) {
        $.utilities[scriptObject.module].init();
        return false;
      }
      var script = $.createElement('script');
      script[0].onerror = function(){
        var err = script.attr("data-error");
        if(err){
          if($.parseInt(err) > 3){
            return false;
          }else{
            script.attr("data-error", $.parseInt(err) + 1);
          }
        }else{
          script.attr("data-error", "1");
        }
        $.getScript(scriptObject, callback);
      };
      script[0].onload = function(){
        $.connections(!1);
        if(callback && scriptObject.module && $.utilities[scriptObject.module] && $.utilities[scriptObject.module].init){
          $.utilities[scriptObject.module].init();
        };
        $.anConstants.loadingScripts.splice($.anConstants.loadingScripts.indexOf(scriptObject.src),1);
      };
      script[0].src = scriptObject.src;
      $.connections(!0);
      document.body.appendChild(script[0]);
      $.anConstants.loadingScripts.push(scriptObject.src);
    };
  
    $.psuedoStop = function(){
      if(navigator.serviceWorker && navigator.serviceWorker.controller){
        navigator.serviceWorker.controller.postMessage("abortFetch");
      };
      if(window.speechSynthesis){
        window.speechSynthesis.cancel();
      }
      $.worker.image.list = [];
      $.utilities.lazyLoad.image.impressions = [];
      $.anConstants.connectionsCount = 0;
      $.anConstants.trackConnectionsCount = 0;
      $.anConstants.loadingScripts = [];
    };
  
    $.stop = function(){
      $.worker.track.stop = !0;
      if(window.stop) window.stop();
      $.psuedoStop();
    };
    
    $.getPermissionStatus = function(featureName, callback) {
      if(navigator.permissions){
        navigator.permissions.query({
          name: featureName
        }).then(function(result) {
          callback.call(result);
        }).catch(function() {
          callback.call({});
        });
      }else{
        callback.call({});
      }
    };
  
    $.translate = function(language, page){
      if($.readCookie('locale') != language){
        $.log.event({'name': 'userLanguage'}, {"type": page, "id": language, "extra": ""}, {});
        $.cookie('locale', language);
        $.cookie('log_locale', 'by_choice');
        $.utilities.default.loader(!0);
        $.anConstants.letUnload = true;
        setTimeout(function(){
          $.utilities.default.loader(!1);
          window.location = window.location;
        }, 500);
      }
    };
  
    $.sanitizeHTML = function(str){
      var temp = $.createElement('div');
      temp[0].textContent = str;
      return temp.html();
    };
  
    $.connections = function(flag){
      if(flag){
        $.anConstants.connectionsCount += 1;
        if($.worker.track.stop && $.anConstants.connectionsCount > 1){
          $.worker.track.stop = !1;
        }
      }else{
        $.anConstants.connectionsCount -= 1;
      }
      if($.anConstants.connectionsCount < 0){
        $.anConstants.connectionsCount = 0; 
      }
      $.worker.init();
    };
  
    $.localStorage = function( key, val, type ) {
      if ( typeof localStorage !== 'undefined' ) {
        if (key) {
          var type = type || '[]';
          if (val) {
            $.log.event({'name': 'localStore_'+key}, {"type": val, "id": "", "extra": ""}, {});
            var _val = $.parseJSON(localStorage[key] || type);
            if(type == '{}'){
              _val[key] = _val[key] || val;
            }else if(_val.indexOf(val) == -1){
              _val.unshift(val);
            }
            localStorage[key] = $.stringifyJSON(_val);
          }else{
            var _val = $.parseJSON(localStorage[key] || type);
            return _val
          }
        }else {
          return undefined
        }
      }else{
        return null
      }
    };
  
    $.network = function(){
      if ('connection' in navigator) {
        var connection = navigator.connection;
        $.anConstants.networkInfo = {
          dl : (connection.downlink || ""),
          et : (connection.effectiveType || ""),
          rtt: (connection.rtt || "")
        }
        $.anConstants.connections = $.anConstants.networkInfo.et.indexOf('2g') > -1 ? 4 : ($.anConstants.networkInfo.et.indexOf('3g') > -1 ? 8 : 12);
        if(!connection.onchange){
          connection.onchange = function(){
            $.network();
          }
        }
      }
    };
    
  })(window.mahaDev);
  
  
  
  
  