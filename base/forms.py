from models import Specialty, Group, Specialist
from django import newforms as forms
from django.template.defaultfilters import slugify 
from django.contrib.auth.models import User
from django.contrib.auth.models import Group as AuthGroup

class SpecialtyForm(forms.ModelForm):
    groups_list = forms.RegexField(regex='[\d,]+', widget=forms.HiddenInput, required=False)
    #groups_list = forms.RegexField(regex='[\d,]+', required=False)
    class Meta:
        model = Specialty
        exclude = ['slug']

class GroupInlineForm(forms.ModelForm):
    specialists_list = forms.RegexField(regex='[\d,]+', widget=forms.HiddenInput, required=False)
    #specialists_list = forms.RegexField(regex='[\d,]+', required=False)
    class Meta:
        model = Group
        exclude = ['specialty','ordering']

class SpecialistInlineForm(forms.ModelForm):
    class Meta:
        model = Specialist
        exclude = ['group','ordering']

class SpecialtyAddForm(SpecialtyForm):
  def clean_name(self,):
    errors = []
    if Specialty.objects.filter(slug=slugify(self.cleaned_data['name'])):
      errors.append('The specialty "%s" already exists.' % self.cleaned_data['name'] )
    
    if errors:
      raise forms.ValidationError(errors)
    else:
      return self.cleaned_data['name']

USER_TYPE_CHOICES = (
    ('Administrator','Administrator'),
    ('Provider','Provider'),
    ('Staff','Staff'),
)

class UserAddForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name  = forms.CharField(max_length=30, required=True)
    email      = forms.EmailField(label='E-mail Address', required=True)
    password   = forms.CharField(help_text=False, widget=forms.PasswordInput, required=True)
    confirm    = forms.CharField(help_text=False, widget=forms.PasswordInput, required=True)
    groups     = forms.ModelMultipleChoiceField(queryset=AuthGroup.objects.all(), required=True, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = User
        exclude = ['is_staff', 'is_active', 'is_superuser', 'last_login', 'date_joined', 'user_permissions', 'password']

 
    def clean(self,):
        errors = []
        if self.cleaned_data.get('confirm', None) != self.cleaned_data.get('password', None):
            errors.append('Passwords do not match!')
            del(self.cleaned_data['confirm'])
            del(self.cleaned_data['password'])
        if User.objects.filter(username=self.cleaned_data.get('username', None)):
            errors.append('The username "%s" already exists. Please choose another.' % self.cleaned_data['username'] )

        if errors:
            raise forms.ValidationError(errors)
        else:
            return self.cleaned_data

class UserEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name  = forms.CharField(max_length=30, required=True)
    email      = forms.EmailField(label='E-Mail Address', required=True)
    password   = forms.CharField(widget=forms.PasswordInput, required=False, help_text='Leave blank to keep the password unchanged')
    confirm    = forms.CharField(widget=forms.PasswordInput, required=False, help_text='Leave blank to keep the password unchanged')
    groups     = forms.ModelMultipleChoiceField(queryset=AuthGroup.objects.all(), required=True, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = User
        exclude = ['username', 'is_staff', 'is_active', 'is_superuser', 'last_login', 'date_joined', 'user_permissions', 'password']

    def clean(self,):
        errors = []
        if 'password' in self.cleaned_data and 'confirm' in self.cleaned_data:
            if self.cleaned_data['confirm'] != self.cleaned_data['password']:
                errors.append('Passwords do not match!')
                del(self.cleaned_data['confirm'])
                del(self.cleaned_data['password'])

        if errors:
            raise forms.ValidationError(errors)
        else:
            return self.cleaned_data
