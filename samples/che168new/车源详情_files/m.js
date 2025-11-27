function getCookie(name, defaultValue) {
    var re = new RegExp(name + '=([^;]*);?', 'gi');
    var v = typeof defaultValue == "undefined" ? null : defaultValue;
    var r = re.exec(document.cookie) || [];
    return (r.length > 1 ? unescape(r[1]) : v);
};

var s = document.getElementsByTagName("script");
var isHaveZepto = false;
    
for (var i = 0; i < s.length; i++) {
    var src = s[i].src.toLowerCase();
    if (src.indexOf("zepto.js") > -1 || src.indexOf("zepto-1.2.min.js") > -1) {
        isHaveZepto = true;
        break;
    }
}
    
var a = document.createElement("script");
if (!isHaveZepto) {
    a.type = "text/javascript";
    a.async = false;
    a.src = "https://s.autoimg.cn/mass/zepto-1.2.min.js?" + Math.floor((new Date()).getTime() / (1000 * 60 * 60 * 24));
    s[0].parentNode.insertBefore(a, s[0]);
}

setTimeout(function () {
    try {
        a = document.createElement("script");
        a.type = "text/javascript";
        a.async = true;
        a.src = "https://x.autoimg.cn/2sc/ev/ev.js?" + Math.floor((new Date()).getTime() / (1000 * 60 * 60 * 24));
        s[0].parentNode.insertBefore(a, s[0]);
        var sid = getCookie("sessionid", "");
        sid = sid || "";
        var suid = getCookie("sessionuid", "");
        suid = suid || "";
        var img = new Image();
        img.src = "https://2scpv.autohome.com.cn/m/sid.ashx?sid=" + sid + "&suid=" + suid;
    } catch(e) {

    }
}, 1000);