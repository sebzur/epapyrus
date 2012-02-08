# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.views.generic import CreateView, UpdateView, DeleteView
from django.db.models import get_model
from epapyrus.forms import forms

from django.db.models.signals import post_save
from django.dispatch import receiver
import django.dispatch

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.decorators import login_required

from django.http import Http404  



tag_save = django.dispatch.Signal(providing_args=['parent','tag'])
obj_delete = django.dispatch.Signal(providing_args=['obj'])



class ArticleCreateView(CreateView):
    model = get_model('epapyrus', 'Article')
    template_name = 'epapyrus/article_add.html'
    form_class = forms.CreateArticle
   
 
    #to powinno byc w inicie, ale nie moge zwalczyc gdzie jest tworzone form
    def get_context_data(self, **kwargs):
        context = super(ArticleCreateView, self).get_context_data(**kwargs)
        context['form'].fields['teaser'].widget.attrs['class'] = 'teaser'
        return context


    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.author=self.request.user;
        self.object.save()
        tag_save.send(sender=ArticleCreateView,  parent = self.object, tag=form.cleaned_data.get('tag'))
        return HttpResponseRedirect("/article/%s/" % self.object.id)
        
class GrouperCreateView(CreateView):
    model = get_model('epapyrus','Grouper')
    template_name = 'epapyrus/grouper_add.html'
    
    form_class = forms.CreateGrouper
    
    
    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.author=self.request.user;
        self.object.save()
        #tag_save.send(sender=ArticleCreateView,  parent = self.object, tag=form.cleaned_data.get('tag'))
        return HttpResponseRedirect('/main/')
    
    
    
class ArticleUpdateView(UpdateView):
    model = get_model('epapyrus', 'Article')
    template_name = 'epapyrus/article_add.html'
    
    form_class = forms.CreateArticle
    #initial = {'tag': 1 }
 
    
        
    def get_initial(self):
        super(ArticleUpdateView, self).get_initial()
    
        if self.object.author != self.request.user:
            raise Http404
      
        self.initial['tag']=self.object.get_tag().values_list('id',flat=True)
    
        return self.initial
        
    
    def form_valid(self, form):
        print form.cleaned_data.get('tag')
        self.object = form.save(commit=False)
        self.object.author=self.request.user;
        self.object.save()
        tag_save.send(sender=ArticleCreateView,  parent = self.object, tag=form.cleaned_data.get('tag'))
        return HttpResponseRedirect("/article/%s/" % self.object.id)    

     #to powinno byc w inicie, ale nie moge zwalczyc gdzie jest tworzone 
    def get_context_data(self, **kwargs):
        context = super(ArticleUpdateView, self).get_context_data(**kwargs)
        context['form'].fields['teaser'].widget.attrs['class'] = 'teaser'
        
        return context



class ArticleDeleteView(DeleteView):
    model = get_model('epapyrus', 'Article')
    template_name = 'epapyrus/article_delete.html'
    
    form_class = forms.CreateArticle
    success_url = '/main/'
 
 
    def get_object(self, queryset=None):
        obj = super(ArticleDeleteView, self).get_object(queryset);
        if self.request.user != obj.author:
            raise Http404
        return obj
   
    # znowu klopot bo delete robi redirecta co niekoniecznie musi byc poprawne
    # a wiec najpier wysgnal a potem 
    
    
    def post(self, *args, **kwargs):
        if args[0].POST.has_key('Cancel'):
           return HttpResponseRedirect("/article/%d/" % self.get_object().id);
        else:
           obj_delete.send(sender=ArticleDeleteView,  obj = self.get_object())
           return self.delete(*args, **kwargs)



#get tag signal after save
@receiver(tag_save)
def save_tag_content(sender, **kwargs):
   
    tag_item_model = get_model('epapyrus','PrimaryTagItem')
    model = ContentType.objects.get_for_model(kwargs['parent'])
    
    saved_tags = kwargs['parent'].get_tag() 
    entered_tags = kwargs['tag']
    
    #a moze tags_delete = list(set(saved_tags) - set(enetered_tags))
    tags_deleted = [ tag for tag in saved_tags if not tag in entered_tags ]
    tags_entered = [ tag for tag in entered_tags if not tag in saved_tags ]
            
    #delete tags that are unchecked
    tag_item_model.objects.filter(content_type__exact=model.pk, object_id__exact=kwargs['parent'].id,tag__in=tags_deleted).delete()
    #enter new tags
    for i in tags_entered:
        tag_item = tag_item_model(content_object=kwargs['parent'], tag=i)
        tag_item.save()
  
   
  

@receiver(obj_delete)
def tag_obj_delete(sender, **kwargs):
   
    tag_item_model = get_model('epapyrus','PrimaryTagItem')
    model = ContentType.objects.get_for_model(kwargs['obj'])
    tag_item_model.objects.filter(content_type__exact=model.pk, object_id__exact=kwargs['obj'].id).delete() 
 