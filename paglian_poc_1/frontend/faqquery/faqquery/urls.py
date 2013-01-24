from django.conf.urls import patterns, include, url
from simplequery.views import hello
from simplequery.views import afip_query_form

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'faqquery.views.home', name='home'),
    # url(r'^faqquery/', include('faqquery.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    ('^hello/$', hello),
    ('^$', afip_query_form),
)
