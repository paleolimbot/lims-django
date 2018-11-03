
import re

from django.core.exceptions import FieldError
from django.http import QueryDict
from django.core.paginator import Paginator
from django.db.models import Q, F, Case, When, prefetch_related_objects, Func, Max, Min
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.template.loader import get_template

from lims import widgets

_RE_TARGET = re.compile('^[A-Za-z0-9_]*$')
_RE_TARGET_FIRST = re.compile(r'^([A-Za-z0-9_]+)__(.*)')


class IsNull(Func):
    function = None
    template = '%(expressions)s IS NULL'


def _get_value(obj, target):
    if target is None:
        return None
    elif callable(target):
        return target(obj)

    target_match = _RE_TARGET_FIRST.match(target)
    if target_match:
        this_target = target_match.group(1)
        next_target = target_match.group(2)
    else:
        this_target = target
        next_target = None

    if not this_target:
        return obj
    elif hasattr(obj, this_target):
        value = getattr(obj, this_target)
        if callable(value):
            value = value()
    elif hasattr(obj, 'tags'):
        tag_qs = obj.tags.filter(key__slug=this_target)
        if tag_qs:
            value = tag_qs[0]
        else:
            value = None
    else:
        value = None

    if next_target:
        return _get_value(value, next_target)
    else:
        return value


class DataViewField:

    def __init__(self, slug, target=None, label=None, sortable=False, queryable=(), output_widget=None):
        self.sortable = sortable
        self.queryable = queryable
        self.slug = str(slug)
        self.target = target if target is not None else self.slug
        self.label = label
        self.output_widget = output_widget if output_widget is not None \
            else widgets.resolve_output_widget('IdentityOutput')

    def validate(self):
        if not callable(self.target) and not _RE_TARGET.match(self.target):
            raise ValueError('Invalid target: "%s"' % self.target)

    def prepare_queryset(self, queryset):
        return queryset

    def sort_by(self, queryset, ascending=True):
        if not self.sortable:
            return queryset

        previous_sort = queryset.query.order_by
        previous_sort = [] if not previous_sort else previous_sort

        if ascending:
            return queryset.order_by(*previous_sort, self.target)
        else:
            return queryset.order_by(*previous_sort, '-' + str(self.target))

    def get_values_iter(self, queryset, context=None):
        target = self.target
        try:
            # TODO: this currently fails every time, because what's getting passed in is a page,
            # not a queryset
            value_qs = queryset.values_list(target, flat=True)
            for obj, value in zip(queryset, value_qs):
                yield self.bind(obj, value, context=context)
        except (FieldError, AttributeError):
            for obj in queryset:
                try:
                    yield self.bind(obj, _get_value(obj, target), context=context)
                except Exception as e:
                    yield self.bind(obj, None, context=context)

    def bind(self, obj, value, context=None):
        return {
            'object': obj,
            'slug': self.slug,
            'target': self.target,
            'label': self.label,
            'value': value,
            'output': self.output_widget.render(value, context=context)
        }


class ModelField(DataViewField):

    def __init__(self, slug, **kwargs):
        defaults = {
            'sortable': True,
            'queryable': ('exact', 'iexact', 'contains', 'icontains', 'gt', 'lt', 'gte', 'lte',
                          'year', 'month', 'day', 'range', 'regex', 'iregex')
        }
        defaults.update(**kwargs)
        super().__init__(slug, **defaults)


class ModelLinkField(ModelField):

    def __init__(self, slug, **kwargs):
        self.link = kwargs.pop('link', 'get_absolute_url')
        super().__init__(slug, **kwargs)

    def bind(self, obj, value, context=None):
        vals = super().bind(obj, value, context=None)
        output = vals['output']
        if output:
            vals['output'] = format_html('<a href="{}">{}</a>', _get_value(obj, self.link), output)
        return vals


class TermField(DataViewField):
    tag_fields = ['comment', 'created', 'id', 'key_id', 'modified', 'numeric_value',
                  'numeric_value_autoset', 'object_id', 'user_id', 'value']

    def __init__(self, term, **kwargs):
        defaults = {
            'slug': term.slug,
            'label': term.name,
            'target': None,
            'sortable': True,
            'queryable': ()
        }
        defaults.update(**kwargs)
        self.term = term
        slug = defaults.pop('slug')
        super().__init__(slug, **defaults)

    def _case_when(self, target, aggregation=Max):
        return aggregation(Case(When(Q(tags__key=self.term), then=F(target))))

    def sort_by(self, queryset, ascending=True):
        if not self.sortable:
            return queryset

        previous_sort = queryset.query.order_by
        previous_sort = [] if not previous_sort else previous_sort

        # tags get sorted by existence, with numerics sorted in front of non-numerics
        dummy_name = '_case_when_' + self.slug
        numeric_dummy_name = dummy_name + '_numeric'
        is_numeric_dummy_name = dummy_name + '_is_numeric'
        null_dummy_name = dummy_name + '_null'

        aggregator = Min if ascending else Max
        annotate_args = {
            dummy_name: self._case_when('tags__value', aggregator),
            numeric_dummy_name: self._case_when('tags__numeric_value', aggregator),
            is_numeric_dummy_name: IsNull(numeric_dummy_name),
            null_dummy_name: IsNull(dummy_name)
        }

        queryset = queryset.annotate(**annotate_args)
        if ascending:
            return queryset.order_by(
                *previous_sort, null_dummy_name, is_numeric_dummy_name, numeric_dummy_name, dummy_name
            )
        else:
            return queryset.order_by(
                *previous_sort, null_dummy_name, '-' + is_numeric_dummy_name, '-' + numeric_dummy_name,
                '-' + dummy_name
            )

    def get_values_iter(self, queryset, context=None):
        prefetch_related_objects(queryset, 'tags')
        for obj in queryset:
            tags = obj.tags.filter(key=self.term)
            # TODO: support multiple tags
            tag = tags[0] if tags else None
            yield self.bind(obj, tag, context=context)

    def bind(self, obj, value, context=None):
        return {
            'object': obj,
            'slug': self.slug,
            'target': self.target,
            'label': self.label,
            'value': value,
            'output': self.output_widget.render(value.value if value else None, context=context)
        }


class DataView:
    widget_template = 'lims/data_view/widget.html'
    actions_template = 'lims/data_view/actions.html'
    table_template = 'lims/data_view/table.html'
    header_template = 'lims/data_view/header.html'
    rows_template = 'lims/data_view/rows.html'
    paginator_template = 'lims/data_view/paginator.html'

    def __init__(self, *extra_fields, name='default', actions=(), default_limit=10, default_order=('-modified', )):
        self.name = str(name)
        self.actions = actions
        self.default_limit = default_limit
        self.default_order = default_order

        if hasattr(self, 'fields'):
            fields = list(self.fields)
        else:
            fields = []

        for field in extra_fields:
            fields.append(field)

        for field in fields:
            field.validate()

        self.fields = fields

    def get_field(self, slug):
        for field in self.fields:
            if field.slug == slug:
                return field
        return None

    def prepare_queryset(self, queryset, query_dict=None, user=None):
        for field in self.fields:
            queryset = field.prepare_queryset(queryset)

        return self._paginate(
            self._order(
                self._filter(
                    queryset,
                    query_dict,
                    user=user
                ),
                query_dict,
                user=user
            ),
            query_dict,
            user=user
        )

    def _filter(self, queryset, query_dict=None, user=None):
        search = [f.target for f in self.fields if f.queryable]
        use = ['%s__%s' % (f.target, q) for f in self.fields for q in f.queryable]

        return default_published_filter(
            filter_queryset_for_user(
                query_string_filter(
                    queryset,
                    query_dict,
                    search=search,
                    use=use,
                    prefix=self.name + '_'
                ),
                user=user,
                permission='view'
            ),
            user=user
        )

    def _paginate(self, queryset, query_dict=None, user=None):
        return query_string_paginate(
            queryset,
            query_dict,
            default_limit=self.default_limit,
            prefix=self.name + '_'
        )

    def _order(self, queryset, query_dict, user=None):
        if query_dict is None:
            return queryset.order_by(*self.default_order)
        else:
            order_var = self.name + '_' + 'order_variable'
            order_values = query_dict.getlist(order_var, [])
            if not order_values:
                return queryset.order_by(*self.default_order)

            order_slugs = [re.sub('^-', '', o) for o in order_values]
            order_fields = [self.get_field(slug) for slug in order_slugs]
            for field, order_val in zip(order_fields, order_values):
                if field:
                    ascending = re.match('^-', order_val) is None
                    queryset = field.sort_by(queryset, ascending=ascending)

        return queryset

    def columns(self, queryset, context=None):
        for field in self.fields:
            yield field.get_values_iter(queryset, context=context)

    def rows(self, queryset, context=None):
        for row in zip(*self.columns(queryset, context=context)):
            yield tuple(row)

    def bind(self, queryset, request, *args, **kwargs):
        return BoundDataView(self, queryset, request, *args, **kwargs)


class BoundDataView:

    def __init__(self, dv, queryset, request, context=None, **kwargs):
        self.kwargs = kwargs
        self.dv = dv
        self.context = context
        self.query_dict = request.GET
        self.model = queryset.model
        self.model_name = self.model.__name__
        self.request = request
        self.url = ''  # may be able to get this off of the request
        self.page = dv.prepare_queryset(queryset, self.query_dict, self.request.user)

        self.name = dv.name
        self.fields = list(dv.fields)
        self.actions = list(dv.actions)

        # copy templates to bound view
        for attr in dir(dv):
            if attr.endswith('_template'):
                setattr(self, attr, getattr(dv, attr))

    def header_links(self):
        sort_var = self.dv.name + '_order_variable'
        current_sort = self.query_dict.getlist(sort_var, [])
        for field in self.dv.fields:
            if field.sortable:
                qd = self.query_dict.copy()
                cls = ''
                if field.slug in current_sort:
                    qd[sort_var] = '-' + field.target
                    cls = 'dsc-sort'
                elif '-' + field.slug in current_sort:
                    qd[sort_var] = field.target
                    cls = 'asc-sort'
                else:
                    qd[sort_var] = field.slug
                yield format_html(
                    '<a class="{cls}" href="{url}">{label}</a>',
                    cls=cls,
                    url=self.url + '?' + qd.urlencode(),
                    label=field.label
                )
            else:
                yield field.label

    def rows(self):
        return self.dv.rows(self.page, context=self.context)

    def columns(self):
        return self.dv.columns(self.page, context=self.context)

    def as_table(self):
        return get_template(self.dv.table_template).render({'dv': self})

    def as_rows(self):
        return get_template(self.dv.rows_template).render({'dv': self})

    def as_paginator(self):
        return get_template(self.dv.paginator_template).render({'dv': self})

    def as_widget(self):
        return get_template(self.dv.widget_template).render({'dv': self}, request=self.request)

    def __str__(self):
        return self.as_widget()


class BaseObjectDataViewWidget(DataView):

    def bind(self, queryset, request, *args, **kwargs):
        view_project = kwargs.pop('project', None)

        # need to assign project context
        if view_project is not None:
            queryset = queryset.filter(project=view_project)
            for field in self.fields:
                if field.target == 'user':
                    field.link = lambda obj: reverse_lazy(
                        'lims:project_user_detail',
                        kwargs={'project_id': view_project.pk, 'pk': obj.user.pk}
                    )
        else:
            # add a project field
            self.fields = [
                ModelLinkField(slug='project', label='Project')
            ] + self.fields

        return super().bind(queryset, request, *args, **kwargs)


class SampleDataViewWidget(BaseObjectDataViewWidget):
    fields = [
        ModelLinkField(slug='slug', label='ID'),
        ModelLinkField(
            slug='user', label='User',
            link=lambda obj: reverse_lazy('lims:user_detail', kwargs={'pk': obj.user.pk})
        ),
        ModelField(slug='collected', label='Collected'),
        ModelField(slug='name', label='Name'),
        ModelField(slug='status', label='Status'),
        ModelField(slug='modified', label='Modified')
    ]


class TermDataViewWidget(BaseObjectDataViewWidget):
    fields = [
        ModelLinkField(slug='slug', label='ID'),
        ModelLinkField(
            slug='user', label='User',
            link=lambda obj: reverse_lazy('lims:user_detail', kwargs={'pk': obj.user.pk})
        ),
        ModelField(slug='name', label='Name'),
        ModelField(slug='status', label='Status'),
        ModelField(slug='modified', label='Modified')
    ]


class AttachmentDataViewWidget(BaseObjectDataViewWidget):
    fields = [
        ModelLinkField(slug='slug', label='ID'),
        ModelLinkField(
            slug='user', label='User',
            link=lambda obj: reverse_lazy('lims:user_detail', kwargs={'pk': obj.user.pk})
        ),
        ModelField(slug='name', label='Name'),
        ModelField(slug='modified', label='Modified'),
    ]


class ProjectDataViewWidget(DataView):
    fields = [
        ModelLinkField(slug='slug', label='ID'),
        ModelLinkField(
            slug='user', label='User',
            link=lambda obj: reverse_lazy('lims:user_detail', kwargs={'pk': obj.user.pk})
        ),
        ModelField(slug='name', label='Name'),
        ModelField(slug='modified', label='Modified'),
    ]


class TagDataViewWidget(DataView):
    fields = [
        ModelLinkField(slug='object', label='Object', link='object__get_absolute_url'),
        ModelLinkField(slug='key', label='Term', link='key__get_absolute_url'),
        ModelField(slug='value', label='Value'),
        ModelField(slug='numeric_value', label='Numeric Value'),
        ModelLinkField(
            slug='user', label='User',
            link=lambda obj: reverse_lazy('lims:user_detail', kwargs={'pk': obj.user.pk})
        ),
        ModelField(slug='modified', label='Modified')
    ]

    def bind(self, queryset, request, *args, **kwargs):
        view_project = kwargs.pop('project', None)

        # need to assign project context
        # not filtering because this is not consistent between tag types
        if view_project is not None:
            for field in self.fields:
                if field.target == 'user':
                    field.link = lambda obj: reverse_lazy(
                        'lims:project_user_detail',
                        kwargs={'project_id': view_project.pk, 'pk': obj.user.pk}
                    )

        return super().bind(queryset, request, *args, **kwargs)


def get_widget_class(model):
    if isinstance(model, type):
        model = model.__name__
    if model == 'Sample':
        return SampleDataViewWidget
    elif model == 'Term':
        return TermDataViewWidget
    elif model == 'Attachment':
        return AttachmentDataViewWidget
    elif model == 'Project':
        return ProjectDataViewWidget
    elif model.endswith('Tag'):
        return TagDataViewWidget
    else:
        raise ValueError('Unknown class: ' + model)


def filter_object_queryset_for_user(queryset, user, permission):
    if user and user.is_staff:
        return queryset

    model_name = queryset.model.__name__
    if model_name == 'Project':
        return queryset.filter(
            Q(permissions__user=user) &
            Q(permissions__permission=permission) &
            Q(permissions__model='Project')
        )
    else:
        return queryset.filter(
            Q(project__permissions__user=user) &
            Q(project__permissions__permission=permission) &
            Q(project__permissions__model=model_name)
        )


def filter_tag_queryset_for_user(queryset, user, permission):
    if user and user.is_staff:
        return queryset

    model_name = re.sub(r'Tag$', '', queryset.model.__name__)
    if model_name == 'Project':
        return queryset.filter(
            Q(object__permissions__user=user) &
            Q(object__permissions__permission=permission) &
            Q(object__permissions__model='Project')
        )
    elif model_name == 'SampleTag':
        return queryset.filter(
            Q(object__object__project__permissions__user=user) &
            Q(object__object__project__permissions__permission=permission) &
            Q(object__object__project__permissions__model='Sample')
        )
    else:
        return queryset.filter(
            Q(object__project__permissions__user=user) &
            Q(object__project__permissions__permission=permission) &
            Q(object__project__permissions__model=model_name)
        )


def filter_queryset_for_user(queryset, user, permission):
    model = queryset.model
    if model.__name__.endswith('Tag'):
        return filter_tag_queryset_for_user(queryset, user, permission)
    else:
        return filter_object_queryset_for_user(queryset, user, permission)


def query_string_order(queryset, query_dict, order_var='order_variable', prefix='', default_order_vars=('-modified', ),
                       use=('modified', )):
    if query_dict is None:
        order_values = default_order_vars
    else:
        order_var = prefix + order_var
        order_values = query_dict.getlist(order_var, default_order_vars)
        negative_use = ['-' + used for used in use]
        order_values = [o for o in order_values if o in (list(use) + negative_use)]
        if not order_values:
            order_values = default_order_vars

    return queryset.order_by(*order_values)


def query_string_paginate(queryset, query_dict, page_var='page_number', limit_var='item_limit', prefix='',
                          default_limit=10, max_limit=1000, default_page=1):
    if query_dict is None:
        page = default_page
        limit = default_limit
    else:
        page_var = prefix + page_var
        limit_var = prefix + limit_var
        try:
            page = int(query_dict.get(page_var, default_page))
        except ValueError:
            page = default_page

        try:
            limit = int(query_dict.get(limit_var, default_limit))
        except ValueError:
            limit = default_limit

        if limit > max_limit:
            limit = max_limit

    return Paginator(queryset, per_page=limit).get_page(page)


def query_string_filter(queryset, query_dict, use=(), search=(), search_func="icontains", prefix=''):
    if query_dict is None:
        return queryset

    q = QueryDict(mutable=True)
    if prefix:
        prefix_re = re.compile('^' + prefix)
        for key in query_dict:
            if prefix_re.match(key):
                q.setlist(prefix_re.sub('', key), query_dict.getlist(key))
    else:
        q = query_dict.copy()

    # ignore empty query
    query = q.get('q', '')
    if query and search:
        search_queries = [{field + "__" + search_func: query} for field in search]
        final_q = None
        for search_query in search_queries:
            if final_q is None:
                final_q = Q(**search_query)
            else:
                final_q = Q(**search_query) | final_q
        queryset = queryset.filter(final_q)

    for key in q:
        if key in use:
            # make sure to ignore empty items! they cause errors
            value = q.getlist(key)
            if len(value) == 1:
                filter_args = {key: value[0]}
            else:
                filter_args = {key: [v for v in value if v]}
            queryset = queryset.filter(**{k: v for k, v in filter_args.items() if v})
        else:
            # ignore unwanted query string items
            pass

    return queryset


class UseEverything:
    """
    This is useful for debugging query_string filter, since it allows
    anything to be passed from the query string to filter().
    """

    def __contains__(self, item):
        return item not in ('page', 'q')


def default_published_filter(queryset, user):
    # in list views, published samples show up in everyone's view, but draft samples
    # show up in only the user's view. auto-draft samples never show up in a list view
    # but should show up in the admin view

    model = queryset.model
    if model.__name__.endswith('TagTag'):
        return queryset.filter(
            Q(object__object__status='published') | (Q(object__object__user=user) & Q(object__object__status='draft'))
        )
    elif model.__name__.endswith('Tag'):
        return queryset.filter(Q(object__status='published') | (Q(object__user=user) & Q(object__status='draft')))
    else:
        return queryset.filter(Q(status='published') | (Q(user=user) & Q(status='draft')))
