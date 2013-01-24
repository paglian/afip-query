# Create your views here.

from django.http import Http404, HttpResponse
from django import template
from backend.faqquery import FaqQuery


def hello(request):
    return HttpResponse("Hello!")


def afip_query_form(request):
    html_tmpl = """
<html>
    <head><title>{{title}}</title></head>
    <body>
        <h2>{{title}}</h2>
        <p>
        <form name="input" action="" method="get">
            Escribe tu consulta: <input type="text" name="query" text="{{query}}">
            <input type="submit" value="Buscar!">
        </form>
        </p>

        {%if query %}
        <p>
            {%if results %}
            Resultados:
                <ul>
                    {% for r in results %}
                    <li>{{r.0}}/100 - <a href="{{ afip_url }}{{ r.1 }}" target="_blank">{{ r.2 }}</a></li>
                    {% endfor %}
                </ul>
            {% else %}
                No se encontraron resultados para la consulta '{{query}}'
            {% endif %}
        </p>
        {% endif %}
    </body>
</html>
"""

    query = ""
    results = []

    if 'query' in request.GET:
        query = request.GET['query']
        try:
            fa = FaqQuery('../../backend/faqs/afip_mono_faq_full.json')
            all_results = fa.query(query)
            for r in all_results:
                score = int(float(r[0])*100)
                if score > 10:
                    r[0] = score
                    results.append(r)
        except:
            raise

    t = template.Template(html_tmpl)
    c = template.Context({
        'title': 'Consulta Monotributo AFIP',
        'afip_url' : 'http://www.afip.gob.ar/genericos/guiavirtual/consultas_detalle.aspx?id=',
        'query': query,
        'results': results
        })

    return HttpResponse(t.render(c))
