from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse , HttpResponseRedirect
from django.contrib.auth import logout
from django.conf import settings
from django.db.models import Q
from django.core.paginator import Paginator

from .utils import *
from .models import *
from .forms import *
from togther.models import communityType,communitySubtype,communityField
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

url = settings.URL
import logging
# uncomment to run it in localhost
# url='http://localhost:8000'
error_logger=logging.getLogger("error_logger")
info_logger=logging.getLogger("info_logger")
api_url = url + '/api/'

def dashboard(request):
    query = request.GET.get('q')
    date_1 = request.GET.get('date_1')
    date_2 = request.GET.get('date_2')
    if query and date_1 and date_2:
        community_ids = query.split(',')
        community_ids_int = []
        for c_id in community_ids:
            community_ids_int.append(int(c_id.strip()))
        # print(date_1)
        # print(date_2)
        date_1 = datetime.strptime(date_1, '%Y-%m-%d')
        date_2 = datetime.strptime(date_2, '%Y-%m-%d')
        date_2 = date_2 + timedelta(days=1)
        date_1_epoch = date_1.timestamp()
        date_2_epoch = date_2.timestamp()
        # print(community_ids)

        records = PerDayRecordOverview.objects.filter(updated_at__gte=date_1_epoch,
                                                      updated_at__lte=date_2_epoch,
                                                      community__id__in=community_ids_int)
        communities = records.values('community__id','community__name').distinct()
        # print(communities)
        result = {}
        new_date = date_1
        while date_1 != date_2:
            rows = ['-']
            result[date_1 - timedelta(days=1)] = {}
            # print(communities)
            for community in communities:
                r = records.filter(updated_at__gte=date_1.timestamp(),
                                updated_at__lte=date_1.timestamp()+24*60*60,
                                community__id=community['community__id'])
                rows.append((community['community__name']+'-'+str(community['community__id'])))
                rows.append('New Members')
                rows.append('Cumulative members')
                rows.append('All Chatroom ')
                rows.append('Admin Chatroom')
                rows.append('Intro Chatroom ')
                rows.append('Chatrooms by members only [- intro rooms] ')
                rows.append('All Messages')
                rows.append('Intro Room Messages')
                if r.exists():
                    r = r[0]
                    list =[
                        r.members_added,
                        r.cummulative_members,
                        r.new_chatrooms,
                        r.new_cm_chatrooms,
                        r.new_intro_rooms,
                        r.new_chatrooms-r.new_cm_chatrooms-r.new_intro_rooms,
                        r.new_messages,
                        r.new_intro_room_messages,
                    ]

                    # print(date_1,community['community__id'],list)
                    result[date_1 - timedelta(days=1)][community['community__id']] = list
                else:
                    list = [0,0,0,0,0,0,0,0]
                    result[date_1 - timedelta(days=1)][community['community__id']] = list
                # print(date_1)
            date_1 = date_1 + timedelta(days=1)


        result_2 = {}
        rows_2 = []
        rows_2.append('New Members')
        rows_2.append('Cumulative members')
        rows_2.append('All Chatroom ')
        rows_2.append('Admin Chatroom')
        rows_2.append('Intro Chatroom ')
        rows_2.append('Chatrooms by members only [- intro rooms] ')
        rows_2.append('All Messages')
        rows_2.append('Intro Room Messages')
        # table_2
        # result_2[' = rows_2
        while new_date != date_2:
            # rows_2 = ['-']

            # print(communities)
            member_added_total = 0
            cummulative_members_total = 0
            new_chatroom_total = 0
            new_cm_chatrooms_total = 0
            intro_chatroom_total = 0
            unique_chatroom_total = 0
            new_messages_total = 0
            new_intro_room_messages_total = 0
            # print(communities)
            for community in communities:
                r = records.filter(updated_at__gte=new_date.timestamp(),
                                updated_at__lte=new_date.timestamp()+24*60*60,
                                community__id=community['community__id'])
                # rows.append((community['community__name']+'-'+str(community['community__id'])))
                # print(r)
                if r.exists():
                    r = r[0]

                    member_added_total += r.members_added
                    cummulative_members_total += r.cummulative_members
                    new_chatroom_total += r.new_chatrooms
                    # new_chatroom_total += r.new_chatrooms
                    new_cm_chatrooms_total += r.new_cm_chatrooms
                    intro_chatroom_total += r.new_intro_rooms
                    # unique_chatroom_total = r.new_chatrooms-r.new_cm_chatrooms-r.new_intro_rooms
                    new_messages_total += r.new_messages
                    new_intro_room_messages_total += r.new_intro_room_messages
                    list = [
                        member_added_total,
                        cummulative_members_total,
                        new_chatroom_total,
                        new_cm_chatrooms_total,
                        intro_chatroom_total,
                        unique_chatroom_total,
                        new_messages_total,
                        new_intro_room_messages_total
                    ]
                    # print('---->',list)
                    # print(date_1,community['community__id'],list)
                    # result[date_1][community['community__id']] = list
                # print(date_1)
            unique_chatroom_total = new_chatroom_total - intro_chatroom_total - new_cm_chatrooms_total

            list = [
                member_added_total,
                cummulative_members_total,
                new_chatroom_total,
                new_cm_chatrooms_total,
                intro_chatroom_total,
                unique_chatroom_total,
                new_messages_total,
                new_intro_room_messages_total
            ]
            # print(list)
            result_2[new_date - timedelta(days=1)] = list
            # print(result_2)
            new_date = new_date + timedelta(days=1)

        # print(result)

        context = {
            'records':records,
            'rows':rows,
            'rows_2':rows_2,
            'result':result,
            'result_2':result_2,
            'q':query,
        }
    else:
        context = {}
    return render(request, 'cms/dashboard.html', context)



def list_community_types(request):
    communitytypes = communityType.objects.all().order_by('id')
    context = {
        'communitytypes':communitytypes,
    }
    return render(request, 'cms/list_community_types.html', context)


def add_community_types(request):
    form = communityTypeForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            return HttpResponseRedirect('/cms/list_community_types')
    context = {
        'form':form,
    }
    return render(request, 'cms/add_community_types.html', context)


def edit_community_types(request,community_type_id):
    communitytype_instance = communityType.objects.get(id = community_type_id)
    form = communityTypeForm(request.POST or None, instance=communitytype_instance)
    if request.method == 'POST':
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            return HttpResponseRedirect('/cms/list_community_types')
    context = {
        'form':form,
    }
    return render(request, 'cms/add_community_types.html', context)


def list_community_subtypes(request):
    communitysubtypes = communitySubtype.objects.all().order_by('id')
    context = {
        'communitysubtypes':communitysubtypes,
    }
    return render(request, 'cms/list_community_subtypes.html', context)


def add_community_subtypes(request):
    form = communitySubtypeForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            return HttpResponseRedirect('/cms/list_community_subtypes')
    context = {
        'form':form,
    }
    return render(request, 'cms/add_community_types.html', context)


def edit_community_subtypes(request,community_subtype_id):
    communitysubtype_instance = communitySubtype.objects.get(id = community_subtype_id)
    form = communitySubtypeForm(request.POST or None, instance=communitysubtype_instance)
    if request.method == 'POST':
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            return HttpResponseRedirect('/cms/list_community_subtypes')
    context = {
        'form':form,
    }
    return render(request, 'cms/add_community_types.html', context)


def list_community_fields(request):
    communityfields = communityField.objects.all().order_by('id')
    page = request.GET.get('page', 1)
    # print(communityfields.count())
    query = request.GET.get('q')
    if query:
        # print('in here')
        communityfields = communityfields.filter(
            Q(question_title__icontains=query) |
            Q(type__type__icontains=query) |
            Q(sub_type__sub_type__icontains=query)
        )
    # print(communityfields.count())
    paginator = Paginator(communityfields, 100)
    try:
        communityfields = paginator.page(page)
    except PageNotAnInteger:
        communityfields = paginator.page(1)
    except EmptyPage:
        communityfields = paginator.page(paginator.num_pages)

    # print(communityfields.count())
    context = {
        'communityfields':communityfields,
        'q':query,
    }
    return render(request, 'cms/list_community_fields.html', context)


def add_community_fields(request):
    form = communityFieldForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            return HttpResponseRedirect('/cms/list_community_field_types')
    context = {
        'form':form,
    }
    return render(request, 'cms/add_community_fields.html', context)


def edit_community_fields(request,community_field_id):
    communityfield_instance = communityField.objects.get(id = community_field_id)
    form = communityFieldForm(request.POST or None, instance=communityfield_instance)
    if request.method == 'POST':
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            return HttpResponseRedirect('/cms/list_community_field_types')
    context = {
        'form':form,
    }
    return render(request, 'cms/add_community_fields.html', context)



def list_new_answers(request):
    new_answers = NewAnswer.objects.all().order_by('-id')
    page = request.GET.get('page', 1)
    # print(communityfields.count())
    query = request.GET.get('q')
    if query:
        # print('in here')
        new_answers = new_answers.filter(
            Q(question_title__icontains=query) |
            Q(type__type__icontains=query) |
            Q(sub_type__sub_type__icontains=query)
        )
    # print(communityfields.count())
    paginator = Paginator(new_answers, 100)
    try:
        new_answers = paginator.page(page)
    except PageNotAnInteger:
        new_answers = paginator.page(1)
    except EmptyPage:
        new_answers = paginator.page(paginator.num_pages)

    # print(communityfields.count())
    context = {
        'new_answers':new_answers,
    }
    return render(request, 'cms/list_new_answers.html', context)




def list_all_answers(request):
    all_answers = communityAnswers.objects.all().filter(question__question_state__in=[1,2]).order_by('-id')
    page = request.GET.get('page', 1)
    # print(communityfields.count())
    query = request.GET.get('q')
    if query:
        # print('in here')
        new_answers = all_answers.filter(
            Q(question_title__icontains=query) |
            Q(type__type__icontains=query) |
            Q(sub_type__sub_type__icontains=query)
        )
    # print(communityfields.count())
    paginator = Paginator(all_answers, 100)
    try:
        all_answers = paginator.page(page)
    except PageNotAnInteger:
        all_answers = paginator.page(1)
    except EmptyPage:
        all_answers = paginator.page(paginator.num_pages)

    # print(communityfields.count())
    context = {
        'all_answers':all_answers,
    }
    return render(request, 'cms/list_all_answers.html', context)


