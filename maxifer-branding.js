/* MAXIFER · Branding compartido — inyecta el topbar visual.
   Lee el nombre de la app desde <title> (quita prefijo "MAXIFER · ").
   No hace nada si la página ya tiene su propio .topbar o .mxb-topbar.

   Soporte staticrypt: intercepta document.write(plainHTML) (que es como
   staticrypt monta la página descifrada) y le inyecta el <link>+<script>
   en su <head> antes de escribirla. En la pantalla de bloqueo NO se
   inyecta el topbar (queda limpia); el header aparece recién en la app
   descifrada. */
(function(){
    var LOGO = 'https://maxifercotizador.github.io/Presupuestador/img/favicon-192.png';
    var LOGO_FALLBACK = 'https://maxifercotizador.github.io/Presupuestador/LOGO_1080PX-100.jpg';
    var BRAND_TAGS = '<link rel="stylesheet" href="maxifer-branding.css">'
                   + '<script defer src="maxifer-branding.js"></script>';

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

    function isStaticryptLock(){
        return (document.documentElement && document.documentElement.classList.contains('staticrypt-html'))
            || (document.body && document.body.classList && document.body.classList.contains('staticrypt-body'))
            || !!document.getElementById('staticrypt-form');
    }

    /* Hook document.write para sobrevivir a staticrypt */
    try {
        var origWrite = document.write.bind(document);
        var origWriteln = document.writeln.bind(document);
        function inject(html){
            if (typeof html !== 'string') return html;
            if (html.indexOf('maxifer-branding.css') !== -1) return html;
            if (!/<\/head\s*>/i.test(html)) return html;
            return html.replace(/<\/head\s*>/i, BRAND_TAGS + '</head>');
        }
        document.write = function(html){ return origWrite(inject(html)); };
        document.writeln = function(html){ return origWriteln(inject(html)); };
    } catch(e){ /* no bloquear si el browser no permite */ }

    function init(){
        if (!document.body) return;
        if (document.querySelector('.mxb-topbar, .topbar')) return;
        if (isStaticryptLock()) return; /* la app real recarga via document.write */

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
