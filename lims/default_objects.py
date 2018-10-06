
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
            ProjectPermission.objects.get_or_create(project=p, user=user, permission='add')
            ProjectPermission.objects.get_or_create(project=p, user=user, permission='edit')
            ProjectPermission.objects.get_or_create(project=p, user=user, permission='delete')
            ProjectPermission.objects.get_or_create(project=p, user=user, permission='view')

        return p


def get_or_create_user_project(user):
    try:
        return Project.objects.get(slug='user_project_%s' % user.pk)
    except Project.DoesNotExist:
        p = Project.objects.get_or_create(
            name='User Project: %s' % user.username,
            slug='user_project_%s' % user.pk
        )[0]

        ProjectPermission.objects.get_or_create(project=p, user=user, permission='add')
        ProjectPermission.objects.get_or_create(project=p, user=user, permission='edit')
        ProjectPermission.objects.get_or_create(project=p, user=user, permission='delete')
        ProjectPermission.objects.get_or_create(project=p, user=user, permission='view')

        return p


def user_post_save_handler(sender, instance, *args, **kwargs):
    # add to default project
    p = get_or_create_default_project()
    ProjectPermission.objects.get_or_create(project=p, user=instance, permission='add')
    ProjectPermission.objects.get_or_create(project=p, user=instance, permission='edit')
    ProjectPermission.objects.get_or_create(project=p, user=instance, permission='delete')
    ProjectPermission.objects.get_or_create(project=p, user=instance, permission='view')

    # add user project (or make sure it exists)
    get_or_create_user_project(instance)
