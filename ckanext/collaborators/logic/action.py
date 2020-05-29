import logging
import datetime

from ckan import model as core_model
from ckan import authz
from ckan.plugins import toolkit

from ckanext.collaborators.model import DatasetMember
from ckanext.collaborators.mailer import mail_notification_to_collaborator

log = logging.getLogger(__name__)


ALLOWED_MEMBER_TYPES = ('user', 'org')
ALLOWED_USER_CAPACITIES = ('editor', 'member', 'limited_member')
ALLOWED_ORG_CAPACITIES = ('editor', 'member', 'limited_member', 'inherit')

def dataset_collaborator_create(context, data_dict):
    '''Make a user a collaborator in a dataset.

    If the user is already a collaborator in the dataset then their
    capacity will be updated.

    Currently you must be an Admin on the dataset owner organization to
    manage collaborators.

    :param id: the id or name of the dataset
    :type id: string
    :param user_id: the id or name of the user to add or edit
    :type user_id: string
    :param capacity: the capacity of the membership. Must be one of {}
    :type capacity: string

    :returns: the newly created (or updated) collaborator
    :rtype: dictionary

    '''.format(', '.join(ALLOWED_USER_CAPACITIES))
    model = context.get('model', core_model)


    dataset_id, member_type, member_id, capacity = toolkit.get_or_bust(data_dict,
        ['id', 'type', 'member_id', 'capacity'])
    
    dataset = model.Package.get(dataset_id)
    if not dataset:
        raise toolkit.ObjectNotFound('Dataset not found')

    toolkit.check_access('dataset_collaborator_create', context, data_dict)

    if member_type == 'user' :
    
        user = model.User.get(member_id)
        if not user:
            raise toolkit.ObjectNotFound('User not found')
    
        if capacity not in ALLOWED_USER_CAPACITIES:
            raise toolkit.ValidationError(
                'Capacity must be one of "{}"'.format(', '.join(ALLOWED_USER_CAPACITIES)))
    
        # Check if member already exists
        member = model.Session.query(DatasetMember).\
            filter(DatasetMember.dataset_id == dataset.id).\
            filter(DatasetMember.type == 'user').\
            filter(DatasetMember.member_id == user.id).one_or_none()
        if not member:
            member = DatasetMember(dataset_id=dataset.id, type='user', member_id=user.id)
        member.capacity = capacity
        member.modified = datetime.datetime.utcnow()

        model.Session.add(member)
        model.repo.commit()

        log.info('User {} added as collaborator in dataset {} ({})'.format(
            user.name, dataset.id, capacity))
        
    elif member_type == 'org':
        
        org = model.Group.get(member_id)
        if not org:
            raise toolkit.ObjectNotFound('Organization not found')

        if capacity not in ALLOWED_ORG_CAPACITIES:
            raise toolkit.ValidationError(
                'Capacity must be one of "{}"'.format(', '.join(ALLOWED_ORG_CAPACITIES)))

        # Check if organization already exists
        member = model.Session.query(DatasetMember).\
            filter(DatasetMember.dataset_id == dataset.id).\
            filter(DatasetMember.type == 'org').\
            filter(DatasetMember.member_id == org.id).one_or_none()
        if not member:
            member = DatasetMember(dataset_id=dataset.id, type='org', member_id=org.id)
        member.capacity = capacity
        member.modified = datetime.datetime.utcnow()

        model.Session.add(member)
        model.repo.commit()

        log.info('Organization {} added as collaborator in dataset {} ({})'.format(
            org.name, dataset.id, capacity))
    
    else:
        raise toolkit.ValidationError('user_id or org_id required')


     # mail_notification_to_collaborator(dataset_id, user_id, capacity,
                                            # event='create')
    
    return member.as_dict()


def dataset_collaborator_delete(context, data_dict):
    '''Remove a collaborator from a dataset.

    Currently you must be an Admin on the dataset owner organization to
    manage collaborators.

    :param id: the id or name of the dataset
    :type id: string
    :param user_id: the id or name of the user to remove
    :type user_id: string

    '''
    model = context.get('model', core_model)

    dataset_id, member_type, member_id = toolkit.get_or_bust(data_dict, ['id', 'type', 'member_id'])
    dataset = model.Package.get(dataset_id)
    
    if not dataset:
        raise toolkit.ObjectNotFound('Dataset not found')

    toolkit.check_access('dataset_collaborator_delete', context, data_dict)

    member = model.Session.query(DatasetMember).\
        filter(DatasetMember.dataset_id == dataset.id).\
        filter(DatasetMember.type == member_type).\
        filter(DatasetMember.member_id == member_id).one_or_none()
    
    if member:
        pass
    elif member_type == 'user':
        raise toolkit.ObjectNotFound('User {} is not a collaborator on this dataset'.format(member_id))
    elif member_type == 'org':
        raise toolkit.ObjectNotFound('Organization {} is not a collaborator on this dataset'.format(member_id))
    else:
        raise toolkit.ValidationError('Type must be one of "{}"'.format(', '.join(ALLOWED_MEMBER_TYPES)))
    

    model.Session.delete(member)
    model.repo.commit()

    if member_type == 'user':
        log.info('User {} removed as collaborator from dataset {}'.format(member_id, dataset.id))
    elif member_type == 'org':
        log.info('Organization {} removed as collaborator from dataset {}'.format(member_id, dataset.id))
    
            
    #mail_notification_to_collaborator(dataset_id, user_id, member.capacity,
     #                                   event='delete')

def dataset_collaborator_list(context, data_dict):
    '''Return the list of all collaborators for a given dataset.

    Currently you must be an Admin on the dataset owner organization to
    manage collaborators.

    :param id: the id or name of the dataset
    :type id: string
    :param capacity: (optional) If provided, only users with this capacity are
        returned
    :type capacity: string

    :returns: a list of collaborators, each a dict including the dataset and
        user id, the capacity and the last modified date
    :rtype: list of dictionaries

    '''
    model = context.get('model', core_model)

    dataset_id = toolkit.get_or_bust(data_dict,'id')

    dataset = model.Package.get(dataset_id)
    if not dataset:
        raise toolkit.ObjectNotFound('Dataset not found')

    toolkit.check_access('dataset_collaborator_list', context, data_dict)

    member_type = data_dict.get('type')
    if member_type and member_type not in ALLOWED_MEMBER_TYPES:
        raise toolkit.ValidationError('Capacity must be one of "{}"'.format(', '.join(ALLOWED_MEMBER_TYPES)))
            
    capacity = data_dict.get('capacity')
    if capacity and capacity not in ALLOWED_ORG_CAPACITIES:
        raise toolkit.ValidationError('Capacity must be one of "{}"'.format(', '.join(ALLOWED_ORG_CAPACITIES)))
    
    q = model.Session.query(DatasetMember).\
        filter(DatasetMember.dataset_id == dataset.id)

    if member_type:
        q = q.filter(DatasetMember.type == member_type)

    if capacity:
        q = q.filter(DatasetMember.capacity == capacity)

    members = q.all()

    return [member.as_dict() for member in members]


def dataset_collaborator_list_for_user(context, data_dict):
    '''Return a list of all dataset the user is a collaborator in

    :param id: the id or name of the user
    :type id: string
    :param capacity: (optional) If provided, only datasets where the user has this
        capacity are returned
    :type capacity: 
    :param permission: (optional) If provided, only datasets where the user has a
        capacity with the requested permission are returned
    :type capacity: string

    :returns: a list of datasets, each a dict including the dataset id, the
        capacity and the last modified date
    :rtype: list of dictionaries

    '''
    model = context.get('model', core_model)

    user_id = toolkit.get_or_bust(data_dict,'id')

    user = model.User.get(user_id)
    if not user:
        raise toolkit.ObjectNotFound('User not found')

    toolkit.check_access('dataset_collaborator_list_for_user', context, data_dict)

    member_type = data_dict.get('type')
    if member_type and member_type not in ALLOWED_MEMBER_TYPES:
        raise toolkit.ValidationError('Type must be one of "{}"'.format(', '.join(ALLOWED_MEMBER_TYPES)))

    permission = data_dict.get('permission','manage_group')
    capacity = data_dict.get('capacity')
    if capacity and capacity not in ALLOWED_USER_CAPACITIES:
        raise toolkit.ValidationError('Capacity must be one of "{}"'.format(', '.join(ALLOWED_USER_CAPACITIES)))
    
    
    roles = authz.get_roles_with_permission(permission)
    
    if capacity and capacity not in roles:
        return [] #Incompatability between provided permissions and capacity
        
    if capacity :
        roles = [capacity]

    out = []


    if not member_type or member_type == 'user' :   
        q = model.Session.query(DatasetMember).\
            filter((DatasetMember.type == 'user') & (DatasetMember.member_id == user.id))

        if capacity:
            q = q.filter(DatasetMember.capacity == capacity )
        
        if permission:
            q = q.filter(DatasetMember.capacity.in_( roles) )
        
        members = q.all()
        
        for member in members:
            out.append({
                'dataset_id': member.dataset_id,
                'type': 'user',
                'capacity': member.capacity,
                'modified': member.modified.isoformat(),
            })


    if not member_type or member_type == 'org':

        user_orgs = toolkit.get_action('organization_list_for_user')(context, data_dict={'id': user.id} )

        user_org_ids = [ org['id'] for org in user_orgs]

        q = model.Session.query(DatasetMember).\
            filter(DatasetMember.type == 'org').\
            filter(DatasetMember.member_id.in_( user_org_ids))

        members = q.all()

        for member in members:

            if  member.capacity == 'inherit':
                org = next( user_org for user_org in user_orgs if user_org['id'] == member.member_id )
                capacity = 'editor' if org.capacity == 'admin' else org.capacity
                if capacity in roles:
                    out.append({
                        'dataset_id': member.dataset_id,
                        'type':'org',
                        'capacity': capacity,
                        'modified': member.modified.isoformat(),
                    })

            elif member.capacity in roles:
                out.append({
                    'dataset_id': member.dataset_id,
                    'type':'org',
                    'capacity': member.capacity,
                    'modified': member.modified.isoformat(),
                })

    return out

def dataset_collaborator_list_for_organization(context, data_dict):
    '''Return a list of all dataset the user is a collaborator in

    :param id: the id or name of the user
    :type id: string
    :param capacity: (optional) If provided, only datasets where the user has this
        capacity are returned
    :type capacity: string

    :returns: a list of datasets, each a dict including the dataset id, the
        capacity and the last modified date
    :rtype: list of dictionaries

    '''
    model = context.get('model', core_model)

    org_id = toolkit.get_or_bust(data_dict,'id')

    org = model.Group.get(org_id)
    if not org:
        raise toolkit.ObjectNotFound('Organization not found')

    toolkit.check_access('dataset_collaborator_list_for_organization', context, data_dict)

    capacity = data_dict.get('capacity')
    if capacity and capacity not in ALLOWED_ORG_CAPACITIES:
        raise toolkit.ValidationError(
            'Capacity must be one of "{}"'.format(', '.join(ALLOWED_ORG_CAPACITIES)))
    q = model.Session.query(DatasetMember).\
        filter(DatasetMemberOrganization.org_id == org.id)

    if capacity:
        q = q.filter(DatasetMember.capacity == capacity)

    members = q.all()

    out = []
    for member in members:
        out.append({
            'dataset_id': member.dataset_id,
            'capacity': member.capacity,
            'modified': member.modified.isoformat(),
        })

    return out

