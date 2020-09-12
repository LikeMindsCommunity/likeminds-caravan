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
    records = PerDayRecordOverview.objects.all().order_by('created_at')[:10]
    context = {
        'records':records
    }
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