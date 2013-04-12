from django.db import models
from django.contrib.auth.models import User 
from django.dispatch import dispatcher
from django.db.models import signals 
from signals import clear_cache_specialist, clear_cache_group, clear_cache_specialty

class UserPreferredSpecialist(models.Model):
    user       = models.ForeignKey(User)
    specialist = models.ForeignKey('Specialist')

    def __unicode__(self,):
        return "%s - %s - %s - %s" % (self.user, self.specialist.group.specialty, self.specialist.group, self.specialist)

    class Meta:
        unique_together = ("user", "specialist",)

class UserPreferredGroup(models.Model):
    user    = models.ForeignKey(User)
    group   = models.ForeignKey('Group')

    def __unicode__(self,):
        return "%s - %s - %s" % (self.user, self.group.specialty, self.group)

    class Meta:
        unique_together = ("user", "group",)


class Specialty(models.Model):
    name    = models.CharField(max_length=50, verbose_name='specialty name')
    slug    = models.SlugField(max_length=50, prepopulate_from=("name",))
    note    = models.TextField(blank=True)

    def __unicode__(self,):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'specialties'

    class Admin:
        save_on_top  = True
        search_fields = ['name']
        fields = (
          (None, {
            'fields': ('name',)
          }),
          (None, {
            'fields': ('note',)
          }),
          (None, {
            'fields': ('slug',),
            'classes': ('collapse',),
          }),
        )


COST_TIER_CHOICES = (
  ('1', '$'),
  ('2', '$$'),
  ('3', '$$$'),
  ('4', '$$$$'),
)
class Group(models.Model):
    specialty           = models.ForeignKey(Specialty, related_name='groups')
    name                = models.CharField(max_length=75, verbose_name='clinic name')
    location            = models.CharField(max_length=75, blank=True)
    phone               = models.PhoneNumberField(blank=True)
    fax                 = models.PhoneNumberField(blank=True)
    medical_records_fax = models.PhoneNumberField(blank=True)
    email               = models.EmailField(blank=True)
    website             = models.URLField(verify_exists=True, blank=True)
    note                = models.TextField(blank=True)
    cost_tier           = models.CharField(max_length=1, choices=COST_TIER_CHOICES, blank=True)
    ordering            = models.PositiveSmallIntegerField()

    def __unicode__(self,):
        return self.name

    def save(self):
        if self.ordering is None:
            try:
                self.ordering = Group.objects.filter(specialty=self.specialty).order_by('-ordering')[0].ordering + 1
            except IndexError:
                self.ordering = 0
        super(Group, self).save()

    class Meta:
        ordering            = ('specialty', 'ordering', 'name',)
        verbose_name        = 'clinic'
        verbose_name_plural = 'clinics'
        permissions         = ( ('reorder_groups', 'Can Reorder Groups'),)

    class Admin:
        list_display        = ('specialty', 'name', 'location', 'phone','fax','note')
        list_display_links  = ('name',)
        list_filter         = ('specialty', )
        save_on_top         = True
        search_fields       = ['name','specialty__name','location']
        list_select_related = True
        fields = (
          (None, {
            'fields': ('specialty','name','location',('phone','fax','medical_records_fax',),'email','note','cost_tier','website')
          }),
        )


class Specialist(models.Model):
    group      = models.ForeignKey(Group, edit_inline=models.STACKED, num_in_admin=5, num_extra_on_change=2, related_name='specialists')
    first_name = models.CharField(max_length=30, core=True)
    last_name  = models.CharField(max_length=30, core=True)
    location   = models.CharField(max_length=75, blank=True)
    note       = models.TextField(blank=True)
    ordering   = models.PositiveSmallIntegerField()

    def __unicode__(self,):
        return "%s, %s" % (self.last_name, self.first_name)

    def save(self):
        if self.ordering is None:
            try:
                self.ordering = Specialist.objects.filter(group=self.group).order_by('-ordering')[0].ordering + 1
            except IndexError:
                self.ordering = 0
        super(Specialist, self).save()

    class Meta:
        verbose_name        = 'individual specialist'
        verbose_name_plural = 'individual specialists'
        ordering            = ('ordering', 'last_name', 'first_name',)
        permissions         = ( ('reorder_specialists', 'Can Reorder Specialists'),)

    class Admin:
        list_display        = ('last_name', 'first_name', 'group')
        list_display_links  = ('last_name',)
        save_on_top         = True
        search_fields       = ['last_name','first_name','location','group__name','group__specialty__name','group__location',]
        list_select_related = True
        fields = (
          ('Specialist Details', {
            'fields': ('group',('first_name','last_name',),'location','note',)
          }),
        )

# Register some signal listeners so that when any instance of the core classes (Specialty, Group, Specialist) get updated/created
#   we can invalidate cache entries to prevent stale data
dispatcher.connect( clear_cache_specialty, signal=signals.post_save, sender=Specialty )
dispatcher.connect( clear_cache_group, signal=signals.post_save, sender=Group )
dispatcher.connect( clear_cache_specialist, signal=signals.post_save, sender=Specialist )
