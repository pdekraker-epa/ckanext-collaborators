import ckan.plugins.toolkit as toolkit

def get_collaborators(package_dict, type=None):
    '''Return collaborators list.
    '''
    context = {'ignore_auth': True} #TODO
    data_dict = {'id': package_dict['id']}
    
    if type:
        data_dict['type'] = type
    
    _collaborators = toolkit.get_action('dataset_collaborator_list')(context, data_dict)
    collaborators = []

    for collaborator in _collaborators:
        collaborators.append([
            collaborator['member_id'],
            collaborator['capacity']            
            ])


    return collaborators


def get_resource_visibility_options():
    return [{'value': 'editor', 'text':'Editor'},
            {'value': 'owner_member', 'text':'Owner Member'},
            {'value': 'member', 'text':'Collaborator Member'},
            {'value': 'package', 'text': 'Match Dataset'}]
