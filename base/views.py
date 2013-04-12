from django.contrib.auth.models import User
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.template.defaultfilters import slugify 
from django.utils import simplejson
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from models import Specialty, Specialist, Group, UserPreferredGroup, UserPreferredSpecialist
from django.views.decorators.cache import never_cache
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import permission_required, user_passes_test
import logging


def build_tree(specialties):
    specialty_list = []

    # get the toplevel list of specialties
    # use select_related on Specialist to get a full tree -- saves us many queries later
    for s in specialties:
        try:
            specialty_list.append(Specialist.objects.select_related().filter(group__specialty=s)[0].group.specialty)
        except IndexError:
            try:
                specialty_list.append(Group.objects.select_related().filter(specialty=s)[0].specialty)
            except IndexError:
                specialty_list.append(s)

    # get the subtree of groups/specialists for each specialty
    for s in specialty_list:
        s.group_list = list(s.groups.all())
        for g in s.group_list:
            g.specialist_list = list(g.specialists.all())
    return specialty_list

@login_required
def show_list(request, doctor='department', specialty='all'):

    queries = []
    queries.append( 'Begin: %i' % len(connection.queries) )

    # get the doctors to list on the sidebar filter
    DocGroup = AuthGroup.objects.get(name='Provider')
    doctors_list = DocGroup.user_set.select_related().order_by('last_name','first_name')

    queries.append( 'Post Docs: %i' % len(connection.queries) )

    # determine if the "doctor" being viewed is valid or the generic department list
    if doctor == 'department':
        selected_doctor = User()
        selected_doctor.id = 0
        selected_doctor.username = "department"
    else:
        # if someone fiddles with the URL and gives an invalid doc, then 404
        selected_doctor = get_object_or_404(User, username=doctor)

    # determine if the specialty being viewed is valid or all specialties
    if specialty == 'all':
        selected_specialty = Specialty()
        selected_specialty.id = 0
        selected_specialty.slug = "all"
        specialties = list(Specialty.objects.all())
    else:
        # if someone fiddles with the URL and gives an invalid specialty, then 404
        selected_specialty = get_object_or_404(Specialty, slug=specialty)
        specialties = [selected_specialty]

    queries.append( 'Post Selected: %i' % len(connection.queries) )

    cache_key = "%i,%i,%i" % ( settings.SITE_ID, selected_doctor.id, selected_specialty.id)
    logging.debug('Lookup on %s' % cache_key)
    cached_info = cache.get( cache_key )
    if not cached_info:
        # build the full tree of specialt(y|ies)/group(s)/specialist(s)
        specialty_list = build_tree(specialties)
        queries.append( 'Post Tree construction: %i' % len(connection.queries) )

        if selected_doctor.id:
            queries.append( 'Pre-UP Sets: %i' % len(connection.queries) )
            upg_set = set([ dict.values()[0] for dict in UserPreferredGroup.objects.filter(user=selected_doctor).values('group') ])
            ups_set = set([ dict.values()[0] for dict in UserPreferredSpecialist.objects.filter(user=selected_doctor).values('specialist') ])
            queries.append( 'Post-UP Sets: %i' % len(connection.queries) )

            for specialty in specialty_list:
                for group in specialty.group_list:
                    group.preferred = group.id in upg_set
                    for specialist in group.specialist_list:
                        specialist.preferred = specialist.id in ups_set

        queries.append( 'Post Preferred: %i' % len(connection.queries) )

        cache.set( cache_key, specialty_list)
    else:
        specialty_list = cached_info  

    all_specialties = Specialty.objects.all().order_by('name')

    context_dict = {
                    'doctors_list' : doctors_list,
                    'all_specialties' : all_specialties,
                    'specialty_list' : specialty_list,
                    'selected_doctor' : selected_doctor,
                    'selected_specialty' : selected_specialty,
                    'query_count' : "<br>".join(queries),
                   }

    if selected_doctor == request.user:
      return render_to_response('user_preferred_list.html', context_dict, context_instance=RequestContext(request))
    #elif request.user.username == 'jwineinger' and selected_doctor.id == 0:
    #  return render_to_response('preferred_list.html', context_dict, context_instance=RequestContext(request))
    else:
      return render_to_response('noneditable_referral_list.html', context_dict, context_instance=RequestContext(request))

def cache_invalidate_specialty(user_id, specialty_id):
    # invalidate the cache for the specific view of the changed Specialist's Specialty
    cache_key = "%i,%i,%i" % ( settings.SITE_ID, user_id, specialty_id)
    logging.debug('Invalidate %s' % cache_key)
    cache.delete( cache_key )

    # invalidate the cache for the all-specialties view as well
    cache_key = "%i,%i,%i" % ( settings.SITE_ID, user_id, 0)
    logging.debug('Invalidate %s' % cache_key)
    cache.delete( cache_key )


@login_required
def toggle_preferred_specialist(request, ):
    specialist = get_object_or_404(Specialist, pk=request.POST['sid'])
    specialist.preferred = not specialist.preferred
    specialist.save()

#    # invalidate the cache for the specific view of the changed Specialist's Specialty
#    cache_key = "%i,%i,%i" % ( settings.SITE_ID, request.user.id, specialist.group.specialty.id)
#    cache.delete( cache_key )
#
#    # invalidate the cache for the all-specialties view as well
#    cache_key = "%i,%i,%i" % ( settings.SITE_ID, request.user.id, 0)
#    cache.delete( cache_key )
    cache_invalidate_specialty(request.user.id, specialist.group.specialty.id)

    object = {"sid": request.POST['sid'], "preferred": int(specialist.preferred) }
    return HttpResponse(simplejson.dumps(object), mimetype='application/javascript')

@login_required
def toggle_preferred_group(request,):
    group = get_object_or_404(Group, pk=request.POST['gid'])
    group.preferred = not group.preferred
    group.save()

#    # invalidate the cache for the specific view of the changed Group's Specialty
#    cache_key = "%i,%i,%i" % ( settings.SITE_ID, request.user.id, group.specialty.id)
#    cache.delete( cache_key )
#
#    # invalidate the cache for the all-specialties view as well
#    cache_key = "%i,%i,%i" % ( settings.SITE_ID, request.user.id, 0)
#    cache.delete( cache_key )
    cache_invalidate_specialty(request.user.id, group.specialty.id)

    object = {"gid": request.POST['gid'], "preferred": int(group.preferred) }
    return HttpResponse(simplejson.dumps(object), mimetype='application/javascript')

@login_required
def toggle_user_preferred_specialist(request, ):
    ups,created = UserPreferredSpecialist.objects.get_or_create(user=request.user, specialist=Specialist.objects.get(pk=request.POST['sid']))
    if not created:
      ups.delete()

#    # invalidate the cache for the specific view of the changed Specialist's Specialty
#    cache_key = "%i,%i,%i" % ( settings.SITE_ID, request.user.id, ups.specialist.group.specialty.id)
#    cache.delete( cache_key )
#
#    # invalidate the cache for the all-specialties view as well
#    cache_key = "%i,%i,%i" % ( settings.SITE_ID, request.user.id, 0)
#    cache.delete( cache_key )
    cache_invalidate_specialty(request.user.id, ups.specialist.group.specialty.id)

    object = {"sid": request.POST['sid'], "preferred": int(created) }
    return HttpResponse(simplejson.dumps(object), mimetype='application/javascript')

@login_required
def toggle_user_preferred_group(request,):
    upg,created = UserPreferredGroup.objects.get_or_create(user=request.user, group=Group.objects.get(pk=request.POST['gid']))
    if not created:
      upg.delete()

#    # invalidate the cache for the specific view of the changed Group's Specialty
#    cache_key = "%i,%i,%i" % ( settings.SITE_ID, request.user.id, upg.group.specialty.id)
#    cache.delete( cache_key )
#
#    # invalidate the cache for the all-specialties view as well
#    cache_key = "%i,%i,%i" % ( settings.SITE_ID, request.user.id, 0)
#    cache.delete( cache_key )
    cache_invalidate_specialty(request.user.id, upg.group.specialty.id)

    object = {"gid": request.POST['gid'], "preferred": int(created) }
    return HttpResponse(simplejson.dumps(object), mimetype='application/javascript')


@login_required
@permission_required('base.add_specialty')
@never_cache
def add_specialty(request,):
    from forms import SpecialtyAddForm as SpecialtyForm
    from forms import GroupInlineForm, SpecialistInlineForm
    if request.method == 'POST':
        specialty_form = SpecialtyForm(request.POST)
        group_forms = []

        groups =  request.POST.get('groups_list','').split(',')
        if not any(groups):
            groups = []

        group_forms = []
        for x in groups:
            specialists = request.POST.get('g%s-specialists_list' % x, '').split(',')
            if not any(specialists):
                specialists = []

            group_forms.append( {
                'group': GroupInlineForm(request.POST, prefix="g%s" % x),
                'specialists' : [SpecialistInlineForm(request.POST, prefix="g%s-s%s" %(x,y)) for y in specialists],
                'specialist_list' : specialists,
                } )
    
        context_dict = {
                        'specialty_form': specialty_form,
                        'group_forms' : group_forms,
                        'group_meta' : Group()._meta,
                        'specialist_meta' : Specialist()._meta,
                        'specialist_reference_form' : SpecialistInlineForm(),
                        'groups_list' : groups,
                       }
        # validate all forms
        validations = [ specialty_form.is_valid(),
                        all([ gf['group'].is_valid() for gf in group_forms]),
                        all([ sf.is_valid() for gf in group_forms for sf in gf['specialists']]),
                      ]
        
        if all(validations):
            new_specialty = specialty_form.save(commit=False)
            new_specialty.slug = slugify(new_specialty.name)
            new_specialty.save()

            for gf in group_forms:
                new_group = gf['group'].save(commit=False)
                new_group.specialty = new_specialty
                new_group.save()

                for specialist_form in gf['specialists']:
                    if type(sf) != type([]):
                        new_specialist = specialist_form.save(commit=False)
                        new_specialist.group = new_group
                        new_specialist.save()

            cache_invalidate_specialty(0, 0)
            return HttpResponseRedirect(reverse('show_filtered_list', kwargs = {'doctor' : 'department', 'specialty' : new_specialty.slug} ))
    else:
        specialty_form = SpecialtyForm()
        group_forms = []
        context_dict = {
                        'specialty_form': specialty_form,
                        'group_meta' : Group()._meta,
                        'specialist_meta' : Specialist()._meta,
                        'group_forms' : group_forms,
                        'specialist_reference_form' : SpecialistInlineForm(),
                        'groups_list' : [],
                       }
    return render_to_response('specialty_one_shot.html', context_dict, context_instance=RequestContext(request))

@login_required
@permission_required('base.change_specialty')
@never_cache
def edit_specialty(request, specialty_id):
    from forms import SpecialtyForm, GroupInlineForm, SpecialistInlineForm

    specialty = get_object_or_404(Specialty, id=specialty_id)

    if request.method == 'POST':
        group_forms = []

        # get all the groups
        groups =  request.POST.get('groups_list','').split(',')
        if not any(groups):
            groups = []

        group_forms = []
        for x in groups:
            # get the specialists in the group, or make an empty list if there arent any
            specialists = request.POST.get('g%s-specialists_list' % x, '').split(',')
            if not any(specialists):
                specialists = []

            try:
                # if the group exists in the DB, we need a form for an instance
                group = specialty.groups.get(pk=x)
                group_form = GroupInlineForm(request.POST, prefix="g%s" % x, instance=group)
            except Group.DoesNotExist:
                # if the group doesnt exist in the DB, just make a form with no instance
                group = None
                group_form = GroupInlineForm(request.POST, prefix="g%s" % x)

            # if the group does exist in the DB, then there might be existing Specialists too
            if group:
                specialist_forms = []
                for s in specialists:
                    try:
                        # if existing Specialist, create form with a Specialist instance
                        specialist = group.specialists.get(pk=s)
                        specialist_forms.append(SpecialistInlineForm(request.POST, prefix="g%s-s%s" % (x,s), instance=specialist))
                    except Specialist.DoesNotExist:
                        specialist = None
                        specialist_forms.append(SpecialistInlineForm(request.POST, prefix="g%s-s%s" % (x,s)))
            else:
                specialist_forms = [SpecialistInlineForm(request.POST, prefix="g%s-s%s" %(x,y)) for y in specialists],

            group_forms.append( {
                'group': group_form,
                'specialists' : specialist_forms,
                'specialist_list' : specialists,
                } )
    
        specialty_form = SpecialtyForm(request.POST, instance=specialty)
        context_dict = {
                        'specialty_form': specialty_form,
                        'group_forms' : group_forms,
                        'group_meta' : Group()._meta,
                        'specialist_meta' : Specialist()._meta,
                        'specialist_reference_form' : SpecialistInlineForm(),
                        'groups_list' : groups,
                       }

        # validate all forms
        validations = [
                        specialty_form.is_valid(),
                        all([ gf['group'].is_valid() for gf in group_forms]),
                        all([ sf.is_valid() for gf in group_forms for sf in gf['specialists'] if type(sf) != type([]) ]),
                      ]
        
        if all(validations):
            new_specialty = specialty_form.save(commit=False)
            new_specialty.slug = slugify(new_specialty.name)
            new_specialty.save()

            for gf in group_forms:
                new_group = gf['group'].save(commit=False)
                new_group.specialty = new_specialty
                new_group.save()

                for specialist_form in gf['specialists']:
                    if type(sf) != type([]):
                        new_specialist = specialist_form.save(commit=False)
                        new_specialist.group = new_group
                        new_specialist.save()

            cache_invalidate_specialty(0, new_specialty.id)
            return HttpResponseRedirect(reverse('show_filtered_list', kwargs = {'doctor' : 'department', 'specialty' : new_specialty.slug} ))
    else:
        groups_list = [str(grp.id) for grp in specialty.groups.all()]
        specialty_form = SpecialtyForm(instance=specialty, initial={'groups_list': ",".join(groups_list)})
        group_forms = []
        for grp in specialty.groups.all():
            specialists = [ str(spec.id) for spec in grp.specialists.all() ]
            group_forms.append( {
                'group': GroupInlineForm(prefix="g%s" % grp.id, instance=grp, initial={'specialists_list':",".join(specialists)}),
                'specialists' : [SpecialistInlineForm(prefix="g%s-s%s" %(grp.id,spec.id), instance=spec) for spec in grp.specialists.all()],
                'specialist_list' : specialists,
                } )
            
        context_dict = {'specialty_id' : specialty_id,
                        'specialty_form': specialty_form,
                        'group_meta' : Group()._meta,
                        'specialist_meta' : Specialist()._meta,
                        'group_forms' : group_forms,
                        'specialist_reference_form' : SpecialistInlineForm(),
                        'groups_list' : [ grp.id for grp in specialty.groups.all()],
                       }
    return render_to_response('specialty_one_shot.html', context_dict, context_instance=RequestContext(request))

def get_unused_id(object, present_ids):
    import random
    new = object.objects.all().order_by('-id')[0].id + random.randint(1, 1000)
    while new in set(present_ids):
        new += random.randint(1, 1000)
    return new

@login_required
@permission_required('base.add_group')
@never_cache
def specialty_oneshot_append_group(request,):
    from forms import GroupInlineForm, SpecialistInlineForm
    from django.utils import simplejson
    from django.template.loader import render_to_string
    present_groups = request.GET.get('groups').split(',')
    if not any(present_groups):
        present_groups = []
    next_group = get_unused_id(Group, present_groups)
    present_groups.append(next_group)

    forms = { 'group': GroupInlineForm(prefix="g%s" % next_group), }
    response_html = render_to_string("group_form.html",
        {'forms': forms,
         'group_meta' : Group()._meta,
         'specialist_meta' : Specialist()._meta,
         'specialist_reference_form' : SpecialistInlineForm(),
         'group_number' : next_group, }, context_instance=RequestContext(request))

    context_dict = {'new_group_html' : response_html,
                    'new_groups_value' : present_groups,}

    data = simplejson.dumps(context_dict)
    response = HttpResponse(data)
    response['mimetype'] = "text/javascript"
    response['Pragma'] = "no cache"
    response['Cache-Control'] = "no-cache, must-revalidate"
    return response
    
@login_required
@permission_required('base.add_specialist')
@never_cache
def specialty_oneshot_append_specialist(request,):
    from forms import SpecialistInlineForm
    from django.utils import simplejson
    from django.template.loader import render_to_string
    group_number = request.GET.get('group_number')
    if not group_number:
        raise Exception('no group number')

    present_specialists = request.GET.get('specialists','').split(',')
    if not any(present_specialists):
        present_specialists = []
    next_specialist = get_unused_id(Specialist, present_specialists)
    present_specialists.append(next_specialist)

    forms = {
        'specialists': [SpecialistInlineForm(prefix="g%s-s%s" % \
            (group_number, next_specialist)) ],
        'specialist_list' : [next_specialist],
            }
    response_html = render_to_string("specialists_form_row.html",
        {'forms': forms,
         'specialist_meta' : Specialist()._meta,
         'specialist_reference_form' : SpecialistInlineForm(),
         'group_number' : group_number,
         'specialist_number' : next_specialist,
        }, context_instance=RequestContext(request))

    context_dict = {'new_specialist_html' : response_html,
                    'new_specialists_value' : present_specialists,
                    'group_number' : group_number,
                   }

    data = simplejson.dumps(context_dict)
    response = HttpResponse(data)
    response['mimetype'] = "text/javascript"
    response['Pragma'] = "no cache"
    response['Cache-Control'] = "no-cache, must-revalidate"
    return response

@login_required
@permission_required('base.remove_group')
@never_cache
def ajax_remove_group(request, specialty_id,):
    try:
        group_id = request.POST.get('group_number', None)
        if not group_id:
            raise Exception('no group number')
        group = Group.objects.select_related().get(specialty__id=specialty_id, id=group_id)
        cache_invalidate_specialty(0, group.specialty.id)
        group.delete()
    except Group.DoesNotExist:
        # if cannot find it, then it was probably one that hadn't been saved yet
        pass

    response = HttpResponse()
    response['mimetype'] = "text/javascript"
    response['Pragma'] = "no cache"
    response['Cache-Control'] = "no-cache, must-revalidate"
    return response


@login_required
@permission_required('base.remove_specialist')
@never_cache
def ajax_remove_specialist(request, specialty_id, ):
    try:
        group_id = request.POST.get('group_number', None)
        specialist_id = request.POST.get('specialist_number', None)
        if not group_id:
            raise Exception('no group number')
        elif not specialist_id:
            raise Exception('no specialist number')

        specialist = Specialist.objects.select_related().get(group__specialty__id=specialty_id, group__id=group_id, id=specialist_id)
        cache_invalidate_specialty(0, specialist.group.specialty.id)
        specialist.delete()
    except Specialist.DoesNotExist:
        # if cannot find it, then it was probably one that hadn't been saved yet
        pass

    response = HttpResponse()
    response['mimetype'] = "text/javascript"
    response['Pragma'] = "no cache"
    response['Cache-Control'] = "no-cache, must-revalidate"
    return response


@login_required
@permission_required('base.reorder_groups')
@never_cache
def reorder_groups(request, specialty_id):
    specialty = get_object_or_404(Specialty, id=specialty_id)

    if request.method == 'POST':
        item_order = request.POST.get('item_order').split(',')
        ordering = 0
        for item in item_order:
            try:
                group = Group.objects.get(pk=item[2:])
                group.ordering = ordering
                group.save()
            except Group.DoesNotExist:
                pass
            ordering = ordering + 1

        cache_invalidate_specialty(0, specialty.id)
        response = HttpResponse(','.join(item_order))
        response['mimetype'] = "text/javascript"
        response['Pragma'] = "no cache"
        response['Cache-Control'] = "no-cache, must-revalidate"
        return response

    else:
        context = {
                    'object_list' : specialty.groups.all(),
                    'specialty' : specialty,
                  }
        return render_to_response('reorder-groups.html', context,  context_instance=RequestContext(request))

@login_required
@permission_required('base.reorder_specialists')
@never_cache
def reorder_specialists(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if request.method == 'POST':
        item_order = request.POST.get('item_order').split(',')
        ordering = 0
        for item in item_order:
            try:
                specialist = Specialist.objects.get(pk=item[2:])
                specialist.ordering = ordering
                specialist.save()
            except Specialist.DoesNotExist:
                pass
            ordering = ordering + 1

        cache_invalidate_specialty(0, group.specialty.id)
        response = HttpResponse(','.join(item_order))
        response['mimetype'] = "text/javascript"
        response['Pragma'] = "no cache"
        response['Cache-Control'] = "no-cache, must-revalidate"
        return response

    else:
        context = {
                    'object_list' : group.specialists.all(),
                    'group' : group,
                  }
        return render_to_response('reorder-specialists.html', context , context_instance=RequestContext(request))

@user_passes_test(lambda u: AuthGroup.objects.get(name='Administrator') in u.groups.all())
def user_list(request,):
    DocGroup = AuthGroup.objects.get(name='Provider')
    provider_list = DocGroup.user_set.select_related().order_by('last_name','first_name')

    StaffGroup = AuthGroup.objects.get(name='Staff')
    staff_list = StaffGroup.user_set.select_related().order_by('last_name','first_name')

    AdminGroup = AuthGroup.objects.get(name='Administrator')
    admin_list = AdminGroup.user_set.select_related().order_by('last_name','first_name')

    return render_to_response('user_list.html', locals(), context_instance=RequestContext(request))

@login_required
def user_edit(request, username):
    from base.forms import UserEditForm as UserForm
    user = get_object_or_404(User, username=username)

    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False) 

            if form.cleaned_data['password']:
                user.set_password( form.cleaned_data['password'] )
            user.save()

            form.save_m2m()

            return HttpResponseRedirect( reverse('user_list'))
        else:
            return render_to_response('user_form.html', {'form':form, 'user_id' : user.id }, context_instance=RequestContext(request))
        
    # set initial so that the password doesnt display anything and so that groups are checked by default
    form = UserForm(instance=user, initial={'password':'', 'groups':[grp['id'] for grp in user.groups.all().values('id')]})
    return render_to_response('user_form.html', {'form':form, 'user_id' : user.id }, context_instance=RequestContext(request))

@login_required
def user_add(request,):
    from base.forms import UserAddForm as UserForm

    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user( form.cleaned_data['username'], form.cleaned_data['email'], form.cleaned_data['password'] )

            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.is_staff = True
            user.is_active = True
            user.is_superuser = False

            user.save()

            for group in form.cleaned_data['groups']:
                user.groups.add(group)
                
            return HttpResponseRedirect( reverse('user_list'))
        else:
            return render_to_response('user_form.html', {'form':form}, context_instance=RequestContext(request))
        
    form = UserForm()
    return render_to_response('user_form.html', {'form':form}, context_instance=RequestContext(request))


@login_required
def cache_status(request, ):
    from django import http
    from django.shortcuts import render_to_response
    from django.conf import settings
    import datetime, re

    try:
        import memcache
    except ImportError:
        raise http.Http404

    if not (request.user.is_authenticated() and
            request.user.is_staff):
        raise http.Http404

    # get first memcached URI
    m = re.match(
        "memcached://([.\w]+:\d+)", settings.CACHE_BACKEND
    )
    if not m:
        raise http.Http404

    host = memcache._Host(m.group(1))
    host.connect()
    host.send_cmd("stats")

    class Stats:
        pass

    stats = Stats()

    while 1:
        line = host.readline().split(None, 2)
        if line[0] == "END":
            break
        stat, key, value = line
        try:
            # convert to native type, if possible
            value = int(value)
            if key == "uptime":
                value = datetime.timedelta(seconds=value)
            elif key == "time":
                value = datetime.datetime.fromtimestamp(value)
        except ValueError:
            pass
        setattr(stats, key, value)

    host.close_socket()

    return render_to_response(
        'memcached_status.html', dict(
            stats=stats,
            hit_rate=100 * stats.get_hits / stats.cmd_get,
            time=datetime.datetime.now(), # server time
        ))
