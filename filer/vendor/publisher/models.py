# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djangocms_publisher.utils.copying import DEFAULT_COPY_EXCLUDE_FIELDS

from .utils.relations import update_relations, ignore_stuff_to_dict
from .utils.copying import copy_object
from .utils.compat import PARLER_IS_INSTALLED


class PublisherQuerySetMixin(object):
    def publisher_published(self):
        return self.filter(publisher_is_published_version=True)

    def publisher_drafts(self):
        return self.filter(publisher_is_published_version=False)

    def publisher_pending_deletion(self):
        return self.filter(
            publisher_is_published_version=True,
            publisher_deletion_requested=True,
        )

    def publisher_pending_changes(self):
        return self.filter(
            Q(publisher_is_published_version=False) |
            Q(
                publisher_is_published_version=True,
                publisher_draft_version__isnull=False,
            )
        )

    def publisher_draft_or_published_only(self, prefer_drafts=False):
        """
        Returns a queryset that does not return duplicates of the same object
        if there is both a draft and published version.
        only a draft: include the draft
        only a published: include the published
        draft and published: include the published (the other way around if
        prefer_draft=True)

        So shorter version:
         - prefer_draft=False: exclude drafts that have a published version.
         - prefer_draft=True: exclude published versions that have a draft.
        """
        if prefer_drafts:
            return self.filter(
                # draft objects
                Q(publisher_is_published_version=False) |
                # OR published without a draft version
                Q(
                    publisher_is_published_version=True,
                    publisher_draft_version__isnull=True,
                )
            )
        else:
            return self.filter(
                # published objects
                Q(publisher_is_published_version=True) |
                # OR drafts without a published version
                Q(
                    publisher_is_published_version=False,
                    publisher_published_version__isnull=True,
                )
            )

    def publisher_draft_or_published_only_prefer_drafts(self):
        return self.publisher_draft_or_published_only(prefer_drafts=True)

    def publisher_draft_or_published_only_prefer_published(self):
        return self.publisher_draft_or_published_only(prefer_drafts=False)


class PublisherQuerySet(PublisherQuerySetMixin, models.QuerySet):
    pass


class PublisherModelMixin(models.Model):
    publisher_is_published_version = models.BooleanField(
        default=False,
        editable=False,
        db_index=True,
    )
    publisher_published_version = models.OneToOneField(
        to='self',
        blank=True,
        null=True,
        default=None,
        related_name='publisher_draft_version',
        limit_choices_to={'publisher_published_version_id__isnull': True},
        editable=False,
    )
    publisher_published_at = models.DateTimeField(
        blank=True,
        null=True,
        default=None,
        editable=False,
    )
    publisher_deletion_requested = models.BooleanField(
        default=False,
        editable=False,
        db_index=True,
    )

    objects = PublisherQuerySet.as_manager()

    class Meta:
        abstract = True

    publisher_copy_exclude_fields = ()

    def publisher_get_copy_exclude_fields(self):
        return (
            set(DEFAULT_COPY_EXCLUDE_FIELDS) |
            set(self.publisher_copy_exclude_fields)
        )

    # USER OVERRIDABLE METHODS
    def publisher_copy_relations(self, old_obj):
        # At this point the basic fields on the model have all already been
        # copied. Only relations need to be copied now.
        # If this was a django-parler model, the translations will already
        # have been copied. (but without their relations, that is also up to
        # you to do here).
        # Warning:
        # External apps should not have relations to any of the objects
        # copied here manually because the draft version will be deleted.
        # If you don't want that to happen, you'll have to be smart about not
        # deleting and recreating all the related objects and instead update
        # them. But it may not always be possible or straight forward.
        pass

    def publisher_copy_object(self, old_obj, commit=True):
        # TODO: use the id swapping trick (but remember to set
        #       publisher_published_version_id too!)
        copy_object(
            new_obj=self,
            old_obj=old_obj,
            exclude_fields=self.publisher_get_copy_exclude_fields(),
        )
        if commit:
            self.save()
            self.publisher_copy_relations(old_obj=old_obj)

    def publisher_rewrite_ignore_stuff(self, old_obj):
        return {}

    def publisher_can_publish(self):
        assert self.publisher_is_draft_version
        # FOR SUBCLASSES
        # Checks whether the data and all linked data is ready to publish.
        # Raise ValidationError if not.

    def publisher_user_can_publish(self, user):
        # FOR SUBCLASSES
        # Checks whether the user has permissions to publish
        return True
    # /USER OVERRIDABLE METHODS

    @property
    def publisher_is_draft_version(self):
        return not self.publisher_is_published_version

    @property
    def publisher_has_published_version(self):
        if self.publisher_is_published_version:
            return True
        else:
            return bool(self.publisher_published_version_id)

    @cached_property
    def publisher_has_pending_changes(self):
        if self.publisher_is_draft_version:
            return True
        else:
            try:
                # Query! Can probably be avoided by using
                # .select_related('draft') in the queryset.
                return bool(self.publisher_draft_version)
            except ObjectDoesNotExist:
                return False

    @property
    def publisher_has_pending_deletion_request(self):
        return self.publisher_is_published_version and self.publisher_deletion_requested

    @transaction.atomic
    def publisher_create_draft(self):
        assert self.publisher_is_published_version
        if self.publisher_has_pending_deletion_request:
            self.publisher_discard_requested_deletion()
        # TODO: Get draft without a query by copying in memory)
        #       Simply setting pk and id was causing weird problems (probably
        #       related to django-parler).
        draft = self._meta.model.objects.get(id=self.id)
        draft.pk = None
        draft.id = None
        draft.publisher_is_published_version = False
        draft.publisher_published_version = self
        # If save() was called even though a draft already exists,
        # we'll get the db error here.
        draft.save()
        draft.publisher_copy_relations(old_obj=self)
        return draft

    def publisher_get_or_create_draft(self):
        if self.publisher_is_draft_version:
            return self, False
        elif (
            self.publisher_is_published_version and
            self.publisher_has_pending_changes
        ):
            return self.publisher_draft_version, False
        elif (
            self.publisher_is_published_version and
            not self.publisher_has_pending_changes
        ):
            return self.publisher_create_draft(), True

    @transaction.atomic
    def publisher_discard_draft(self):
        assert self.publisher_is_draft_version
        old_obj = self
        new_obj = self.publisher_published_version
        update_relations(
            old_obj=old_obj,
            new_obj=new_obj,
            exclude=ignore_stuff_to_dict(self.publisher_rewrite_ignore_stuff(old_obj=old_obj))
        )
        self.delete()

    @transaction.atomic
    def publisher_publish(self, validate=True):
        assert self.publisher_is_draft_version
        draft = self
        if validate:
            draft.publisher_can_publish()
        now = timezone.now()
        existing_published = draft.publisher_published_version
        if not existing_published:
            # This means there is no existing published version. So we can just
            # make this draft the published version.
            # As a nice side-effect all existing ForeignKeys pointing to this
            # object will now be automatically pointing the published version.
            # Win-win.
            draft.publisher_is_published_version = True
            draft.publisher_published_at = now
            draft.save()
            return draft

        # There is an existing live version:
        # * update the live version with the data from the draft
        published = draft.publisher_published_version
        published.publisher_published_at = now
        published.publisher_copy_object(old_obj=self)
        # * find any other objects still pointing to the draft version and
        #   switch them to the live version. (otherwise cascade or set null
        #   would yield unexpected results)
        update_relations(
            old_obj=draft,
            new_obj=published,
            exclude=ignore_stuff_to_dict(self.publisher_rewrite_ignore_stuff(old_obj=draft))
        )
        # * Delete draft (self)
        draft.delete()
        # Refresh from db to get the latest version without any cached stuff.
        # refresh_from_db() does not work in some cases because parler
        # caches translations at _translations_cache wich may remain with stale
        # data.
        published = self._meta.model.objects.get(pk=published.pk)
        return published

    @transaction.atomic
    def publisher_request_deletion(self):
        assert (
            self.publisher_is_draft_version and self.publisher_has_published_version or
            self.publisher_is_published_version
        )
        # shortcut to be able to request_deletion on a draft. Preferrably this
        # should be done on the live object.
        if self.publisher_is_draft_version:
            return self.publisher_published_version.request_deletion()

        # It is a published object
        published = self
        if self.publisher_has_pending_changes:
            draft = published.publisher_draft_version
        else:
            draft = None

        published.publisher_deletion_requested = True
        published.save(update_fields=['publisher_deletion_requested'])
        if draft:
            draft.delete()
        return published

    @transaction.atomic
    def publisher_discard_requested_deletion(self):
        assert self.publisher_is_published_version
        self.publisher_deletion_requested = False
        self.save(update_fields=['publisher_deletion_requested'])

    @transaction.atomic
    def publisher_publish_deletion(self):
        assert self.publisher_has_pending_deletion_request
        self.delete()
        self.id = None
        return self

    def publisher_get_published_version(self):
        if self.publisher_is_published_version:
            return self
        if self.publisher_published_version_id:
            return self.publisher_published_version
        return None

    def publisher_get_draft_version(self):
        if self.publisher_is_draft_version:
            return self
        if self.publisher_has_pending_changes:
            return self.publisher_draft_version
        return None

    def publisher_available_actions(self, user):
        actions = {}
        if self.publisher_deletion_requested:
            actions['discard_requested_deletion'] = {}
            actions['publish_deletion'] = {}
        if self.publisher_is_draft_version and self.publisher_has_pending_changes:
            actions['publish'] = {}
        if (
            self.publisher_is_draft_version and
            self.publisher_has_pending_changes and
            self.publisher_has_published_version
        ):
            actions['discard_draft'] = {}
        if self.publisher_is_published_version and not self.publisher_has_pending_changes:
            actions['create_draft'] = {}
        if self.publisher_is_published_version and not self.publisher_deletion_requested:
            actions['request_deletion'] = {}
        for action_name, data in actions.items():
            data['name'] = action_name
            if action_name in ('publish', 'publish_deletion'):
                # FIXME: do actual permission check
                data['has_permission'] = user.is_superuser
            else:
                data['has_permission'] = True
        return actions

    def publisher_allowed_actions(self, user):
        return [
            action
            for action, data in self.publisher_available_actions(user).items()
            if data['has_permission']
        ]

    @property
    def publisher_status_text(self):
        if self.publisher_has_pending_deletion_request:
            return _('Pending deletion')
        elif self.publisher_is_draft_version:
            if self.publisher_has_published_version:
                return _('Unpublished changes')
            else:
                return _('Not published')
        return ''

    def publisher_add_status_label(self, label):
        """
        Extra label to be added to the default string representation of objects
        to identify their status.
        """
        status = self.publisher_status_text
        if status:
            return '{} [{}]'.format(label, status.upper())
        else:
            return '{}'.format(label)

    @cached_property
    def publisher_is_parler_model(self):
        if not PARLER_IS_INSTALLED:
            return False
        from parler.models import TranslatableModel
        return isinstance(self, TranslatableModel)

