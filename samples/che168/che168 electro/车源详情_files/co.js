/* Append File:/app/scripts/ahapp-2.0.js */
function ahappLog(msg) {
    console.log(msg);
}
;(function() {
    // 基础框架
    // for iOS & Android
    if (window.AHJavascriptBridge && window.AHJavascriptBridge._version==='2.0') {
    ahappLog('AHJavascriptBridge 已经存在，不能正确初始化jsbridge框架');
    return
    };

    var ua = navigator.userAgent;
    var isApp = ua.indexOf("auto_android") > -1 || ua.indexOf("auto_iphone") > -1 || ua.indexOf("autospeed_ios") > -1 || ua.indexOf("autospeed_android") > -1 || ua.indexOf("autohomeapp") > -1 || ua.indexOf("autohome") > -1 || window.__AUTOHOMEWEBVIEW__;
    if(!isApp){
        return;
    }
    var isIOS = ua.indexOf('_iphone') > -1 || ua.indexOf('iPhone') > -1 || ua.indexOf('iPad') > -1;
    var isAndroid = ua.indexOf('_android') > -1 || ua.indexOf('Android') > -1 || ua.indexOf('Adr') > -1;

    var METHOD_ON_JS_BRIDGE_READY = 'ON_JS_BRIDGE_READY';
    var METHOD_GET_JS_BIND_METHOD_NAMES = 'GET_JS_BIND_METHOD_NAMES';
    var METHOD_GET_NATIVE_BIND_METHOD_NAMES = 'GET_NATIVE_BIND_METHOD_NAMES';

    var BRIDGE_PROTOCOL_URL="";
    if (isIOS) {
        BRIDGE_PROTOCOL_URL = 'ahjb://_AUTOHOME_JAVASCRIPT_BRIDGE_'; // iOS
    }
    // var BRIDGE_PROTOCOL_URL = 'ahjb://_AUTOHOME_JAVASCRIPT_BRIDGE_'; // iOS

    var iframeTrigger; // iOS
    var AJI = window._AUTOHOME_JAVASCRIPT_INTERFACE_; // Android
    var commandQueue = [];
    var mapMethod = {};
    var mapCallback = {};
    var callbackNum = 0;


    /**
     *  调用Native方法
     *
     *  @param methodName   方法名
     *  @param methodArgs   方法参数
     *  @param callback     回调方法
     */
    function invoke(methodName, methodArgs, callback) {
        var command = _createCommand(methodName, methodArgs, callback, null, null);
        _sendCommand(command);
    }

    /**
     *  JS绑定方法, 提供给Native调用
     *
     *  @param name    方法名
     *  @param method  方法实现
     */
    function bindMethod(name, method) {
        mapMethod[name] = method;
    }

    /**
     *  解除JS绑定方法
     *
     *  @param name 方法名
     */
    function unbindMethod(name) {
        delete mapMethod[name];
    }

    /**
     *  获取所有JS绑定的方法名
     */
    function getJsBindMethodNames() {
        var methodNames = [];
        for (var methodName in mapMethod) {
            methodNames.push(methodName);
        }
        return methodNames;
    }

    /**
     * 获取所有Native绑定的方法名
     *
     * @param callback 返回的数据回调方法
     */
    function getNativeBindMethodNames(callback) {
        invoke(METHOD_GET_NATIVE_BIND_METHOD_NAMES, null, callback);
    }

    /**
     *  检查Native待处理命令(Android)
     */
    function _checkNativeCommand() {
        var strCommands = AJI.getNativeCommands();
        if (strCommands) {
            var commands = eval(strCommands);
            for (var i = 0; i < commands.length; i++) {
                _handleCommand(commands[i]);
            }
        }
    }


    /**
     * 初始化
     */
    function _init() {

        // 初始化自带的绑定
        _initBindMethods();

        // deprecated, 被事件通知取代
        if (typeof onBridgeReady === 'function'){
            onBridgeReady();
        }

        // 通知Native桥接完成
        invoke(METHOD_ON_JS_BRIDGE_READY, 'v2', null);

        // 通知JS桥接完成(事件&方法)
        var event = document.createEvent('HTMLEvents');
        event.initEvent(METHOD_ON_JS_BRIDGE_READY, false, true);
        document.dispatchEvent(event);
    }
    /**
     * 初始化自带的绑定方法
     */
    function _initBindMethods() {
        // 获取JS所有绑定的方法
        bindMethod(METHOD_GET_JS_BIND_METHOD_NAMES, function(args, callback) {
            callback(getJsBindMethodNames());
        });
    }

    /**
     *  发送JS命令
     *
     *  @param command 命令
     */
    function _sendCommand(command) {
        // iOS 触发Native检查命令队列
        if (isIOS) {
            if (!iframeTrigger) {
                iframeTrigger = document.createElement('iframe');
                iframeTrigger.style.display = 'none';
                document.documentElement.appendChild(iframeTrigger);
            }
            commandQueue.push(command);
            iframeTrigger.src = BRIDGE_PROTOCOL_URL;
        }
        // Android 直接发送命令队列
        else if (isAndroid) {
            commandQueue.push(command);
            var jsonCommands = JSON.stringify(commandQueue);
            commandQueue = [];
            AJI.receiveCommands(jsonCommands);
        }
    }

    /**
     *  Native获取JS待处理的命令组(iOS)
     */
    function _getJsCommands() {
        var jsonCommands = JSON.stringify(commandQueue);
        commandQueue = [];
        return jsonCommands;
    }

    /**
     *  接收Native发送的字符串命令组(iOS)
     *
     *  @param strCommands 字符串命令组
     */
    function _receiveCommands(strCommands) {
        var commands = eval(strCommands);
        for (var i = 0; i < commands.length; i++) {
            _handleCommand(commands[i]);
        }
    }

    /**
     *  处理命令
     *
     *  @param command 命令
     */
    function _handleCommand(command) {
        setTimeout(function() {
            if (!command) return;
            // 执行命令
            if (command.methodName) {
                var method = mapMethod[command.methodName];
                if (method) {
                    var result = method(command.methodArgs, function(result) {
                        if (command.callbackId) {
                            var returnCommand = _createCommand(null, null, null, command.callbackId, result);
                            _sendCommand(returnCommand);
                        }
                    });
                    // 兼容使用return返回结果
                    if (result) {
                        if (command.callbackId) {
                            var returnCommand = _createCommand(null, null, null, command.callbackId, result);
                            _sendCommand(returnCommand);
                        }
                    }
                }
            }
            // 回调命令
            else if (command.returnCallbackId) {
                var callback = mapCallback[command.returnCallbackId];
                if (callback) {
                    callback(command.returnCallbackData);
                    delete mapCallback[command.returnCallbackId];
                }
            }

        });
    }

    /**
     *  创建命令
     *
     *  @param methodName           方法名
     *  @param methodArgs           方法参数
     *  @param callback             回调方法
     *  @param returnCallbackId     返回的回调方法ID
     *  @param returnCallbackData   返回的回调方法数据
     */
    function _createCommand(methodName, methodArgs, callback, returnCallbackId, returnCallbackData) {
        var command = {};
        if (methodName) command.methodName = methodName;
        if (methodArgs) command.methodArgs = methodArgs;
        if (callback) {
            callbackNum++;
            var callbackId = 'js_callback_' + callbackNum;
            mapCallback[callbackId] = callback;
            command.callbackId = callbackId;
        }
        if (returnCallbackId) command.returnCallbackId = returnCallbackId;
        if (returnCallbackData) command.returnCallbackData = returnCallbackData;
        return command;
    }

    window.AHJavascriptBridge = {
        invoke: invoke,
        bindMethod: bindMethod,
        unbindMethod: unbindMethod,
        getJsBindMethodNames: getJsBindMethodNames,
        getNativeBindMethodNames: getNativeBindMethodNames,
        _checkNativeCommand: _checkNativeCommand, // iOS
        _getJsCommands: _getJsCommands, // Android
        _receiveCommands: _receiveCommands, // Android
        _version:'2.0'
    };

    window.AHJavascriptBridgeInit = _init; // 由于ios回退时，不会再次加载js，故自执行方法不能执行。此处代码供客户端调用，
    _init();
})();



;(function() {
// 具体方法
    if (window.AHAPP && window.AHJavascriptBridge && window.AHJavascriptBridge._version === '2.0') {
    ahappLog('window.AHAPP 已经存在，不能正确初始化jsbridge框架');
    return;
    }
    var ua = navigator.userAgent;
    var isIOS = ua.indexOf('_iphone') > -1 || ua.indexOf('iPhone') > -1 || ua.indexOf('iPad') > -1 || ua.indexOf('Mac') > -1;
    var isAndroid = ua.indexOf('_android') > -1 || ua.indexOf('Android') > -1 || ua.indexOf('Adr') > -1 || ua.indexOf('Linux') > -1;
    var bindMethodArray = null; // 方法数组
    var noMethodStr='{returncode:1,message:"该方法暂不支持",result:{}}';

    var SetTokenObj = {
    isRunConfig: false, // 是否运行config方法
    isSet: false, // 是否执行设置token
    token: '',  // app token
    appid: '' // app appid
    };
    if(typeof AHAPPCONFIG !== 'undefined' ){
    SetTokenObj.token = AHAPPCONFIG.token; // app token
    SetTokenObj.appid = AHAPPCONFIG.appid; // app appid
    }

    document.addEventListener('ON_JS_BRIDGE_READY',
        function() {
        AHJavascriptBridge.getNativeBindMethodNames(function(res) {
            bindMethodArray = JSON.stringify(res);
        });
        start('config', null, true); // 启动方法
    },false);

    function empFun() {} // 空方法

    function removeObjMethod(obj) { // 去除传递过来参数的 success 和 fail 方法
    var newObj = {};
    var isCopy = true;
    for (var key in obj) {
        isCopy = !( typeof obj[key] === 'function' && (key === 'success' || key === 'fail') );
        if (isCopy) {
        newObj[key] = obj[key];
        }
    }
    return newObj;
    }

    function setAHAPPToken(tokenObj){
        SetTokenObj.isRunConfig = false; // 设置token完毕后，需要重新执行config方法
        SetTokenObj.isSet = true;
        SetTokenObj.token = tokenObj.token; // app token
        SetTokenObj.appid = tokenObj.appid; // app appid
    }
    function start(type, o, isfirst) { // 开始方法
    if ( !bindMethodArray ) { // 方法数组不存在  由于历史原因此处进行二次判断
        ahappLog('bindMethodArray值不存在');
        return;
    }

    if ( bindMethodArray.indexOf(type) > -1  && !SetTokenObj.isRunConfig) { // 如果存在config并且config未成功执行
        run('config', { // 执行config
        appkey:SetTokenObj.token,
        appid:SetTokenObj.appid,
        success: function(result) {
            SetTokenObj.isRunConfig = true;
            if (!isfirst) {
            run(type, o); // 方法执行
            }
            console.log('配置启动成功');
        },
        fail: function(result) {
            SetTokenObj.isRunConfig = false;
            console.log('配置启动失败');
        }
        });
    }
    }


    function run(type, o) { // 方法执行
    var paramToApp = removeObjMethod(o); // 传递给客户端的参数
    if ( bindMethodArray.indexOf(type)>-1 ) { // 判断执行的方法是否存在
        AHJavascriptBridge.invoke(type, paramToApp,
        function(res) {
            _callbackHtml(o, res);
        });
    }else{
        ahappLog('可执行的类型为：' + bindMethodArray);
        _callbackHtml(o,noMethodStr);
    }
    }
    /*
    1、方法数组是否存在
    2、config是否存在
    3、执行方法
    */
    function invokeNative(type, o) { // 调用方法 type:方法类型 o:参数
    if ( !!bindMethodArray ) { // 方法数组存在
        if ( bindMethodArray.indexOf('config') > -1  && !SetTokenObj.isRunConfig) { // 如果存在config并且config未成功执行
        start(type, o, false); //
        return; // 结束该方法的执行
        }
        run(type, o);
        return;
    }
    // 方法数组不存在
    AHJavascriptBridge.getNativeBindMethodNames(function(res) {
        bindMethodArray = JSON.stringify(res);
        if ( bindMethodArray.indexOf('config') > -1  && !SetTokenObj.isRunConfig) { // 如果存在config并且config未成功执行
            start(type, o, false); // 重新启动配置
            return; // 结束该方法的执行
        }
        run(type, o);
    });
    }

    //H5 为右上角原生分享按钮设置分享内容
    function setNativeShareInfo(o){
        AHJavascriptBridge.bindMethod('getshareinfo',
            function(args, callback) {
                // var json={"platform":o.platform,"url":o.url,"title":o.title,"content":o.content,"imgurl":o.imgurl,extendList:o.extendList,binaryimage:o.binaryimage};
                callback(o);
            });

    }

    function setNativeShareFinish(o){
        AHJavascriptBridge.bindMethod("nativesharefinish",
            function(args, callback) {
                _callbackHtml(o,args);
            });
    }

    //H5 为右上角原生城市按钮设置城市选择完毕后的回调
    function setChooseCityFinish(o){
        AHJavascriptBridge.bindMethod("choosecityfinish",
            function(args, callback) {
                _callbackHtml(o,args);
            });
    }

    function _callbackHtml(o,resultJson){
            if(resultJson.returncode==0){
                o.success(resultJson);
            }else{
                o.fail(resultJson);
            }
    }

    window.AHAPP = {
        invokeNative:invokeNative,
        setAHAPPToken:setAHAPPToken,
        setNativeShareInfo:setNativeShareInfo,
        setNativeShareFinish:setNativeShareFinish,
        setChooseCityFinish:setChooseCityFinish,
    };
})();
/* Append File:/bi/che/ahas_single.min.js */
!function(e){"function"==typeof define&&define.amd?define(e):e()}(function(){"use strict";function e(n){return(e="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(e){return typeof e}:function(e){return e&&"function"==typeof Symbol&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e})(n)}function n(e,n){return null!=n&&"undefined"!=typeof Symbol&&n[Symbol.hasInstance]?!!n[Symbol.hasInstance](e):e instanceof n}function t(e){return o(e)||i(e)||r()}function o(e){if(Array.isArray(e)){for(var n=0,t=new Array(e.length);n<e.length;n++)t[n]=e[n];return t}}function i(e){if(Symbol.iterator in Object(e)||"[object Arguments]"===Object.prototype.toString.call(e))return Array.from(e)}function r(){throw new TypeError("Invalid attempt to spread non-iterable instance")}function a(e){if(null===e||void 0===e)throw new TypeError("Object.assign cannot be called with null or undefined");return Object(e)}function d(e){return"xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g,function(n){var t=(e+16*Math.random())%16|0;return e=Math.floor(e/16),("x"===n?t:3&t|8).toString(16)})}function c(e,n){var t=(new Date).getTime(),o="cb"+(t+"").substr(0,5),i="ahcm_jsonp_script";window[o]=function(e){e?n&&n(e):n&&n(!1);try{var t=document.getElementById(i);t.parentNode.removeChild(t)}catch(e){}};var r=document.createElement("script");r.type="text/javascript",r.id=i,r.src="https://al.autohome.com.cn/ckmp?tpid="+e+"&callback="+o+"&rid="+d(t)+"&ttp="+t,function(){var e=document.getElementsByTagName("head")[0]||document.documentElement;e?e.insertBefore(r,e.firstChild):setTimeout(arguments.callee,1e3)}()}function s(){var e=DC_session.getItem("oldreferrer")||document.referrer,n=DC_session.getItem("initreferrer");return{old:e,new:n&&n.split("$$$")[1]===location.href?n.split("$$$")[0]:DC_session.getItem("newreferrer")&&DC_session.getItem("newreferrer")===location.href?e:DC_session.getItem("newreferrer")||document.referrer}}function u(){document.referrer&&!DC_session.getItem("initreferrer")&&DC_session.setItem("initreferrer",w(document.referrer)+"$$$"+w(location.href));var e=DC_session.getItem("newreferrer")||"";location.href!==e&&(DC_session.setItem("oldreferrer",e),DC_session.setItem("newreferrer",location.href))}function f(e,n,t){var o={tempform:document.createElement("form"),frameId:"kjdp_sendBrowserLog"+Math.round(100*Math.random()),iframe:document.createElement("iframe")};o.iframe.id=o.frameId,o.iframe.name=o.frameId,o.iframe.style.display="none",o.iframe.src="about:blank",o.tempform.action=e,o.tempform.method="post",o.tempform.style.display="none";for(var i in n)o.opt=document.createElement("input"),o.opt.name=i,o.opt.value=n[i],o.tempform.appendChild(o.opt);o.opt=document.createElement("input"),o.opt.type="submit",o.tempform.appendChild(o.opt),document.body.appendChild(o.iframe);try{o.iframe.contentWindow.document.body.appendChild(o.tempform),o.tempform.submit(),o.iframe.onload=function(){t&&t(),setTimeout(function(){o.iframe.parentNode.removeChild(o.iframe),o={}},10)}}catch(e){t&&t(),console.log("上报错误")}}function p(){var e=navigator.userAgent,n=/che_(iphone|android)(;|%3B|\/)(\d+\.\d+\.\d+)/i,t=/che_(iphone|android)/.test(e)||n.test(e),o=e.match(n);return{isApp:t,app_key:o&&o[1],app_ver:o&&o[3]}}function l(){var e=navigator.userAgent,n=document.cookie,t=/auto_(iphone|android)(;|%3B|\/)(\d+\.\d+\.\d+)/i,o=/.*app_key=auto_(iphone|android)(.*)app_ver=(\d+\.\d+\.\d+)/i,i=/autohomeapp/.test(e)||t.test(e)||o.test(n),r=e.match(t)||n.match(o);return{isApp:i,app_key:r&&r[1],app_ver:r&&r[3]}}function g(){var e=navigator.userAgent,n=document.cookie,t=/auto_(iphone|android)(;|%3B|\/)(\d+\.\d+\.\d+)/i,o=/.*app_key=auto_(iphone|android)(.*)app_ver=(\d+\.\d+\.\d+)/i;return/autohomeapp/.test(e)||t.test(e)||o.test(n)}function m(){if(h(window.pvTrack)||h(window.pvTrack.site))return"00";var e=window.pvTrack.site;return e>0&&e<1211e3?"01":e>1211e3&&e<1212e3?"02":"00"}function v(e){return"[object Array]"==Object.prototype.toString.call(Object(e))}function h(e){return void 0==e||"-"==e||""==e}function w(e,t){return n(encodeURIComponent,Function)?t?encodeURI(e):encodeURIComponent(e):escape(e)}function C(e){var n="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",t=0,o="";for(t=0;t<e;t++)o+=n[parseInt(Math.random()*Math.pow(10,6))%n.length];return(new Date).getTime()+o}function _(e,n){var t=new Image(1,1);t.onload=t.onerror=function(){t.onload=t.onerror=null,t=null,n&&n()},t.src=e}function b(e){var n=[];for(var t in e)e.hasOwnProperty(t)&&n.push(w(t)+"="+w(e[t]));return n.join("&")}function y(n){function t(n,o){if("object"==e(o))for(var r in o)if("object"!=e(o[r])){var a=n+"["+r+"]="+o[r];i+=w(a)+"&"}else t(n+"["+r+"]",o[r]);return i}var o="",i="";if("object"==e(n))for(var r in n)"function"!=typeof n[r]&&"object"!=e(n[r])?o+=r+"="+w(n[r])+"&":"object"==e(n[r])&&(i="",o+=t(r,n[r]));return o.replace(/&$/g,"")}function D(e){console.log(e)}function k(e){var n=new Date;return"expires="+(e=new Date(n.getTime()+1e3*e)).toGMTString()+"; "}function I(){return window.pageLoadId?[window.pageLoadId.substring(2,10)>>3,Math.random().toString().substring(2,5)].join(""):"noloadid"}function A(){var e=BDP_DC.readCookie("ahpvno");e&&9999!=e?e++:e=1,window.BDP_DC.setCookie("ahpvno",e,86400)}var B=Object.getOwnPropertySymbols,O=Object.prototype.hasOwnProperty,P=Object.prototype.propertyIsEnumerable,x=function(){try{if(!Object.assign)return!1;var e=new String("abc");if(e[5]="de","5"===Object.getOwnPropertyNames(e)[0])return!1;for(var n={},t=0;t<10;t++)n["_"+String.fromCharCode(t)]=t;if("0123456789"!==Object.getOwnPropertyNames(n).map(function(e){return n[e]}).join(""))return!1;var o={};return"abcdefghijklmnopqrst".split("").forEach(function(e){o[e]=e}),"abcdefghijklmnopqrst"===Object.keys(Object.assign({},o)).join("")}catch(e){return!1}}()?Object.assign:function(e,n){for(var t,o,i=a(e),r=1;r<arguments.length;r++){t=Object(arguments[r]);for(var d in t)O.call(t,d)&&(i[d]=t[d]);if(B){o=B(t);for(var c=0;c<o.length;c++)P.call(t,o[c])&&(i[o[c]]=t[o[c]])}}return i},E={version:"20200618",alPath:"//al.autohome.com.cn/"};window.DC_session={setItem:function(e,n){return sessionStorage&&sessionStorage.setItem(e,n),n},getItem:function(e){return sessionStorage&&sessionStorage.getItem(e)||""}};var N=function(e){var n=e.url,t=e.data,o=e.type;o&&"get"===o.toLocaleLowerCase()?_(n+"?"+b(t)):o&&"post"===o.toLocaleLowerCase()?f(n,t):_(n+"?"+b(t))},S=function(){var e=this,n=window.screen,t=window.navigator;e.screen=n?n.width+"x"+n.height:"-",e.colorDepth=n?n.colorDepth+"-bit":"-",e.charset=document.characterSet?document.characterSet:document.charset?document.charset:"-",e.language=(t&&t.language?t.language:t&&t.browserLanguage?t.browserLanguage:"-").toLowerCase(),e.cookieEnabled=t&&t.cookieEnabled?1:0,e.docTitle=document.title?document.title.substring(0,126):"",e.getClientInfo=function(n){return n?{ahpcs:e.charset,ahpsr:e.screen,ahpsc:e.colorDepth,ahpul:e.language,ahpce:e.cookieEnabled,ahpdtl:e.docTitle}:"&ahpcs=".concat(w(e.charset),"&ahpsr=").concat(e.screen,"&ahpsc=").concat(e.colorDepth,"&ahpul=").concat(e.language,"&ahpce=").concat(e.cookieEnabled,"&ahpdtl=").concat(w(e.docTitle))}},T=function(e,n){var t=parseFloat(e),o=parseFloat(n),i=e.replace(t+".",""),r=n.replace(o+".","");return t>o||!(t<o)&&i>=r},j=function(e){g()&&T(l().app_ver||"1.0.0","10.2.4")?setTimeout(function(){try{var n={};(n=window.frames.length!=parent.frames.length?parent:window)&&n.AHJavascriptBridge&&"2.0"==n.AHJavascriptBridge._version&&n.AHJavascriptBridge.getNativeBindMethodNames?n.AHJavascriptBridge.getNativeBindMethodNames(function(t){t&&t.indexOf&&t.indexOf("visitinfo")>-1?n.AHAPP.invokeNative("visitinfo",{success:function(n){e(n&&n.result&&n.result.info?n.result.info:!1)},fail:function(n){e(!1)}}):e(!1)}):e(!1)}catch(n){e(-1)}}):e(!1)};if(!p().isApp&&g()&&!window.AHJavascriptBridge&&!window.AHAPP){var J=function(e,n,t){var o=W(e,n,t,null,null);G(o)},M=function(e,n){me[e]=n},H=function(e){delete me[e]},L=function(){var e=[];for(var n in me)e.push(n);return e},R=function(e){J(ue,null,e)},V=function(){var e=le.getNativeCommands();if(e)for(var n=ie(e),t=0;t<n.length;t++)Y(n[t])},$=function(){F(),"function"==typeof onBridgeReady&&onBridgeReady(),J(ce,"v2",null);var e=document.createEvent("HTMLEvents");e.initEvent(ce,!1,!0),document.dispatchEvent(e)},F=function(){M(se,function(e,n){n(L())})},G=function(e){if(ae)pe||((pe=document.createElement("iframe")).style.display="none",document.documentElement.appendChild(pe)),ge.push(e),pe.src=fe;else if(de){ge.push(e);var n=JSON.stringify(ge);ge=[],le.receiveCommands(n)}},U=function(){var e=JSON.stringify(ge);return ge=[],e},q=function(e){for(var n=ie(e),t=0;t<n.length;t++)Y(n[t])},Y=function(e){setTimeout(function(){if(e)if(e.methodName){var n=me[e.methodName];if(n){var t=n(e.methodArgs,function(n){if(e.callbackId){var t=W(null,null,null,e.callbackId,n);G(t)}});if(t&&e.callbackId){var o=W(null,null,null,e.callbackId,t);G(o)}}}else if(e.returnCallbackId){var i=ve[e.returnCallbackId];i&&(i(e.returnCallbackData),delete ve[e.returnCallbackId])}})},W=function(e,n,t,o,i){var r={};if(e&&(r.methodName=e),n&&(r.methodArgs=n),t){var a="js_callback_"+ ++he;ve[a]=t,r.callbackId=a}return o&&(r.returnCallbackId=o),i&&(r.returnCallbackData=i),r},z=function(e){var n={};for(var t in e)!("function"==typeof e[t]&&("success"===t||"fail"===t))&&(n[t]=e[t]);return n},K=function(e){_e.isRunConfig=!1,_e.isSet=!0,_e.token=e.token,_e.appid=e.appid},Q=function(e,n,t){if(!we)return void D("bindMethodArray值不存在");we.indexOf(e)>-1&&!_e.isRunConfig&&X("config",{appkey:_e.token,appid:_e.appid,success:function(o){_e.isRunConfig=!0,t||X(e,n),console.log("配置启动成功")},fail:function(e){_e.isRunConfig=!1,console.log("配置启动失败")}})},X=function(e,n){var t=z(n);we.indexOf(e)>-1?AHJavascriptBridge.invoke(e,t,function(e){oe(n,e)}):(D("可执行的类型为："+we),oe(n,Ce))},Z=function(e,n){if(we)return we.indexOf("config")>-1&&!_e.isRunConfig?void Q(e,n,!1):void X(e,n);AHJavascriptBridge.getNativeBindMethodNames(function(t){if((we=JSON.stringify(t)).indexOf("config")>-1&&!_e.isRunConfig)return void Q(e,n,!1);X(e,n)})},ee=function(e){AHJavascriptBridge.bindMethod("getshareinfo",function(n,t){t(e)})},ne=function(e){AHJavascriptBridge.bindMethod("nativesharefinish",function(n,t){oe(e,n)})},te=function(e){AHJavascriptBridge.bindMethod("choosecityfinish",function(n,t){oe(e,n)})},oe=function(e,n){0==n.returncode?e.success(n):e.fail(n)},ie=window.eval,re=navigator.userAgent,ae=re.indexOf("_iphone")>-1||re.indexOf("iPhone")>-1||re.indexOf("iPad")>-1,de=re.indexOf("_android")>-1||re.indexOf("Android")>-1||re.indexOf("Adr")>-1,ce="ON_JS_BRIDGE_READY",se="GET_JS_BIND_METHOD_NAMES",ue="GET_NATIVE_BIND_METHOD_NAMES",fe="";ae&&(fe="ahjb://_AUTOHOME_JAVASCRIPT_BRIDGE_");var pe,le=window._AUTOHOME_JAVASCRIPT_INTERFACE_,ge=[],me={},ve={},he=0;window.AHJavascriptBridge={invoke:J,bindMethod:M,unbindMethod:H,getJsBindMethodNames:L,getNativeBindMethodNames:R,_checkNativeCommand:V,_getJsCommands:U,_receiveCommands:q,_version:"2.0"},window.AHJavascriptBridgeInit=$,$();var ae=(re=navigator.userAgent).indexOf("_iphone")>-1||re.indexOf("iPhone")>-1||re.indexOf("iPad")>-1||re.indexOf("Mac")>-1,de=re.indexOf("_android")>-1||re.indexOf("Android")>-1||re.indexOf("Adr")>-1||re.indexOf("Linux")>-1,we=null,Ce='{returncode:1,message:"该方法暂不支持",result:{}}',_e={isRunConfig:!1,isSet:!1,token:"",appid:""};"undefined"!=typeof AHAPPCONFIG&&(_e.token=AHAPPCONFIG.token,_e.appid=AHAPPCONFIG.appid),document.addEventListener("ON_JS_BRIDGE_READY",function(){AHJavascriptBridge.getNativeBindMethodNames(function(e){we=JSON.stringify(e)}),Q("config",null,!0)},!1),window.AHAPP={invokeNative:Z,setAHAPPToken:K,setNativeShareInfo:ee,setNativeShareFinish:ne,setChooseCityFinish:te}}window.BDP_DC={domain:".autohome.com.cn",readCookie:function(e){var n=new RegExp("(^| )"+e+"=([^;]*)(;|$)"),t=document.cookie.match(n);return null!=t?decodeURIComponent(t[2]):""},setCookie:function(e,n,t,o){if(this.disableCookie&&this.disableCookie())return"disable";var i=t>0?k(t):"",r=e+"="+n;r.length>256&&(r=r.substring(0,256)),i=r+"; path=/; "+i+"domain="+(o||this.domain)+";",document.cookie=i},removeCookie:function(e){var n=(new Date).toUTCString();document.cookie=e+"=; path=/; expires="+n+"; domain="+this.domain+";"}};var be=function(e){var n=window.pvTrack||{};return DC_Config.assign(e||{},{ahpvers:window.DC_Config&&window.DC_Config.version,ahpplid:window.pageLoadId,ahpprlid:window.rPageLoadId,ahpsign:I(),ref:s().new,cur:document.URL,site:n.site||0,category:n.category||0,subcategory:n.subcategory||0,object:n.object||n.objectid||0,series:n.series||n.seriesid||0,spec:n.spec||n.specid||0,level:n.level||0,dealer:n.dealer||0},(new S).getClientInfo("post"))},ye=function(e){var n={ahpvers:DC_Config.version,ahpplid:window.pageLoadId,ahpprlid:window.rPageLoadId,ahpsign:I(),ref:s().old,cur:document.URL,extends:JSON.stringify({ah_uuid:window.BDP_DC.readCookie("__ah_uuid_ng")})};return window.pvTrack&&["site","category","subcategory","object"].forEach(function(e){null!=window.pvTrack[e]&&(n[e]=window.pvTrack[e])}),n};window.BDP_DC.domain=".che168.com",p().isApp&&T(p().app_ver||"1.0.0","7.8.3")&&void 0===window.bdpBrage&&setTimeout(function(){window.bdpBrage={},window.bdpBrage.isAvailable=function(){return"undefined"!=typeof AHJavascriptBridge},window.bdpBrage.bindMethod=function(e,n){window.bdpBrage.isAvailable()?AHJavascriptBridge.bindMethod(e,n):n(!1)},window.bdpBrage.invoke=function(e,n,t){window.bdpBrage.isAvailable()&&AHJavascriptBridge.invoke(e,n,t)}}),window.DC_Config={version:E.version,alPath:document.location.protocol+"//al.che168.com/",pvInitPath:"che_pv_init",updateLoadId:!1,assign:x},window.pageLoadId=C(12),window.DC_ahas={name:"default",getPageVars:function(e){var n=window.pvTrack||{},t=["type","typeid","abtest","bcTypeId","site_ref"],o=window.BDP_DC.readCookie("ahuuid")||"",i=window.BDP_DC.readCookie("sessionid")||"",r={auto_session:o,che_session:36==i.length?i:"",userarea:window.BDP_DC.readCookie("userarea")};null!=n.page&&(r.usc_page=n.page),null!=n.platform&&(r.usc_platform=n.platform),null!=n.abtest&&(r.abtest=n.abtest),t.forEach(function(e){null!=n[e]&&(r.type=n[e])}),null!=n.pageVars&&DC_Config.assign(r,n.pageVars),c(window.BDP_DC.readCookie("sessionid")||"",function(n){if(n){var t=n.split(","),o=t[0],i=t[1]||-1;window.BDP_DC.setCookie("ahuuid",o);var a=window.BDP_DC.readCookie("ahuuid")||"";r.auto_no=i,r.auto_session=a,p().isApp?setTimeout(function(){window.bdpBrage?window.bdpBrage.invoke("visitinfo",123,function(n){n&&n.result&&n.result.info&&(r.appVisitId=n.result.info),e&&e(JSON.stringify(r))}):e&&e(JSON.stringify(r))},10):j(function(n){n&&(r.appVisitId=n),e&&e(JSON.stringify(r))})}else e&&e(JSON.stringify(r))})},_trackPageInit:function(){A(),DC_Config.updateLoadId&&(window.rPageLoadId=window.pageLoadId,window.pageLoadId=C(10));var e=arguments[0],n=window.BDP_DC.readCookie("fvlid");h(n)&&(n=window.pageLoadId,window.BDP_DC.setCookie("fvlid",n,31536e4)),e&&(window.pvTrack=e),this.getPageVars(function(e){var t=DC_Config.assign({fvlid:n},be(),{fvlid:n,pgvar:e,ahpvno:BDP_DC.readCookie("ahpvno")});N({url:window.DC_Config.alPath+DC_Config.pvInitPath,type:"get",data:t}),DC_Config.updateLoadId=!0,u()})},_trackEvent:function(){var e=arguments[0],n=arguments[1]||{},t=window._postEvent||[];DC_Config.assign(n,ye()),arguments.length>2&&!h(arguments[2])&&("string"==typeof arguments[2]?n.evextends=arguments[2]:n.evextends=JSON.stringify(arguments[2]));var o={url:window.DC_Config.alPath+e,type:t.indexOf(e)>-1||n._post?"post":"get",data:n};N(o)},_trackerEventPath:function(){return y(DC_Config.assign(ye()))}},window.DC_ahas.push=function(e){if(v(e)){var n=e[0],o=e.slice(1);this[n].apply(this,t(o))}},window.trackCustomEvent=function(e,n,t){DC_ahas.push(["_trackEvent",e,n,t])},window.trankCustomPv=window.trackPageView=function(e){DC_ahas.push(["_trackPageInit",e])},window._trackPVTrigger||window.trackPageView(),window.ah_get_visite_info=function(){var e=BDP_DC.readCookie("sessionid")&&BDP_DC.readCookie("sessionid").split("||")[0]||"0",n=BDP_DC.readCookie("che_sessionvid")||"0";return g()?(BDP_DC.readCookie("app_deviceid")||"0")+"||"+n+"||"+window.DC_Config.version+"||03||"+BDP_DC.readCookie("ahpvno"):e+"||"+n+"||"+window.DC_Config.version+"||"+m()+"||"+BDP_DC.readCookie("ahpvno")}});

!function(n){"function"==typeof define&&define.amd?define(n):n()}(function(){"use strict";function n(n){return void 0==n||"-"==n||""==n}function e(){var n=navigator.userAgent,e=document.cookie,i=/auto_(iphone|android)(;|%3B|\/)(\d+\.\d+\.\d+)/i,t=/.*app_key=auto_(iphone|android)(.*)app_ver=(\d+\.\d+\.\d+)/i;return/autohomeapp/.test(n)||i.test(n)||t.test(e)}function i(n){console.log(n)}function t(n){if(null===n||void 0===n)throw new TypeError("Object.assign cannot be called with null or undefined");return Object(n)}if(!function(){var n=navigator.userAgent,e=/che_(iphone|android)(;|%3B|\/)(\d+\.\d+\.\d+)/i,i=/che_(iphone|android)/.test(n)||e.test(n),t=n.match(e);return{isApp:i,app_key:t&&t[1],app_ver:t&&t[3]}}().isApp&&e()&&!window.AHJavascriptBridge&&!window.AHAPP){var o=function(n,e,i){var t=h(n,e,i,null,null);l(t)},a=function(n,e){R[n]=e},r=function(n){delete R[n]},c=function(){var n=[];for(var e in R)n.push(e);return n},d=function(n){o(J,null,n)},f=function(){var n=M.getNativeCommands();if(n)for(var e=E(n),i=0;i<e.length;i++)g(e[i])},u=function(){s(),"function"==typeof onBridgeReady&&onBridgeReady(),o(B,"v2",null);var n=document.createEvent("HTMLEvents");n.initEvent(B,!1,!0),document.dispatchEvent(n)},s=function(){a(H,function(n,e){e(c())})},l=function(n){if(I)j||((j=document.createElement("iframe")).style.display="none",document.documentElement.appendChild(j)),S.push(n),j.src=x;else if(P){S.push(n);var e=JSON.stringify(S);S=[],M.receiveCommands(e)}},v=function(){var n=JSON.stringify(S);return S=[],n},p=function(n){for(var e=E(n),i=0;i<e.length;i++)g(e[i])},g=function(n){setTimeout(function(){if(n)if(n.methodName){var e=R[n.methodName];if(e){var i=e(n.methodArgs,function(e){if(n.callbackId){var i=h(null,null,null,n.callbackId,e);l(i)}});if(i&&n.callbackId){var t=h(null,null,null,n.callbackId,i);l(t)}}}else if(n.returnCallbackId){var o=T[n.returnCallbackId];o&&(o(n.returnCallbackData),delete T[n.returnCallbackId])}})},h=function(n,e,i,t,o){var a={};if(n&&(a.methodName=n),e&&(a.methodArgs=e),i){var r="js_callback_"+ ++D;T[r]=i,a.callbackId=r}return t&&(a.returnCallbackId=t),o&&(a.returnCallbackData=o),a},m=function(n){var e={};for(var i in n)!("function"==typeof n[i]&&("success"===i||"fail"===i))&&(e[i]=n[i]);return e},O=function(n){L.isRunConfig=!1,L.isSet=!0,L.token=n.token,L.appid=n.appid},_=function(n,e,t){if(!G)return void i("bindMethodArray值不存在");G.indexOf(n)>-1&&!L.isRunConfig&&A("config",{appkey:L.token,appid:L.appid,success:function(i){L.isRunConfig=!0,t||A(n,e),console.log("配置启动成功")},fail:function(n){L.isRunConfig=!1,console.log("配置启动失败")}})},A=function(n,e){var t=m(e);G.indexOf(n)>-1?AHJavascriptBridge.invoke(n,t,function(n){y(e,n)}):(i("可执行的类型为："+G),y(e,F))},b=function(n,e){if(G)return G.indexOf("config")>-1&&!L.isRunConfig?void _(n,e,!1):void A(n,e);AHJavascriptBridge.getNativeBindMethodNames(function(i){if((G=JSON.stringify(i)).indexOf("config")>-1&&!L.isRunConfig)return void _(n,e,!1);A(n,e)})},k=function(n){AHJavascriptBridge.bindMethod("getshareinfo",function(e,i){i(n)})},N=function(n){AHJavascriptBridge.bindMethod("nativesharefinish",function(e,i){y(n,e)})},C=function(n){AHJavascriptBridge.bindMethod("choosecityfinish",function(e,i){y(n,e)})},y=function(n,e){0==e.returncode?n.success(e):n.fail(e)},E=window.eval,w=navigator.userAgent,I=w.indexOf("_iphone")>-1||w.indexOf("iPhone")>-1||w.indexOf("iPad")>-1,P=w.indexOf("_android")>-1||w.indexOf("Android")>-1||w.indexOf("Adr")>-1,B="ON_JS_BRIDGE_READY",H="GET_JS_BIND_METHOD_NAMES",J="GET_NATIVE_BIND_METHOD_NAMES",x="";I&&(x="ahjb://_AUTOHOME_JAVASCRIPT_BRIDGE_");var j,M=window._AUTOHOME_JAVASCRIPT_INTERFACE_,S=[],R={},T={},D=0;window.AHJavascriptBridge={invoke:o,bindMethod:a,unbindMethod:r,getJsBindMethodNames:c,getNativeBindMethodNames:d,_checkNativeCommand:f,_getJsCommands:v,_receiveCommands:p,_version:"2.0"},window.AHJavascriptBridgeInit=u,u();var I=(w=navigator.userAgent).indexOf("_iphone")>-1||w.indexOf("iPhone")>-1||w.indexOf("iPad")>-1||w.indexOf("Mac")>-1,P=w.indexOf("_android")>-1||w.indexOf("Android")>-1||w.indexOf("Adr")>-1||w.indexOf("Linux")>-1,G=null,F='{returncode:1,message:"该方法暂不支持",result:{}}',L={isRunConfig:!1,isSet:!1,token:"",appid:""};"undefined"!=typeof AHAPPCONFIG&&(L.token=AHAPPCONFIG.token,L.appid=AHAPPCONFIG.appid),document.addEventListener("ON_JS_BRIDGE_READY",function(){AHJavascriptBridge.getNativeBindMethodNames(function(n){G=JSON.stringify(n)}),_("config",null,!0)},!1),window.AHAPP={invokeNative:b,setAHAPPToken:O,setNativeShareInfo:k,setNativeShareFinish:N,setChooseCityFinish:C}}var V=Object.getOwnPropertySymbols,q=Object.prototype.hasOwnProperty,U=Object.prototype.propertyIsEnumerable,Y=function(){try{if(!Object.assign)return!1;var n=new String("abc");if(n[5]="de","5"===Object.getOwnPropertyNames(n)[0])return!1;for(var e={},i=0;i<10;i++)e["_"+String.fromCharCode(i)]=i;if("0123456789"!==Object.getOwnPropertyNames(e).map(function(n){return e[n]}).join(""))return!1;var t={};return"abcdefghijklmnopqrst".split("").forEach(function(n){t[n]=n}),"abcdefghijklmnopqrst"===Object.keys(Object.assign({},t)).join("")}catch(n){return!1}}()?Object.assign:function(n,e){for(var i,o,a=t(n),r=1;r<arguments.length;r++){i=Object(arguments[r]);for(var c in i)q.call(i,c)&&(a[c]=i[c]);if(V){o=V(i);for(var d=0;d<o.length;d++)U.call(i,o[d])&&(a[o[d]]=i[o[d]])}}return a};!function(){try{if(e()){var i=function(e,i,t){var o=arguments[0],a=arguments[1]||{};if(("auto_common_event"===o||"che_common_event"===o)&&a.action){var r=a;arguments.length>2&&!n(arguments[2])&&(r=Y(r,arguments[2])),AHAPP.invokeNative("postClickEvent",{eventid:"h5_app_"+a.action,eventname:"h5_app_"+a.action,args:r,success:function(n){},fail:function(n){}})}},t=window.trackCustomEvent;window.trackCustomEvent=function(n,e,o){t(n,e,o),i(n,e,o)}}}catch(n){}}()});


