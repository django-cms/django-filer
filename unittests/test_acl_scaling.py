import pytest

from django.contrib.auth import get_user_model

from finder.models.folder import FolderModel
from finder.models.permission import AccessControlEntry, DefaultAccessControlEntry, Privilege


pytestmark = pytest.mark.django_db


@pytest.fixture(params=['inode', 'default'])
def acl_target(request, sub_folder):
    if request.param == 'inode':
        return (
            AccessControlEntry, {'inode': sub_folder.id},
            sub_folder.apply_access_control_lists,
        )
    return (
        DefaultAccessControlEntry, {'folder': sub_folder},
        sub_folder.apply_default_access_control_list,
    )


@pytest.fixture
def many_users():
    User = get_user_model()
    return User.objects.bulk_create([
        User(username=f'principal-{index}', is_staff=True) for index in range(40)
    ])


def acl_payload(entries):
    return [
        {
            'type': 'user' if entry.user_id else 'group' if entry.group_id else 'everyone',
            'principal': entry.user_id or entry.group_id,
            'privilege': entry.privilege,
        }
        for entry in entries
    ]


@pytest.mark.parametrize('input_kind', ['json', 'queryset'])
def test_acl_queries_bounded(acl_target, many_users, django_assert_num_queries, input_kind):
    model, lookup, apply_acl = acl_target
    entries = model.objects.bulk_create([
        model(**lookup, user=user, privilege=Privilege.READ) for user in many_users
    ])
    next_acl = acl_payload(entries) if input_kind == 'json' else model.objects.filter(**lookup)
    expected = 2 if input_kind == 'json' else 3

    with django_assert_num_queries(expected):
        apply_acl(next_acl)

    assert set(model.objects.filter(**lookup).values_list('id', flat=True)) == {entry.id for entry in entries}


def test_acl_matching_is_linear(acl_target, many_users):
    model, lookup, apply_acl = acl_target
    entries = model.objects.bulk_create([
        model(**lookup, user=user, privilege=Privilege.READ) for user in many_users
    ])
    comparisons = 0

    class Principal(int):
        __hash__ = int.__hash__

        def __eq__(self, other):
            nonlocal comparisons
            comparisons += 1
            return super().__eq__(other)

    next_acl = acl_payload(entries)
    for entry in next_acl:
        entry['principal'] = Principal(entry['principal'])

    apply_acl(next_acl)

    # Count principal comparisons rather than relying on machine-dependent timing.
    assert comparisons <= 2 * len(entries)


@pytest.mark.parametrize('input_kind', ['json', 'queryset'])
def test_acl_reconciles_entries(acl_target, staff_users, groups, ambit, input_kind):
    model, lookup, apply_acl = acl_target
    unchanged = model.objects.create(**lookup, group=groups[0], privilege=Privilege.READ)
    updated = model.objects.create(**lookup, user=staff_users[0], privilege=Privilege.READ)
    removed = model.objects.create(**lookup, user=staff_users[1], privilege=Privilege.READ)
    source = FolderModel.objects.create(parent=ambit.root_folder, name='ACL source')
    source_lookup = {'inode': source.id} if model is AccessControlEntry else {'folder': source}
    entries = model.objects.bulk_create([
        model(**source_lookup, group=groups[0], privilege=Privilege.READ),
        model(**source_lookup, user=staff_users[0], privilege=Privilege.FULL),
        model(**source_lookup, group=groups[1], privilege=Privilege.READ_WRITE),
        model(**source_lookup, privilege=Privilege.READ),
    ])
    next_acl = acl_payload(entries) if input_kind == 'json' else model.objects.filter(**source_lookup)

    apply_acl(next_acl)

    actual = model.objects.filter(**lookup)
    assert set(actual.values_list('user_id', 'group_id', 'privilege')) == {
        (None, groups[0].id, Privilege.READ),
        (staff_users[0].id, None, Privilege.FULL),
        (None, groups[1].id, Privilege.READ_WRITE),
        (None, None, Privilege.READ),
    }
    assert actual.filter(id=unchanged.id).exists()
    assert actual.filter(id=updated.id).exists()
    assert not actual.filter(id=removed.id).exists()

    apply_acl([] if input_kind == 'json' else model.objects.none())
    assert not model.objects.filter(**lookup).exists()
    assert model.objects.filter(**source_lookup).count() == len(entries)
