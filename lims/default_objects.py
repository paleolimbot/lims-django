
from .models import Project, ProjectPermission
from django.contrib.auth.models import User


def get_or_create_default_project():
    try:
        return Project.objects.get(slug="default_project")
    except Project.DoesNotExist:
        p = Project.objects.get_or_create(
            name="Default Project",
            slug="default_project"
        )[0]

        for user in User.objects.all():
            add_user_to_default_project(user)

        return p


def add_user_to_default_project(user):
    p = get_or_create_default_project()
    for model in ('Sample', 'Location', 'Attachment', 'Term'):
        ProjectPermission.objects.get_or_create(project=p, user=user, permission='edit', model=model)
        ProjectPermission.objects.get_or_create(project=p, user=user, permission='view', model=model)

    ProjectPermission.objects.get_or_create(project=p, user=user, permission='view', model='Project')
    return user


def get_or_create_user_project(user):
    try:
        return Project.objects.get(slug='user_project_%s' % user.pk)
    except Project.DoesNotExist:
        p = Project.objects.get_or_create(
            name='User Project: %s' % user.username,
            slug='user_project_%s' % user.pk
        )[0]

        for model in ('Sample', 'Location', 'Attachment', 'Term'):
            ProjectPermission.objects.get_or_create(project=p, user=user, permission='edit', model=model)
            ProjectPermission.objects.get_or_create(project=p, user=user, permission='view', model=model)

        ProjectPermission.objects.get_or_create(project=p, user=user, permission='view', model='Project')
        return p


def user_post_save_handler(sender, instance, *args, **kwargs):
    # add to default project
    add_user_to_default_project(instance)

    # add user project (or make sure it exists)
    get_or_create_user_project(instance)
