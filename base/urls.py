from django.conf.urls.defaults import *

urlpatterns = patterns('base.views',
    (r'^$'             , 'show_list'   , {}, 'show_list'),
    (r'^cache_status/$', 'cache_status', {}, 'cache_status'),

    (r'^filter/(?P<doctor>\w+)/(?P<specialty>[-\w]+)/$' , 'show_list'                       , {}, 'show_filtered_list'),
    (r'^toggle/ps/$'                                    , 'toggle_preferred_specialist'     , {}, 'toggle_preferred_specialist'),
    (r'^toggle/pg/$'                                    , 'toggle_preferred_group'          , {}, 'toggle_preferred_group'),
    (r'^toggle/ups/$'                                   , 'toggle_user_preferred_specialist', {}, 'toggle_user_preferred_specialist'),
    (r'^toggle/upg/$'                                   , 'toggle_user_preferred_group'     , {}, 'toggle_user_preferred_group'),

    (r'^admin/base/specialty/add/$',                    'add_specialty',                       {}, 'add_specialty'),
    (r'^admin/base/specialty/add/append/group$',        'specialty_oneshot_append_group',      {}, 'specialty_oneshot_add_group'),
    (r'^admin/base/specialty/add/append/specialist$',   'specialty_oneshot_append_specialist', {}, 'specialty_oneshot_add_specialist'),
    (r'^admin/base/specialty/(?P<specialty_id>\d+)/$',  'edit_specialty',                      {}, 'edit_specialty'),

    (r'^admin/base/specialty/(?P<specialty_id>\d+)/group/delete/$',      'ajax_remove_group',      {}, 'ajax_remove_group'),
    (r'^admin/base/specialty/(?P<specialty_id>\d+)/specialist/delete/$', 'ajax_remove_specialist', {}, 'ajax_remove_specialist'),

    (r'^reorder/specialty/(?P<specialty_id>\d+)/$', 'reorder_groups'     , {}, 'reorder_groups'),
    (r'^reorder/group/(?P<group_id>\d+)/$'        , 'reorder_specialists', {}, 'reorder_specialists'),

    (r'^user/list/$', 'user_list', {}, 'user_list'),
    # do this to intercept the redirect to the admin change User view when done adding, editing, or deleting a user
    (r'^admin/auth/user/$', 'user_list'),

    (r'^user/(?P<username>\w+)/edit/$', 'user_edit', {}, 'user_edit'),
    (r'^user/add/$', 'user_add', {}, 'user_add'),
)
