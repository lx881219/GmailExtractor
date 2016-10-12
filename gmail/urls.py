from django.conf.urls import url, include

from . import views

app_name = "gmail"

urlpatterns = [
    url('', include('social.apps.django_app.urls', namespace='social')),
    url(r'^$', 'gmail.views.home', name='home'),
    url(r'^members/', 'gmail.views.members', name='members'),
    url(r'^logout/$', 'gmail.views.logout', name='logout'),
]