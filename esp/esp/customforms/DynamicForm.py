from esp.customforms.models import Field, Attribute, Section, Page, Form
from django import forms
from django.forms.models import fields_for_model
from form_utils.forms import BetterForm
from collections import OrderedDict
from formtools.wizard.views import SessionWizardView
from django.core.files.storage import FileSystemStorage
from django.shortcuts import redirect, HttpResponse
from django.http import HttpResponseRedirect
from localflavor.us.forms import USStateField, USPhoneNumberField, USStateSelect
from esp.customforms.forms import NameField, AddressField
from esp.customforms.DynamicModel import DMH
from esp.utils.forms import DummyField
from esp.users.models import ContactInfo, ESPUser
from argcache import cache_function
from esp.program.models import Program

from esp.customforms.linkfields import cf_cache, generic_fields, custom_fields
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from esp.middleware import ESPError

class BaseCustomForm(BetterForm):
    """
    Base class for all custom forms.
    """
    def clean(self):
        """
        Takes cleaned_data and expands the values for combo fields
        """
        cleaned_data = self.cleaned_data.copy()
        for k,v in self.cleaned_data.items():
            if isinstance(v, list):
                cleaned_data[k] = ";".join(v)
            if isinstance(v, dict):
                cleaned_data.update(v)
                del cleaned_data[k]

        return cleaned_data


def matches_answer(target_val):
    """
    A simple validator that checks whether you have provided the right answer.
    """
    def func(value):
        if value != target_val:
            raise ValidationError('Incorrect answer.') #  'Expected: %s' % target_val
    return func


class CustomFormHandler():
    """
    Handles creation of 'one' Django form (=one page)
    """
    _field_types = generic_fields

    _field_attrs = ['label', 'help_text', 'required']

    _contactinfo_map = {
        'name': ['first_name', 'last_name'],
        'email': 'e_mail',
        'phone': 'phone_day',
        'address': ['address_street', 'address_city', 'address_state', 'address_zip'],
        'street': 'address_street',
        'city': 'address_city',
        'zip': 'address_zip',
        'state': 'address_state'
    }

    _combo_fields = ['name', 'address']

    def __init__(self, page, form):
        self.page = page
        self.form = form
        self.seq = page[0][0]['section__page__seq']
        self.fields = []
        self.fieldsets = []

    def _getAttrs(self, attrs):
        """
        Takes attrs from the metadata and returns its Django equivalent
        """

        other_attrs = {}
        for attr in attrs:
            if attr['attr_type'] == 'options':
                other_attrs['choices'] = []
                options_list = attr['value'].split('|')[:-1]
                for option in options_list:
                    other_attrs['choices'].append( (option, option) )
            elif attr['attr_type'] == 'limits':
                limits = attr['value'].split(',')
                if limits[0]: other_attrs['min_value'] = int(limits[0])
                if limits[1]: other_attrs['max_value'] = int(limits[1])
            elif attr['attr_type'] == 'charlimits':
                limits = attr['value'].split(',')
                if limits[0]: other_attrs['min_length'] = int(limits[0])
                if limits[1]: other_attrs['max_length'] = int(limits[1])
            """elif attr['attr_type']=='wordlimits':
                limits=attr['value'].split(',')
                if limits[0]: other_attrs['min_words']=int(limits[0])
                if limits[1]: other_attrs['max_words']=int(limits[1])
            """
        return other_attrs

    def _getFields(self):
        """
        Sets self.fields and self.fieldsets for this page
        """
        model_fields_cache = {}
        for section in self.page:
            curr_fieldset = []
            curr_fieldset.extend([section[0]['section__title'], {'fields':[], 'classes':['section',]}])
            curr_fieldset[1]['description'] = section[0]['section__description']

            # Check for only_fkey models.
            # If any, insert the relevant field into the first section of the fist page
            if section[0]['section__seq'] == 0 and self.seq == 0:
                if self.form.link_type != '-1':
                    label = 'Please pick the %s you want to fill the form for' % self.form.link_type
                    link_cls = cf_cache.only_fkey_models[self.form.link_type]
                    if self.form.link_id == -1:
                        # User needs to be shown a list of instances from which to select
                        queryset = link_cls.objects.all()
                        widget = forms.Select()
                    else:
                        queryset = link_cls.objects.filter(pk=self.form.link_id)
                        widget = forms.HiddenInput()
                    fld = forms.ModelChoiceField(queryset = queryset, label = label, initial = queryset[0],
                                                widget = widget, required = True, empty_label = None)
                    self.fields.append(['link_%s' % link_cls.__name__, fld ])
                    curr_fieldset[1]['fields'].append('link_%s' % link_cls.__name__)

            for field in section:
                field_name = 'question_%d' % field['id']
                field_attrs = {'label': field['label'], 'help_text': field['help_text'], 'required': field['required']}

                # Setting the 'name' attribute for combo fields
                """
                if field['field_type'] in self._combo_fields:
                    field_attrs['name']=field_name
                """

                #   Extract form attributes for further use below
                other_attrs = []
                for attr_name in field['attributes']:
                    other_attrs.append({'attr_type': attr_name, 'value': field['attributes'][attr_name]})

                    #   Create dynamic validators to check results if the correct answer has
                    #   been specified by the form author
                    if attr_name == 'correct_answer' and len(field['attributes'][attr_name].strip()) > 0:
                        if field['field_type'] in ['dropdown', 'radio']:
                            value_choices = field['attributes']['options'].split('|')
                            target_value = value_choices[int(field['attributes'][attr_name])]
                        elif field['field_type'] in ['checkboxes']:
                            value_choices = field['attributes']['options'].split('|')
                            target_value = [value_choices[int(index)] for index in field['attributes'][attr_name].split(',')]
                        else:
                            target_value = field['attributes'][attr_name]

                        field_attrs['validators'] = [matches_answer(target_value)]

                if other_attrs:
                    field_attrs.update(self._getAttrs(other_attrs))

                # First, check for link fields
                if cf_cache.isLinkField(field['field_type']):
                    # Get all form fields for this model, if it hasn't already been done
                    link_model = cf_cache.modelForLinkField(field['field_type'])
                    if not link_model:
                        continue
                    if link_model.__name__ not in model_fields_cache:
                        model_fields_cache[link_model.__name__] = {}
                        model_fields_cache[link_model.__name__].update(fields_for_model(link_model, widgets=getattr(link_model, 'link_fields_widgets', None)))

                    model_field = cf_cache.getLinkFieldData(field['field_type'])['model_field']

                    field_is_custom = False
                    if model_field in model_fields_cache[link_model.__name__]:
                        form_field = model_fields_cache[link_model.__name__][model_field]
                    else:
                        #   See if there's a custom field
                        if model_field in custom_fields:
                            form_field = cf_cache.getCustomFieldInstance(model_field, field_name)
                            field_is_custom = True
                        else:
                            raise Exception('Could not find linked field: %s' % model_field)

                    # TODO -> enforce "Required" constraint server-side as well, or trust the client-side code?
                    form_field.__dict__.update(field_attrs)
                    form_field.widget.attrs.update({'class': ''})
                    if form_field.required:
                        # Add a class 'required' to the widget
                        form_field.widget.attrs['class'] += 'required '
                        form_field.widget.is_required = True

                    if not field_is_custom:
                        # Add in other classes for validation
                        generic_type = cf_cache.getGenericType(form_field)
                        if 'widget_attrs' in self._field_types[generic_type] and 'class' in self._field_types[generic_type]['widget_attrs']:
                            form_field.widget.attrs['class'] += self._field_types[generic_type]['widget_attrs']['class']

                    # Adding to field list
                    self.fields.append([field_name, form_field])
                    curr_fieldset[1]['fields'].append(field_name)
                    continue

                # Generic field
                widget_attrs = {}
                if 'attrs' in self._field_types[field['field_type']]:
                    field_attrs.update(self._field_types[field['field_type']]['attrs'])
                if 'widget_attrs' in self._field_types[field['field_type']]:
                    widget_attrs.update(self._field_types[field['field_type']]['widget_attrs'])
                typeMap = self._field_types[field['field_type']]['typeMap']

                # Setting classes required for front-end validation
                if field['required']:
                    widget_attrs['class'] += ' required'
                if 'min_value' in field_attrs:
                    widget_attrs['min'] = field_attrs['min_value']
                if 'max_value' in field_attrs:
                    widget_attrs['max'] = field_attrs['max_value']
                if 'min_length' in field_attrs:
                    widget_attrs['minlength'] = field_attrs['min_length']
                if 'max_length' in field_attrs:
                    widget_attrs['maxlength'] = field_attrs['max_length']
                if 'min_words' in field_attrs:
                    widget_attrs['minWords'] = field_attrs['min_words']
                if 'max_words' in field_attrs:
                    widget_attrs['maxWords'] = field_attrs['max_words']

                # For combo fields, classes need to be passed in to the field
                if field['field_type'] in self._combo_fields:
                    field_attrs.update(widget_attrs)

                # Setting the queryset for a courses field
                if field['field_type'] == 'courses':
                    if self.form.link_type == 'program' or self.form.link_type == 'Program':
                        field_attrs['queryset'] = Program.objects.get(pk = self.form.link_id).classsubject_set.all()

                # Initializing widget
                if field_attrs['widget'] is not None:
                    try:
                        field_attrs['widget'] = field_attrs['widget'](attrs = widget_attrs)
                    except KeyError:
                        pass

                self.fields.append([field_name, typeMap(**field_attrs) ])
                curr_fieldset[1]['fields'].append(field_name)

            self.fieldsets.append(tuple(curr_fieldset))

    def getInitialLinkDataFields(self):
        """
        Returns a dict mapping fields to be pre-populated with the corresponding model and model-field
        """
        initial = {}
        for section in self.page:
            for field in section:
                ftype = field['field_type']
                if cf_cache.isLinkField(ftype):
                    field_name = 'question_%d' % field['id']
                    initial[field_name] = {'model': cf_cache.modelForLinkField(ftype)}
                    """
                    if 'combo' in link_fields[ftype]:
                        initial[field_name]['field']=[]
                        for f in link_fields[ftype]['combo']:
                            initial[field_name]['field'].append(link_fields[f]['model_field'])
                    else:
                    """
                    model_field = cf_cache.getLinkFieldData(ftype)['model_field']
                    if cf_cache.isCompoundLinkField(initial[field_name]['model'], model_field):
                        model_field = cf_cache.getCompoundLinkFields(initial[field_name]['model'], model_field)
                    initial[field_name]['model_field'] = model_field
        return initial

    def getForm(self):
        """
        Returns the BetterForm class for the current page
        """
        _form_name = "Page_%d_%d" % (self.form.id, self.seq)

        if not self.fields:
            self._getFields()
        class Meta:
            fieldsets = self.fieldsets
        attrs = {'Meta': Meta}
        attrs.update(OrderedDict(self.fields))

        page_form = type(_form_name, (BaseCustomForm,), attrs)
        return page_form


class FormStorage(FileSystemStorage):
    """
    The Storage sublass used to temporarily store submitted files.
    """
    pass

class ComboForm(SessionWizardView):
    """
    The WizardView subclass used to implement the FormWizard
    """

    # TODO ->   The WizardView doesn't delete old files if the
    #           form doesn't submit successfully. Need to figure
    #           out how to perform this cleanup.
    #           vdugar, 4/10/12

    template_name = 'customforms/form.html'
    curr_request = None
    form_handler = None
    form = None
    file_storage = FormStorage()

    def get_context_data(self, form, **kwargs):
        """
        Override the existing method to add in additional
        context data such as the form's title and description
        """

        context = super(ComboForm, self).get_context_data(form=form, **kwargs)
        context.update({
                        'form_title': self.form.title,
                        'form_description': self.form.description,
            })

        return context

    def done(self, form_list, **kwargs):
        data = {}
        dyn = DMH(form=self.form)
        dynModel = dyn.createDynModel()
        fields = dict(dyn.fields)
        link_models_cache = {}

        # Plonking in user_id if the form is non-anonymous
        if not self.form.anonymous:
            data['user'] = self.curr_request.user

        # Populating data with the values that need to be inserted
        for form in form_list:
            for k,v in form.cleaned_data.items():
                # Check for only_fkey link models first
                if k.split('_')[1] in cf_cache.only_fkey_models:
                    data[k] = v
                    continue

                field_id = int(k.split("_")[1])
                ftype = fields[field_id]

                # Now check for link fields
                if cf_cache.isLinkField(ftype):
                    model = cf_cache.modelForLinkField(ftype)
                    if model.__name__ not in link_models_cache:
                        link_models_cache[model.__name__] = {'model': model, 'data': {}}
                        pre_instance = self.form_handler.getInstanceForLinkField(k, model)
                        if pre_instance is not None:
                            link_models_cache[model.__name__]['instance'] = pre_instance
                        else:
                            link_models_cache[model.__name__]['instance'] = getattr(model, 'cf_link_instance')(self.curr_request)
                    ftype_parts = ftype.split('_')
                    if len(ftype_parts) > 1 and cf_cache.isCompoundLinkField(model, '_'.join(ftype_parts[1:])):
                        #   Try to match a model field to the last part of the key we have.
                        partial_field_name = str(field_id).join(k.split(str(field_id))[1:]).lstrip('_')
                        target_fields = cf_cache.getCompoundLinkFields(model, '_'.join(ftype_parts[1:]))
                        for f in target_fields:
                            if f.endswith(partial_field_name):
                                model_field = f
                                break
                    else:
                        model_field = cf_cache.getLinkFieldData(ftype)['model_field']
                    link_models_cache[model.__name__]['data'].update({model_field: v})
                else:
                    data[k] = v

        # Create/update instances corresponding to link fields
        # Also, populate 'data' with foreign-keys that need to be inserted into the response table
        for k,v in link_models_cache.items():
            if v['instance'] is not None:
                # TODO-> the following update won't work for fk fields.
                v['instance'].__dict__.update(v['data'])
                v['instance'].save()
                curr_instance = v['instance']
            else:
                try:
                    new_instance = v['model'].objects.create(**v['data'])
                except:
                    # show some error message
                    pass
            if v['instance'] is not None:
                data['link_%s' % v['model'].__name__] = v['instance']

        # Saving response
        initial_keys = data.keys()
        for key in initial_keys:
            #   Check that we didn't already handle this value as a linked field
            if key.split('_')[0] in cf_cache.link_fields:
                del data[key]
            #   Check that this value didn't come from a dummy field
            if key.split('_')[0] == 'question' and generic_fields[fields[int(key.split('_')[1])]]['typeMap'] == DummyField:
                del data[key]
        dynModel.objects.create(**data)
        return HttpResponseRedirect('/customforms/success/%d/' % self.form.id)

    def render_to_response(self, context):
        #   Override rendering function to use our context processors.
        from esp.utils.web import render_to_response as render_to_response_base
        return render_to_response_base(self.template_name, self.request, context)

    def get_form_prefix(self, step, form):
        """
        The WizardView implements a form prefix for each step. Setting the prefix to an empty string,
        as the field name is already unique
        """
        return ''


class FormHandler:
    """
    Handles creation of a form (single page or multi-page). Uses Django's form wizard.
    """

    def __init__(self, form, request, user=None):
        self.form = form
        self.request = request
        self.wizard = None
        self.user = user
        self.handlers = []

    def __marinade__(self):
        """
        Implemented for caching convenience
        """
        return "fh"

    @cache_function
    def _getFormMetadata(self, form):
        """
        Returns the metadata for this form. Gets everything in one large query, and then organizes the information.
        Used for rendering.
        """
        fields = Field.objects.filter(form=form).order_by('section__page__seq', 'section__seq', 'seq').values('id', 'field_type',
                'label', 'help_text', 'required', 'seq',
                'section__title', 'section__description', 'section__seq', 'section__id',
                'section__page__id', 'section__page__seq',
                'attribute__attr_type', 'attribute__value')

        # Generating the 'master' struct for metadata
        # master_struct is a nested list of the form (pages(sections(fields)))
        field_dict = {}
        master_struct = []
        for field in fields:
            try:
                page = master_struct[field['section__page__seq']]
            except IndexError:
                page = []
                master_struct.append(page)
            try:
                section = page[field['section__seq']]
            except IndexError:
                section = []
                page.append(section)
            if field['id'] not in field_dict:
                section.append(field)
                field_dict[field['id']] = field
                field_dict[field['id']]['attributes'] = {field['attribute__attr_type']: field['attribute__value']}
            else:
                field_dict[field['id']]['attributes'].update({field['attribute__attr_type']: field['attribute__value']})
        return master_struct
    _getFormMetadata.depend_on_row('customforms.Field', lambda field: {'form': field.form})
    _getFormMetadata.depend_on_row('customforms.Attribute', lambda attr: {'form': attr.field.form})
    _getFormMetadata.depend_on_row('customforms.Section', lambda section: {'form': section.page.form})
    _getFormMetadata.depend_on_row('customforms.Page', lambda page: {'form': page.form})

    def _getHandlers(self):
        """
        Returns a list of CustomFormHandler instances corresponding to each page
        """
        master_struct = self._getFormMetadata(self.form)
        for page in master_struct:
            self.handlers.append(CustomFormHandler(page=page, form=self.form))
        return self.handlers

    def _getFormList(self):
        """
        Returns the list of BetterForm sub-classes corresponding to each page
        """
        form_list = []
        if not self.handlers:
            self._getHandlers()
        for handler in self.handlers:
            form_list.append(handler.getForm())
        return form_list

    def getInstanceForLinkField(self, field_name, model):
        """
        Checks the link_id attribute for this field, and returns the corresponding model
        instance if one has been specified by the form creator.
        Returns None otherwise.
        """
        master_struct = self._getFormMetadata(self.form)
        field_id = int(field_name.split("_")[1])
        for page in master_struct:
            for section in page:
                for field in section:
                    if field['id'] == field_id:
                        # TODO I think this needs to be changed to
                        # iterate through field['attributes'] instead
                        # (see commit message), but I'm not familiar
                        # enough with this function or when/how/on what
                        # fields it is called to be confident enough to
                        # make this change myself at this time.
                        # -jmoldow, 2013-01-24
                        if field['attribute__value'] == "-1" or not field['attribute__value']:
                            return None
                        else:
                            instance_id = int(field['attribute__value'])
                            instance = model.objects.get(pk = instance_id)
                            return instance

    def _getInitialData(self, form, user):
        """
        Returns the initial data, if any, for this form according to the format that FormWizard expects.
        """
        initial_data = {}
        link_models_cache = {} # Stores data from a particular model
        """
        if form.anonymous or user is None:
            return {}
        """
        if not self.handlers:
            self._getHandlers()
        for handler in self.handlers:
            initial = handler.getInitialLinkDataFields()
            if initial:
                initial_data[handler.seq] = {}
                for k,v in initial.items():
                    if v['model'].__name__ not in link_models_cache:
                        # Get the corresponding instance, and get its values
                        # First, check for pre-specified instances
                        pre_instance = self.getInstanceForLinkField(k, v['model'])
                        if pre_instance is not None:
                            link_models_cache[v['model'].__name__] = pre_instance
                        else:
                            # Get the instance from the model method that should have been defined
                            link_models_cache[v['model'].__name__] = getattr(v['model'], 'cf_link_instance')(self.request)
                        if link_models_cache[v['model'].__name__] is not None:
                            link_models_cache[v['model'].__name__] = link_models_cache[v['model'].__name__].__dict__
                    if link_models_cache[v['model'].__name__] is not None:
                        if not isinstance(v['model_field'], list):
                            # Simple field
                            initial_data[handler.seq].update({ k:link_models_cache[v['model'].__name__][v['model_field']] })
                        else:
                            # Compound field. Needs to be passed a list of values.
                            initial_data[handler.seq].update({k:[link_models_cache[v['model'].__name__][val] for val in v['model_field'] ]})
        return initial_data

    def get_initial_data(self, initial_data=None):
        if initial_data is None:
            initial_data = {}
        linked_initial_data = self._getInitialData(self.form, self.user)
        combined_initial_data = {}
        for i in range(len(self.handlers)):
            combined_initial_data[i] = {}
            if i in linked_initial_data:
                combined_initial_data[i].update(linked_initial_data[i])
            if i in initial_data:
                combined_initial_data[i].update(initial_data[i])
        return combined_initial_data

    def get_wizard(self, initial_data=None):
        combined_initial_data = self.get_initial_data(initial_data)
        return ComboForm(   form_list = self._getFormList(),
                            initial_dict = combined_initial_data,
                            form_handler = self,
                            form = self.form)

    def get_wizard_view(self, initial_data=None):
        """
        Calls the as_view() method of ComboForm with the appropriate arguments and returns the response
        """

        # First, let's get the initial data for all the steps
        combined_initial_data = self.get_initial_data(initial_data)

        # Now, return the appropriate response
        return ComboForm.as_view(
                                self._getFormList(),
                                initial_dict = combined_initial_data,
                                curr_request = self.request,
                                form_handler = self,
                                form = self.form)(self.request)

    def deleteForm(self):
        """
        Deletes all information relating to the form from the db.
        Also removes the response table
        """
        dyn = DMH(form=self.form)
        dyn.deleteTable()
        self.form.delete() # Cascading Foreign Keys should take care of everything

    # IMPORTANT -> *NEED* TO REGISTER A CACHE DEPENDENCY ON THE RESPONSE MODEL
    # @cache_function
    def getResponseData(self, form):
        """
        Returns the response data for this form, along with the questions
        """
        dmh = DMH(form=form)
        dyn = dmh.createDynModel()
        response_data = {'questions': [], 'answers': []}
        responses = dyn.objects.all().order_by('id').values()
        fields = Field.objects.filter(form=form).order_by('section__page__seq', 'section__seq', 'seq').values('id', 'field_type', 'label')

        # Let's first do a bit of introspection to figure out
        # what the linked models are, and what values need to be added to the
        # response data from these linked models.
        # And since we're already iterating over fields,
        # let's also set the questions in the process.
        add_fields = {}

        # Add in the user column if form is not anonymous
        if not form.anonymous:
            response_data['questions'].append(['user_id', 'User ID', 'fk'])
            response_data['questions'].append(['user_display', 'User', 'textField'])
            response_data['questions'].append(['user_email', 'User email', 'textField'])
            response_data['questions'].append(['username', 'Username', 'textField'])

        # Add in the column for link fields, if any
        if form.link_type != "-1":
            only_fkey_model = cf_cache.only_fkey_models[form.link_type]
            response_data['questions'].append(["link_%s_id" % only_fkey_model.__name__, form.link_type, 'fk'])
        else:
            only_fkey_model = None

        for field in fields:
            # I'll do a lot of merging here later
            qname = 'question_%d' % field['id']
            ftype = field['field_type']
            if cf_cache.isLinkField(ftype):
                # Let's grab the model first
                model = cf_cache.modelForLinkField(ftype)

                # Now let's see what fields need to be set
                add_fields[qname] = [model, cf_cache.getLinkFieldData(ftype)['model_field']]
                response_data['questions'].append([qname, field['label'], ftype])
                # Include this field only if it isn't a dummy field
            elif generic_fields[ftype]['typeMap'] is not DummyField:
                response_data['questions'].append([qname, field['label'], ftype])

        users = ESPUser.objects.in_bulk(map(lambda response: response['user_id'], responses))

        # Now let's set up the responses
        for response in responses:
            link_instances_cache={}

            # Add in user if form is not anonymous
            if not form.anonymous and response['user_id']:
                user = users[response['user_id']]
                response['user_id'] = unicode(response['user_id'])
                response['user_display'] = user.name()
                response['user_email'] = user.email
                response['username'] = user.username

            # Add in links
            if only_fkey_model is not None:
                if only_fkey_model.objects.filter(pk=response["link_%s_id" % only_fkey_model.__name__]).exists():
                    inst = only_fkey_model.objects.get(pk=response["link_%s_id" % only_fkey_model.__name__])
                else: inst = None
                response["link_%s_id" % only_fkey_model.__name__] = unicode(inst)

            # Now, put in the additional fields in response
            for qname, data in add_fields.items():
                if data[0].__name__ not in link_instances_cache:
                    if data[0].objects.filter(pk=response["link_%s_id" % data[0].__name__]).exists():
                        link_instances_cache[data[0].__name__] = data[0].objects.get(pk=response["link_%s_id" % data[0].__name__])
                    else:
                        link_instances_cache[data[0].__name__] = None

                if cf_cache.isCompoundLinkField(data[0], data[1]):
                    if link_instances_cache[data[0].__name__] is None:
                        response[qname] = []
                    else:
                        response[qname] = [link_instances_cache[data[0].__name__].__dict__[x] for x in cf_cache.getCompoundLinkFields(data[0], data[1])]
                else:
                    if link_instances_cache[data[0].__name__] is None:
                        response[qname]=''
                    else:
                        response[qname] = link_instances_cache[data[0].__name__].__dict__[data[1]]

        # Add responses to response_data
        response_data['answers'].extend(responses)

        return response_data
    # getResponseData.depend_on_row('customforms.Field', lambda field: {'form': field.form})

    def getResponseExcel(self):
        """
        Returns the response data as excel data.
        """
        import xlwt
        try:
            from cStringIO import StringIO
        except:
            from StringIO import StringIO

        response_data = self.getResponseData(self.form)
        wbk = xlwt.Workbook()
        sheet = wbk.add_sheet('sheet 1')

        # Adding in styles for the column headers
        style = xlwt.XFStyle()
        font = xlwt.Font()
        font.name = "Times New Roman"
        font.bold = True
        style.font = font

        # write the questions first
        for i in range(0, len(response_data['questions'])):
            sheet.write(0,i, response_data['questions'][i][1], style)

        # Build up a simple dict storing question_name and question_index (=column number)
        ques_cols = {}
        for qid, ques in enumerate(response_data['questions']):
            ques_cols.update({ques[0]: qid})

        # Now writing the answers
        for idx, response in enumerate(response_data['answers']):
            for ques, ans in response.items():
                try:
                    col = ques_cols[ques]
                except KeyError:
                    continue
                # Join together responses from compound fields
                if isinstance(ans, list):
                    write_ans = " ".join(ans)
                else: write_ans = ans
                sheet.write(idx+1, col, write_ans)

        output = StringIO()
        wbk.save(output)
        return output

    def rebuildData(self):
        """
        Returns the metadata so that a form can be re-built in the form builder
        """
        metadata = {
            'title': self.form.title,
            'desc': self.form.description,
            'anonymous': self.form.anonymous,
            'link_type': self.form.link_type,
            'link_id': self.form.link_id,
            'perms': self.form.perms,
            'pages': self._getFormMetadata(self.form)
        }
        return metadata









