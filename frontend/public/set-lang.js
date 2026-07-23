(function () {
  var lang = localStorage.getItem("lang") || "ar";
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
})();
