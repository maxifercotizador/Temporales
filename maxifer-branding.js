/* MAXIFER · Branding compartido — inyecta el topbar visual.
   Lee el nombre de la app desde <title> (quita prefijo "MAXIFER · ").
   No hace nada si la página ya tiene su propio .topbar o .mxb-topbar. */
(function(){
    var LOGO = 'https://maxifercotizador.github.io/Presupuestador/img/favicon-192.png';
    var LOGO_FALLBACK = 'https://maxifercotizador.github.io/Presupuestador/LOGO_1080PX-100.jpg';

    function escapeHtml(s){
        return String(s).replace(/[&<>"']/g, function(c){
            return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
        });
    }

    function appNameFromTitle(){
        var raw = (document.title || '').trim();
        var clean = raw.replace(/^MAXIFER\s*[·\-|:]+\s*/i, '').trim();
        return clean || raw || 'App';
    }

    function init(){
        if (!document.body) return;
        if (document.querySelector('.mxb-topbar, .topbar')) return;

        var appName = document.body.getAttribute('data-mxb-app') || appNameFromTitle();

        var bar = document.createElement('div');
        bar.className = 'mxb-topbar';
        bar.innerHTML = ''
            + '<div class="mxb-topbar-inner">'
            +   '<a href="index.html" class="mxb-brand">'
            +     '<img alt="MAXIFER" src="' + LOGO + '" '
            +          'onerror="this.onerror=null;this.src=\'' + LOGO_FALLBACK + '\'">'
            +     '<div class="mxb-brand-text"><strong>MAXIFER</strong>' + escapeHtml(appName) + '</div>'
            +   '</a>'
            + '</div>';
        document.body.insertBefore(bar, document.body.firstChild);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
