''' IMPORTS '''
import traceback
import requests

# Disable insecure warnings
requests.packages.urllib3.disable_warnings()

''' CONSTANTS '''
SCIM_EXTENSION_SCHEMA = "urn:scim:schemas:extension:custom:1.0:user"
USER_NOT_FOUND = "User not found"
USER_FIELDS = 'Name,Email,Region,Location,JobTitle,DirectManager,MobilePhone,TimeZone,username,profile,firstname,' \
              'lastname,state'

# ,C_PrimaryLanguage,C_SecondaryLanguages,C_Company'

'''CLIENT CLASS'''


class Client(BaseClient):
    """
    Client will implement the Clarizen API, and should not contain any Demisto logic.
    Should only do requests and return data.
    """

    def __init__(self, base_url, username, version, password, verify=True, proxy=False, headers=None, auth=None):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.verify = verify
        self.version = version
        self.headers = headers
        self.auth = auth
        self.session = requests.Session()
        self.get_client_token()
        if not proxy:
            self.session.trust_env = False

    def get_client_token(self):

        uri = '/authentication/login'

        params = {
            "userName": self.username,
            "Password": self.password
        }

        res = self.http_request('post', uri, data=None, params=params)
        try:
            res_json = res.json()
            self.headers['content-type'] = 'application/json'
            if res_json.get("sessionId") is not None:
                self.headers['Authorization'] = 'Session ' + res_json.get("sessionId")
            else:
                demisto.info("No session token has been found.")
        except ValueError:
            demisto.info("No response has been found.")

    def http_request(self, method, url_suffix, params=None, data=None):
        full_url = self.base_url + url_suffix

        res = requests.request(
            method,
            full_url,
            verify=self.verify,
            params=params,
            json=data,
            headers=self.headers
        )
        return res

    def get_user_by_id(self, user_type):

        uri = '/data/objects' + user_type
        params = {
            'fields': USER_FIELDS

        }
        return self.http_request(
            method='GET',
            url_suffix=uri,
            params=params
        )

    def get_user_by_email(self, user_type):

        uri = '/data/findUserQuery'
        data = {

            'email': user_type

        }
        return self.http_request(
            method='POST',
            url_suffix=uri,
            data=data
        )

    def get_disabled_user_by_email(self, user_type):

        uri = '/data/Query'
        data = {
            "q": f"SELECT Name FROM User WHERE email='{user_type}'"
        }
        return self.http_request(
            method='POST',
            url_suffix=uri,
            data=data
        )

    def create_user(self, data):

        uri = '/data/objects/User'

        return self.http_request(
            method='PUT',
            url_suffix=uri,
            data=data
        )

    def update_user(self, data, user_id):

        uri = '/data/objects/User/' + user_id

        return self.http_request(
            method='POST',
            url_suffix=uri,
            data=data
        )

    def enable_or_disable_user(self, data):

        uri = '/data/lifecycle'

        return self.http_request(
            method='POST',
            url_suffix=uri,
            data=data
        )

    def build_clarizen_user_profile(self, client, args, scim, custom_mapping):
        parsed_scim_data = map_scim(scim)
        extension_schema = scim.get(SCIM_EXTENSION_SCHEMA)

        manager_id = None

        if extension_schema and extension_schema.get('manageremail') is not None:
            manageremail = extension_schema.get('manageremail')
            user_type = manageremail
            res = client.get_user_by_email(user_type)
            res_json = res.json()
            if not res_json.get('entities'):
                manager_id = ''
            else:
                manager_id = res_json.get('entities')[0].get('id')

            del extension_schema['manageremail']
        clarizen_user = {
            "Username": parsed_scim_data.get('userName'),
            "firstname": parsed_scim_data.get('first_name'),
            "lastname": parsed_scim_data.get('last_name'),
            "Name": parsed_scim_data.get('displayName'),
            "DirectManager": manager_id,
            "Email": parsed_scim_data.get('email'),
            "JobTitle": parsed_scim_data.get('title'),
            "Location": parsed_scim_data.get('city')[0] if (parsed_scim_data.get('city')) else None,
            "Region": parsed_scim_data.get('state')[0] if (parsed_scim_data.get('state')) else None,
            "MobilePhone": parsed_scim_data.get('phone_work')[0] if (parsed_scim_data.get('phone_work')) else None

        }

        if args.get('customMapping'):
            custom_mapping = json.loads(args.get('customMapping'))
        elif custom_mapping:
            custom_mapping = json.loads(custom_mapping)

        if custom_mapping and extension_schema:
            for key, value in custom_mapping.items():
                # key is the attribute name in input scim. value is the attribute name of app profile
                if extension_schema.get(key):
                    clarizen_user[value] = extension_schema.get(key)

        return clarizen_user


class OutputContext:
    """
        Class to build a generic output and context.
    """

    def __init__(self, success=None, active=None, iden=None, username=None, email=None, errorCode=None,
                 errorMessage=None, details=None):
        self.instanceName = demisto.callingContext['context']['IntegrationInstance']
        self.brand = demisto.callingContext['context']['IntegrationBrand']
        self.command = demisto.command().replace('-', '_').title().replace('_', '')
        self.success = success
        self.active = active
        self.iden = iden
        self.username = username
        self.email = email
        self.errorCode = errorCode
        self.errorMessage = errorMessage
        self.details = details
        self.data = {
            "brand": self.brand,
            "instanceName": self.instanceName,
            "success": success,
            "active": active,
            "id": iden,
            "username": username,
            "email": email,
            "errorCode": errorCode,
            "errorMessage": errorMessage,
            "details": details
        }


'''HELPER FUNCTIONS'''


def verify_and_load_scim_data(scim):
    try:
        scim = json.loads(scim)
    except Exception:
        pass
    if type(scim) != dict:
        raise Exception("SCIM data is not a valid JSON")
    return scim


def map_scim(scim):
    try:
        scim = json.loads(scim)
    except Exception:
        pass
    if type(scim) != dict:
        raise Exception('Provided client data is not JSON compatible')
    mapping = {
        "userName": "userName",
        "email": "emails(val.primary && val.primary==true).[0].value",
        "displayName": "displayName",
        "first_name": "name.givenName",
        "last_name": "name.familyName",
        "active": "active",
        "id": "id",
        "address_one": "addresses(val.primary && val.primary==true).streetAddress",
        "address_two": "addresses( !val.primary ).formatted",
        "city": "addresses(val.primary && val.primary==true).locality",
        "country": "addresses(val.primary && val.primary==true).country",
        "phone_home": "phoneNumbers(val.type && val.type=='home').value",
        "phone_mobile": "phoneNumbers(val.type && val.type=='mobile').value",
        "phone_work": "phoneNumbers(val.type && val.type=='work').value",
        "state": "addresses(val.primary && val.primary==true).region",
        'title': "title",
        "zip": "addresses(val.primary && val.primary==true).postalCode",
    }

    parsed_scim = dict()
    for k, v in mapping.items():
        try:
            parsed_scim[k] = demisto.dt(scim, v)
        except Exception:
            parsed_scim[k] = None
    return parsed_scim


'''COMMAND FUNCTIONS'''


def test_module(client, args):
    uri = '/authentication/login'
    params = {
        "userName": client.username,
        "Password": client.password
    }

    res = client.http_request('post', uri, data=None, params=params)
    demisto.info(str(res.url))

    if res.status_code == 200:
        demisto.results('ok')
    else:
        return_error('Error testing [%d] - %s' % (res.status_code, res.text))


def get_user_command(client, args):
    """
        Returning user POST/GET details and status of response.

        Args:   demisto command line argument
        client: Clarizen client

        Returns:
            success : success=True, id, email, login as username, details, active status
            fail : success=False, id, login as username, errorCode, errorMessage, details
    """
    scim = verify_and_load_scim_data(args.get('scim'))
    parsed_scim_data = map_scim(scim)
    user_id = parsed_scim_data.get('id')
    username = parsed_scim_data.get('userName')
    email = parsed_scim_data.get('email')

    if not (user_id or username or email):
        raise Exception('You must provide either the id, username or email of the user')

    if user_id:
        user_type = "/User/" + user_id

    else:
        if username:
            user_type = username
        else:
            user_type = email

        res = client.get_user_by_email(user_type)
        res_json = res.json()
        if not res_json.get('entities'):
            second_res = client.get_disabled_user_by_email(user_type)
            res_json = second_res.json()
        # If the user doesn't exist, a 404 will be returned saying the user doesn't exist.
        if not res_json.get('entities'):
            generic_iam_context_data_list = []
            generic_iam_context = OutputContext(success=False, iden=None, username=None, errorCode=404,
                                                email=None,
                                                errorMessage=USER_NOT_FOUND, details=res_json)
            generic_iam_context_data_list.append(generic_iam_context.data)
            generic_iam_context_dt = f'{generic_iam_context.command}(val.id == obj.id && val.instanceName == ' \
                                     f'obj.instanceName) '
            outputs = {
                generic_iam_context_dt: generic_iam_context_data_list
            }
            readable_output = tableToMarkdown(name='Get Clarizen User:',
                                              t=generic_iam_context_data_list,
                                              headers=["brand", "instanceName", "success", "active", "id", "username",
                                                       "email",
                                                       "errorCode", "errorMessage", "details"],
                                              removeNull=True)
            return (
                readable_output,
                outputs,
                generic_iam_context_data_list
            )

        user_type = res_json.get('entities')[0].get('id')

    res = client.get_user_by_id(user_type)
    res_json = res.json()
    generic_iam_context_data_list = []
    if res.status_code == 200:

        if res_json:
            active = res_json.get('state').get('id')
            active = active.replace('/State/', '')
            if active == 'Active':
                active = True
            if active == 'Disabled':
                active = False
            user_id = res_json.get('id')
            user_id = user_id.replace('/User/', '')
            generic_iam_context = OutputContext(success=True, iden=user_id,
                                                email=res_json.get('Email'),
                                                username=res_json.get('username'), details=res_json,
                                                active=active)
            generic_iam_context_data_list.append(generic_iam_context.data)
        else:
            generic_iam_context = OutputContext(success=False, iden=user_id, username=username, errorCode=404,
                                                email=email,
                                                errorMessage=USER_NOT_FOUND)
            generic_iam_context_data_list.append(generic_iam_context.data)
    else:
        generic_iam_context = OutputContext(success=False, iden=user_id, username=username, email=email,
                                            errorCode=res.status_code,
                                            errorMessage=res_json.get('error', {}).get('message'), details=res_json)
        generic_iam_context_data_list.append(generic_iam_context.data)

    generic_iam_context_dt = f'{generic_iam_context.command}(val.id == obj.id && val.instanceName == obj.instanceName)'
    outputs = {
        generic_iam_context_dt: generic_iam_context_data_list
    }
    readable_output = tableToMarkdown(name='Get Clarizen User:',
                                      t=generic_iam_context_data_list,
                                      headers=["brand", "instanceName", "success", "active", "id", "username", "email",
                                               "errorCode", "errorMessage", "details"],
                                      removeNull=True)
    return (
        readable_output,
        outputs,
        generic_iam_context_data_list
    )


def create_user_command(client, args):
    """
        Create user using PUT to Clarizen API , if Connection to the service is successful.

        Args:   demisto command line argument
        client: Clarizen Client

        Returns:
            success : success=True, id, email, login as username, details, active status
            fail : success=False, id, login as username, errorCod, errorMessage, details
    """

    scim = verify_and_load_scim_data(args.get('scim'))

    custom_mapping = demisto.params().get('customMappingCreateUser')

    clarizen_user = client.build_clarizen_user_profile(client, args, scim, custom_mapping)
    clarizen_user['Username'] = clarizen_user.get('Email')
    new_clarizen_user = {}
    for key, value in clarizen_user.items():
        if not (value is None):
            new_clarizen_user[key] = value

    res = client.create_user(new_clarizen_user)
    res_json = res.json()
    if res.status_code == 200:

        active = True
        result = res_json.get('id')
        user_res = client.get_user_by_id(result)
        user_res_json = user_res.json()
        user_id = result.replace('/User/', '')

        generic_iam_context = OutputContext(success=True, iden=user_id, email=user_res_json.get('Email'),
                                            username=user_res_json.get('username'), details=scim, active=active)
    else:
        generic_iam_context = OutputContext(success=False, errorCode=res.status_code,
                                            errorMessage=res_json.get('error', {}).get('message'), details=res_json)

    generic_iam_context_dt = f'{generic_iam_context.command}(val.id == obj.id && val.instanceName == obj.instanceName)'
    outputs = {
        generic_iam_context_dt: generic_iam_context.data
    }
    readable_output = tableToMarkdown('Create Clarizen User:', t=generic_iam_context.data,
                                      headers=["brand", "instanceName", "success", "active", "id", "username", "email",
                                               "errorCode", "errorMessage", "details"],
                                      removeNull=True
                                      )
    return (
        readable_output,
        outputs,
        generic_iam_context.data
    )


def update_user_command(client, args):
    """
        Update user using POST to Clarizen API , if Connection to the service is successful.

        Args:   demisto command line argument
        client: Clarizen Client

        Returns:
            success : success=True, id, details
            fail : success=False, id, errorCod, errorMessage, details
    """
    old_scim = verify_and_load_scim_data(args.get('oldScim'))
    new_scim = verify_and_load_scim_data(args.get('newScim'))
    custom_mapping = demisto.params().get('customMappingUpdateUser')

    parsed_old_scim = map_scim(old_scim)
    user_id = parsed_old_scim.get('id')

    if not user_id:
        raise Exception('You must provide id of the user')

    clarizen_user = client.build_clarizen_user_profile(client, args, new_scim, custom_mapping)

    new_clarizen_user = {}

    for key, value in clarizen_user.items():
        if not (value is None):
            new_clarizen_user[key] = value
    get_user_id = "/User/" + user_id
    get_user_res = client.get_user_by_id(get_user_id)
    get_user_res_json = get_user_res.json()
    res = client.update_user(new_clarizen_user, user_id)
    res_json = res.json()

    if res_json.get('Email'):
        email = res_json.get('Email')
    else:
        email = get_user_res_json.get('Email')

    if res_json.get('username'):
        userName = res_json.get('username')
    else:
        userName = get_user_res_json.get('username')

    if res.status_code == 200:
        result = res_json

        generic_iam_context = OutputContext(success=True, iden=user_id, email=email,
                                            username=userName, details=result, active=True)
    else:
        generic_iam_context = OutputContext(success=False, iden=user_id, email=get_user_res_json.get('Email'),
                                            username=get_user_res_json.get('username'), errorCode=res.status_code,
                                            errorMessage=res_json.get('message'), details=res_json)

    generic_iam_context_dt = f'{generic_iam_context.command}(val.id == obj.id && val.instanceName == obj.instanceName)'
    outputs = {
        generic_iam_context_dt: generic_iam_context.data
    }
    readable_output = tableToMarkdown('Update Clarizen User:', t=generic_iam_context.data,
                                      headers=["brand", "instanceName", "success", "active", "id", "username", "email",
                                               "errorCode", "errorMessage", "details"],
                                      removeNull=True
                                      )
    return (
        readable_output,
        outputs,
        generic_iam_context.data
    )


def disable_user_command(client, args):
    """
        Disable user using POST to Clarizen API , if Connection to the service is successful.

        Args:   demisto command line argument
        client: Clarizen Client

        Returns:
            success : success=True, id, details, active status
            fail : success=False, id, errorCod, errorMessage, details
    """
    scim = verify_and_load_scim_data(args.get('scim'))
    parsed_scim_data = map_scim(scim)
    user_id = parsed_scim_data.get('id')

    if not user_id:
        raise Exception('You must provide sys id of the user')

    clarizen_user = {
        "ids": [f"/User/{user_id}"],
        "operation": "Disable"
    }

    res = client.enable_or_disable_user(clarizen_user)
    res_json = res.json()

    if res.status_code == 200:
        get_user_id = "/User/" + user_id
        get_user_res = client.get_user_by_id(get_user_id)
        get_user_res_json = get_user_res.json()

        result = res_json
        active = False

        generic_iam_context = OutputContext(success=True, iden=user_id, email=get_user_res_json.get("Email"),
                                            username=get_user_res_json.get("username"), details=result, active=active)
    else:
        generic_iam_context = OutputContext(success=False, iden=user_id, errorCode=res.status_code,
                                            errorMessage=res_json.get('message'), details=res_json)

    generic_iam_context_dt = f'{generic_iam_context.command}(val.id == obj.id && val.instanceName == obj.instanceName)'
    outputs = {
        generic_iam_context_dt: generic_iam_context.data
    }
    readable_output = tableToMarkdown('Disable Clarizen User:', t=generic_iam_context.data,
                                      headers=["brand", "instanceName", "success", "active", "id", "username", "email",
                                               "errorCode", "errorMessage", "details"],
                                      removeNull=True
                                      )
    return (
        readable_output,
        outputs,
        generic_iam_context.data
    )


def enable_user_command(client, args):
    """
        Enable user using POST to Clarizen API , if Connection to the service is successful.

        Args:   demisto command line argument
        client: Clarizen Client

        Returns:
            success : success=True, id, details, active status
            fail : success=False, id, errorCod, errorMessage, details
    """
    scim = verify_and_load_scim_data(args.get('scim'))
    custom_mapping = demisto.params().get('customMappingUpdateUser')

    parsed_scim = map_scim(scim)
    user_id = parsed_scim.get('id')

    if not user_id:
        raise Exception('You must provide id of the user')

    clarizen_user = {
        "ids": [f"/User/{user_id}"],
        "operation": "Enable"
    }

    res = client.enable_or_disable_user(clarizen_user)
    if res.status_code != 200:
        res_json = res.json()
        generic_iam_context = OutputContext(success=False, iden=user_id, errorCode=res.status_code,
                                            errorMessage=res_json.get('message'), details=res_json)

        generic_iam_context_dt = f'{generic_iam_context.command}(val.id == obj.id && val.instanceName == ' \
                                 f'obj.instanceName) '
        outputs = {
            generic_iam_context_dt: generic_iam_context.data
        }
        readable_output = tableToMarkdown('Enable Clarizen User:', t=generic_iam_context.data,
                                          headers=["brand", "instanceName", "success", "active", "id", "username",
                                                   "email",
                                                   "errorCode", "errorMessage", "details"],
                                          removeNull=True
                                          )
        return (
            readable_output,
            outputs,
            generic_iam_context.data
        )

    clarizen_user = client.build_clarizen_user_profile(client, args, scim, custom_mapping)

    new_clarizen_user = {}

    for key, value in clarizen_user.items():
        if not (value is None):
            new_clarizen_user[key] = value

    res = client.update_user(new_clarizen_user, user_id)
    res_json = res.json()
    if res.status_code == 200:

        get_user_id = "/User/" + user_id
        get_user_res = client.get_user_by_id(get_user_id)
        get_user_res_json = get_user_res.json()

        result = res_json
        active = True

        generic_iam_context = OutputContext(success=True, iden=user_id, email=get_user_res_json.get('Email'),
                                            username=get_user_res_json.get("username"), details=result, active=active)
    else:
        generic_iam_context = OutputContext(success=False, iden=user_id, errorCode=res.status_code,
                                            errorMessage=res_json.get('message'), details=res_json)

    generic_iam_context_dt = f'{generic_iam_context.command}(val.id == obj.id && val.instanceName == obj.instanceName)'
    outputs = {
        generic_iam_context_dt: generic_iam_context.data
    }
    readable_output = tableToMarkdown('Enable Clarizen User:', t=generic_iam_context.data,
                                      headers=["brand", "instanceName", "success", "active", "id", "username", "email",
                                               "errorCode", "errorMessage", "details"],
                                      removeNull=True
                                      )
    return (
        readable_output,
        outputs,
        generic_iam_context.data
    )


def main():
    """
        PARSE AND VALIDATE INTEGRATION PARAMS
    """
    params = demisto.params()

    api_version = params.get('api_version', None)

    # get the Clarizen API url
    base_url = urljoin(params.get('url').strip('/'))
    username = params.get('credentials', {}).get('identifier')
    password = params.get('credentials', {}).get('password')
    verify_certificate = not demisto.params().get('insecure', False)
    proxy = demisto.params().get('proxy', False)
    command = demisto.command()

    LOG(f'Command being called is {command}')
    commands = {
        'test-module': test_module,
        'get-user': get_user_command,
        'create-user': create_user_command,
        'update-user': update_user_command,
        'disable-user': disable_user_command,
        'enable-user': enable_user_command
    }

    client = Client(
        base_url=base_url,
        verify=verify_certificate,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json'

        },
        version=api_version,
        username=username,
        password=password,
        proxy=proxy)

    try:
        if command in commands:
            human_readable, outputs, raw_response = commands[command](client, demisto.args())
            return_outputs(readable_output=human_readable, outputs=outputs, raw_response=raw_response)
    # Log exceptions
    except Exception:
        return_error(f'Failed to execute {demisto.command()} command. Traceback: {traceback.format_exc()}')


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()