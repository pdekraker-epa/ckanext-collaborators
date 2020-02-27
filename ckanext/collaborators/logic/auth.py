from ckan.plugins import toolkit

import logging

import ckan.model as model

import ckan.logic as logic
from ckan.logic.auth import (get_package_object, get_resource_object)
from ckan.authz import has_user_permission_for_group_or_org
# from ckan.logic.auth.update import package_update as core_package_update
from ckan.logic.auth.get import resource_show as core_resource_show
# from ckan.logic.auth.get import package_show as core_package_show

log = logging.getLogger()

def _auth_collaborator(context, data_dict, message):
    user = context['user']

    dataset = toolkit.get_action('package_show')(
        {'ignore_auth': True}, {'id': data_dict['id']})

    owner_org = dataset.get('owner_org')
    if not owner_org:
        return {'success': False}

    if not has_user_permission_for_group_or_org(
            owner_org, user, 'update_dataset'):
        return {
            'success': False,
            'msg': toolkit._(message) % user}

    return {'success': True}


def dataset_collaborator_create(context, data_dict):
    '''Checks if a user is allowed to add collaborators to a dataset

    The current implementation restricts this ability to Administrators of the
    organization the dataset belongs to.
    '''
    return _auth_collaborator(context, data_dict,
        'User %s not authorized to add members to this dataset')


def dataset_collaborator_delete(context, data_dict):
    '''Checks if a user is allowed to delete collaborators from a dataset

    The current implementation restricts this ability to Administrators of the
    organization the dataset belongs to.
    '''
    return _auth_collaborator(context, data_dict,
        'User %s not authorized to remove members from this dataset')


def dataset_collaborator_list(context, data_dict):
    '''Checks if a user is allowed to list collaborators from a dataset

    The current implementation restricts this ability to Administrators of the
    organization the dataset belongs to.
    '''
    return _auth_collaborator(context, data_dict,
        'User %s not authorized to list members from this dataset')


def dataset_collaborator_list_for_user(context, data_dict):
    '''Checks if a user is allowed to list all datasets a user is a collaborator in

    The current implementation restricts to the own users themselves.
    '''
    user_obj = context.get('auth_user_obj')
    if user_obj and data_dict.get('id') in (user_obj.name, user_obj.id):
        return {'success': True}
    return {'success': False}


# Core overrides
@toolkit.chained_auth_function
def package_update(next_auth, context, data_dict):

    user_name = context['user']
    dataset = get_package_object(context, data_dict)

    datasets = toolkit.get_action('dataset_collaborator_list_for_user')(
        context, {'id': user_name, 'capacity': 'editor'})
    
    if  dataset.id in [d['dataset_id'] for d in datasets]:
        return {'success': True}
        
    return next_auth(context, data_dict)
        

#@toolkit.chained_auth_function
@toolkit.auth_allow_anonymous_access
def resource_show( context, data_dict):

    base_auth = core_resource_show(context, data_dict)
    if not base_auth['success']:
        return base_auth
    
    r = context.pop('resource',False)

    resource_obj = get_resource_object(context, data_dict)
    visibility = resource_obj.extras.get('visibility','package')
    
    if visibility.startswith('editor'):
        required_permission = 'dataset_update'
        require_owner = False
    elif visibility.startswith('owner'):
        required_permission = 'read'
        require_owner = True
    elif visibility.startswith('collaborator'):
        # collaborator member
        required_permission = 'read'
        require_owner = False
    else:
        return {'success': True}

    package_obj = get_package_object(context, {'id': resource_obj.package_id})
    user_name = context['user']

    if has_user_permission_for_group_or_org(package_obj.owner_org, user_name, required_permission):
        return {'success': True}

    if require_owner:
        return {'success': False}

    collaborator_packages = toolkit.get_action('dataset_collaborator_list_for_user')(
        context, {'id': user_name, 'permission': required_permission})

    if package_obj.id in [p['dataset_id'] for p in collaborator_packages]:
        return {'success': True}
    
    return {'success': False}

# @toolkit.auth_allow_anonymous_access
# def resource_view_show(context, data_dict):
    # r = context.pop('resource',False)
    # resource_obj = get_resource_object(context, data_dict)
    # return core_resource_show(context, {'id': resource_obj.id})

# @toolkit.auth_allow_anonymous_access
# def resource_view_list(context, data_dict):
    # resourceObj = model.Resource.get(data_dict['id'])
    # return core_package_show(context, {'id': resourceObj.package_id})

 
