from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^', include('base.urls')),

    (r'^login/$', 'django.contrib.auth.views.login'),
    (r'^logout/$', 'django.contrib.auth.views.logout', {'template_name' : 'registration/logout.html'}),

    # Uncomment this for admin:
    (r'^admin/', include('django.contrib.admin.urls')),
)
