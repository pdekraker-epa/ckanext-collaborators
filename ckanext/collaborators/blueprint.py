from flask import Blueprint
from flask.views import MethodView

from ckan.common import _, g

import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckan.lib.navl.dictization_functions as dictization_functions
import ckan.logic as logic


def collaborators_read(dataset_id):
    context = {u'model': model, u'user': toolkit.c.user}
    data_dict = {'id': dataset_id}

    try:
        toolkit.check_access(u'dataset_collaborator_list', context, data_dict)
        # needed to ckan_extend package/edit_base.html
        g.pkg_dict = toolkit.get_action('package_show')(context, data_dict)
    except toolkit.NotAuthorized:
        message = 'Unauthorized to read collaborators {0}'.format(dataset_id)
        return toolkit.abort(401, toolkit._(message))
    except toolkit.ObjectNotFound:
        return toolkit.abort(404, toolkit._(u'Resource not found'))

    return toolkit.render('collaborator/collaborators.html')

def collaborator_delete(dataset_id):
    context = {u'model': model, u'user': toolkit.c.user}

    try:
        member_type = toolkit.request.params.get(u'type')
        member_id = toolkit.request.params.get(u'member_id')
    
        toolkit.get_action('dataset_collaborator_delete')(context, {
            'id': dataset_id,
            'type': member_type,
            'member_id': member_id
        })
    except toolkit.NotAuthorized:
        message = u'Unauthorized to delete collaborators {0}'.format(dataset_id)
        return toolkit.abort(401, toolkit._(message))
    except toolkit.ObjectNotFound as e:
        return toolkit.abort(404, toolkit._(e.message))

    if member_type == 'user':
        toolkit.h.flash_success(toolkit._('User removed from collaborators'))
    if member_type == 'org':
        toolkit.h.flash_success(toolkit._('Organization removed from collaborators'))

    return toolkit.redirect_to(u'collaborators.read', dataset_id=dataset_id)

class CollaboratorEditView(MethodView):
    def post(self, dataset_id):
        context = {u'model': model, u'user': toolkit.c.user}

        try:
            form_dict = logic.clean_dict(
                dictization_functions.unflatten(
                    logic.tuplize_dict(
                        logic.parse_params(toolkit.request.form))))

            if form_dict['username']:
                user = toolkit.get_action('user_show')(context, {'id':form_dict['username'] })

                data_dict = {
                    'id': dataset_id,
                    'type': 'user',
                    'member_id': user['id'],
                    'capacity': form_dict['capacity']
                }
                
                toolkit.get_action('dataset_collaborator_create')(context, data_dict)
                toolkit.h.flash_success(toolkit._('User added to collaborators'))

            elif form_dict['organization']:
                org = toolkit.get_action('organization_show')(context, {'id':form_dict['organization'] })

                data_dict = {
                    'id': dataset_id,
                    'type': 'org',
                    'member_id': org['id'],
                    'capacity': form_dict['capacity']
                }
            
                toolkit.get_action('dataset_collaborator_create')(context, data_dict)
                toolkit.h.flash_success(toolkit._('Organization added to collaborators'))

        except dictization_functions.DataError:
            return toolkit.abort(400, _(u'Integrity Error'))
        except toolkit.NotAuthorized:
            message = u'Unauthorized to edit collaborators {0}'.format(dataset_id)
            return toolkit.abort(401, toolkit._(message))
        except toolkit.ObjectNotFound:
            return toolkit.abort(404, toolkit._(u'Resource not found'))
        except toolkit.ValidationError as e:
            toolkit.h.flash_error(e.error_summary)
        
        return toolkit.redirect_to(u'collaborators.read', dataset_id=dataset_id)

    def get(self, dataset_id):
        context = {u'model': model, u'user': toolkit.c.user}
        data_dict = {'id': dataset_id}

        try:
            toolkit.check_access(u'dataset_collaborator_list', context, data_dict)
            # needed to ckan_extend package/edit_base.html
            g.pkg_dict = toolkit.get_action('package_show')(context, data_dict)
        except toolkit.NotAuthorized:
            message = u'Unauthorized to read collaborators {0}'.format(dataset_id)
            return toolkit.abort(401, toolkit._(message))
        except toolkit.ObjectNotFound as e:
            return toolkit.abort(404, toolkit._(u'Resource not found'))

        member_type = toolkit.request.params.get(u'type')
        member_id = toolkit.request.params.get(u'member_id')
        capacity = 'member'

        extra_vars = {
            'type': member_type,
            'capacities': [
                {'name':'editor', 'value': 'editor'},
                {'name':'member', 'value':'member'}
                ],
            'capacity': capacity}

        if member_type and member_id:
            data_dict['member_type'] = member_type        
            collaborators = toolkit.get_action('dataset_collaborator_list')(context, data_dict)
            for c in collaborators:
                if c['member_id'] == member_id :
                    capacity = c['capacity']
            
            if member_type == 'user':
                g.user_dict = toolkit.get_action('user_show')(context, {'id': member_id})
            else:
                g.org_dict = toolkit.get_action('organization_show')(context, {'id': member_id})
                
        if not member_type or member_type == 'org':
            extra_vars['capacities'].append({'name':'inherit', 'value':'inherit'})  

        return toolkit.render('collaborator/collaborator_new.html', extra_vars)


collaborators = Blueprint('collaborators', __name__)

collaborators.add_url_rule(
    rule=u'/dataset/collaborators/<dataset_id>',
    endpoint='read',
    view_func=collaborators_read, methods=['GET',]
    )

collaborators.add_url_rule(
    rule=u'/dataset/collaborators/<dataset_id>/new',
    view_func=CollaboratorEditView.as_view('new'),
    methods=['GET', 'POST',]
    )

collaborators.add_url_rule(
    rule=u'/dataset/collaborators/<dataset_id>/delete',
    endpoint='delete',
    view_func=collaborator_delete, methods=['POST',]
    )
    
