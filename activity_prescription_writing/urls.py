from django.conf.urls.defaults import *
from django.conf import settings
import os.path

media_root = os.path.join(os.path.dirname(__file__),"media")

urlpatterns = patterns('',
                       (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': media_root}),
                       (r'^$', 'tobaccocessation.activity_prescription_writing.views.rx'),
                       (r'^(?P<ordinal>\d+)/$', 'tobaccocessation.activity_prescription_writing.views.rx'),
)