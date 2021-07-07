import demistomock as demisto
from CommonServerPython import *  # noqa # pylint: disable=unused-wildcard-import

import requests
import traceback
from typing import Dict, Any
from datetime import datetime, timedelta

# Disable insecure warnings
requests.packages.urllib3.disable_warnings()  # pylint: disable=no-member


""" CONSTANTS """

SECURITYSCORECARD_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

""" CLIENT CLASS """


class Client(BaseClient):
    """Client class to interact with the service API

    This Client implements API calls, and does not contain any XSOAR logic.
    Should only do requests and return data.
    It inherits from BaseClient defined in CommonServer Python.
    Most calls use _http_request() that handles proxy, SSL verification, etc.
    For this  implementation, no special attributes defined
    """

    def get_portfolios(self) -> List[Dict[str, Any]]:

        return self._http_request(
            'GET',
            url_suffix='portfolios'
        )

    def get_companies_in_portfolio(
        self, 
        portfolio: str, 
        grade: Optional[str],
        industry: Optional[str],
        vulnerability: Optional[str],
        issue_type: Optional[str],
        had_breach_within_last_days: Optional[int]
    ) -> List[Dict[str, Any]]:

        request_params: Dict[str, Any] = {}

        if grade:
            request_params['grade'] = grade
        
        if industry:
            request_params['industry'] = str.upper(industry)

        if vulnerability:
            request_params['vulnerability'] = vulnerability
        
        if issue_type:
            request_params['issue_type'] = issue_type
        
        if had_breach_within_last_days:
            request_params['had_breach_within_last_days'] = had_breach_within_last_days

        return self._http_request(
            'GET',
            url_suffix='portfolios/{0}/companies'.format(portfolio),
            params=request_params
        )

    def get_company_score(self, domain: str) -> List[Dict[str, Any]]:

        return self._http_request(
            'GET',
            url_suffix='companies/{0}'.format(domain)
        )

    def get_company_factor_score(self, domain: str, severity_in: Optional[List[str]]) -> List[Dict[str, Any]]:

        request_params: Dict[str, Any] = {}

        if severity_in:
            request_params['severity_in'] = severity_in

        return self._http_request(
            'GET',
            url_suffix='companies/{0}/factors'.format(domain),
            params=request_params
        )

    def get_company_historical_scores(self, domain: str, _from: str, to: str, timing: str) -> List[Dict[str, Any]]:

        request_params: Dict[str, Any] = {}

        if _from:
            request_params['from'] = _from

        if to:
            request_params['to'] = to

        if timing:
            request_params['timing'] = timing
        # API by default is set to daily
        else:
            request_params['timing'] = 'daily'

        return self._http_request(
            'GET',
            url_suffix='companies/{0}/history/score'.format(domain),
            params=request_params
        )
    
    def get_company_historical_factor_scores(self, domain: str, _from: str, to: str, timing: str) -> List[Dict[str, Any]]:

        request_params: Dict[str, Any] = {}

        if _from:
            request_params['from'] = _from

        if to:
            request_params['to'] = to

        if timing:
            request_params['timing'] = timing
        # # API by default is set to daily
        # else:
        #     request_params['timing'] = 'daily'

        return self._http_request(
            'GET',
            url_suffix='companies/{0}/history/factors/score'.format(domain),
            params=request_params
        )

    def create_grade_change_alert(self, email: str, change_direction: str, score_types: List[str], target: List[str]) -> List[Dict[str, Any]]:

        payload = {}
        if change_direction:
            payload["change_direction"] = change_direction

        if len(score_types) > 0:
            payload["score_types"] = score_types

        if len(target) > 0:
            payload["target"] = target

        return self._http_request(
            'POST',
            url_suffix="users/by-username/{0}/alerts/grade".format(email),
            json_data=payload
        )
    
    def create_score_threshold_alert(self, email: str, change_direction: str, threshold: int, score_types: List[str], target: List[str]) -> List[Dict[str, Any]]:

        payload = {}
        if change_direction:
            payload["change_direction"] = change_direction

        threshold = arg_to_number(arg=threshold, arg_name=threshold, required=True)
        payload["threshold"] = threshold

        if len(score_types) > 0:
            payload["score_types"] = score_types

        if len(target) > 0:
            payload["target"] = target

        return self._http_request(
            'POST',
            url_suffix="users/by-username/{0}/alerts/score".format(email),
            json_data=payload
        )
        
    def delete_alert(self, email: str, alert_id: str, alert_type: str) -> List[Dict[str, Any]]:

        return self._http_request(
            "DELETE",
            url_suffix="users/by-username/{0}/alerts/{1}/{2}".format(email, alert_type, alert_id),
            return_empty_response=True
        )

    def get_alerts_last_week(self, email: str, portfolio_id: Optional[str]) -> List[Dict[str, Any]]:

        query_params = {}
        
        if portfolio_id:
            query_params["portfolio"] = portfolio_id

        return self._http_request(
            "GET",
            url_suffix="users/by-username/{0}/notifications/recent".format(email),
            params=query_params
        )

    def get_domain_services(self, domain: str) -> List[Dict[str, Any]]:

        return self._http_request(
            'GET',
            url_suffix="companies/{0}/services".format(domain)
        )

    def fetch_alerts(self, page_size: int, username: str):
        
        query_params = {}

        if page_size:
            query_params["page_size"] = page_size 
        # Default to 100 alerts
        else:
            query_params["page_size"] = 100
        
        query_params["username"] = username

        # Default parameters to sort by descending date
        # sort=date&order=desc&
        query_params["sort"] = "date"
        query_params["order"] = "desc"

        return self._http_request(
            "GET",
            url_suffix="users/by-username/{0}/notifications/recent".format(username),
            params=query_params
        )

""" HELPER FUNCTIONS """

def verify_grade(grade):
    """
    Helper function to verify the grade is valid.
    Grade should be a letter between a-f.
    Grade will be capitalized as API expects it.
    """

    demisto.debug("Verifying grade argument '{0}'...".format(grade))
    # Converting to lower case to normalize letter comparison 
    grade_lower = str.lower(grade)

    # Regex to check if the grade matches alphabet range
    grade_match = re.search("[a-f]", grade_lower)

    if grade_match:
        demisto.debug("Grade valid")
        return str.capitalize(grade_lower)
    else:
        return_warning("Grade {0} is invalid. Ignoring grade argument".format(grade_lower))
        return None

# TODO create domain validation method
# https://www.geeksforgeeks.org/how-to-validate-a-domain-name-using-regular-expression/

# TODO write image Markdown converter method

# TODO create email address validation
# https://www.geeksforgeeks.org/check-if-email-address-valid-or-not-in-python/

def incidents_to_import(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

    """
    Helper function to filter events that need to be imported
    It filters the events based on the `created_at` timestamp.
    Function will only be called if the SecurityScorecard API returns more than one alert.

    :type ``events``: ``List[Dict[str, Any]]``
    
    :return
        Events to import

    :rtype
        ``List[Dict[str, Any]]``
    """

    # Check for existence of last run
    # When integration runs for the first time, it will not exist
    if demisto.getLastRun().get("last_run"):
        last_run = int(demisto.getLastRun().get("last_run"))
    else:
        fetchDaysAgo = demisto.params().get("fetchDaysAgo")

        # Default to 7 days if parameter is not specified
        if not fetchDaysAgo:
            daysAgo = 7
        else:
            daysAgo = int(fetchDaysAgo)

        demisto.debug("Didn't find getLastRun in integration context, using parameter 'fetchDaysAgo' value {0} instead".format(daysAgo)) 
        date_days_ago = datetime.now() - timedelta(days=daysAgo)
        last_run = int(date_days_ago.timestamp())

    demisto.debug("Last run timestamp: {0}".format(last_run))

    incidents_to_import: List[Dict[str, Any]] = []

    for alert in alerts:

    	alert_timestamp = int(datetime.strptime(alert.get("created_at"), SECURITYSCORECARD_DATE_FORMAT).timestamp())

        alert_id = alert.get("id")
        
        demisto.debug("last_run: {0}, alert_timestamp: {1}, should import alert '{2}'? (last_run < alert_timestamp): {3}".format(last_run, alert_timestamp, alert_id, (last_run < alert_timestamp)))

        if alert_timestamp < last_run:
            incident = {}
            incident["name"] = "SecurityScorecard '{0}' Incident".format(alert.get("change_type"))
            incident["occurred"] = datetime.strptime(alert.get("created_at"), SECURITYSCORECARD_DATE_FORMAT).strftime(DATE_FORMAT)
            incident["rawJSON"] = json.dumps(alert)
            incidents_to_import.append(incident)
		
	
    now = int(datetime.utcnow().timestamp())
    demisto.debug("Setting last runtime: {0}".format(now))
    demisto.setLastRun({
        'last_run': now
    })

    return incidents_to_import

""" COMMAND FUNCTIONS """

# TODO implement test module
def test_module(client: Client) -> str:
    """Tests API connectivity and authentication'

    Returning 'ok' indicates that the integration works like it is supposed to.
    Connection to the service is successful.
    Raises exceptions if something goes wrong.

    :type client: ``Client``
    :param Client: client to use

    :return: 'ok' if test passed, anything else will fail the test.
    :rtype: ``str``
    """

    message: str = ''
    try:
        # TODO: ADD HERE some code to test connectivity and authentication to your service.
        # This  should validate all the inputs given in the integration configuration panel,
        # either manually or by using an API that uses them.
        message = 'ok'
    except DemistoException as e:
        if 'Forbidden' in str(e) or 'Authorization' in str(e):  # TODO: make sure you capture authentication errors
            message = 'Authorization Error: make sure API Key is correctly set'
        else:
            raise e
    return message

#region Methods
#---------------
def securityscorecard_portfolios_get_command(client: Client) -> CommandResults:
    """`zsecurityscorecard_portfolios_get_command`: Get all Portfolios you have access to.

    See https://securityscorecard.readme.io/reference#get_portfolios
	
	:type ``client``: ``Client``
		
	:return:
		A ``CommandResults`` object that is passed to ``return_results``
	:rtype: ``CommandResults``
	"""

    portfolios = client.get_portfolios()

    # Check that API returned more than 0 portfolios
    if portfolios.get('total') and not int(portfolios.get('total')) > 0:
        return_warning("No Portfolios were found in your account. Please create a new one and try again.", exit=True)

    # API response is a dict with 'entries'
    entries = portfolios.get('entries')

    markdown = tableToMarkdown('Your SecurityScorecard Portfolios', entries, headers=['id', 'name', 'privacy'])

    results = CommandResults(
        readable_output=markdown,
        outputs_prefix='SecurityScorecard.Portfolio',
        outputs_key_field='id',
        outputs=portfolios
    )

    return_results(results)

def securityscorecard_portfolio_get_companies_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    """zsecurityscorecard_portfolio_get_companies_commandz: Retrieve all companies in portfolio.
	
    https://securityscorecard.readme.io/reference#get_portfolios-portfolio-id-companies

	:type ``client``: ``Client``
	:type `` args``: ``Dict[str, Any]``
		``args['portfolio_id']``: Portfolio ID. A list of Portfolio IDs can be retrieved using the ``!securityscorecard-portfolios-get`` command., type ``String``
		``args['grade']``: Grade filter. The acceptable values are capitalized letters between A-F, e.g. B., type ``String``
		``args['industry']``: Industry filter. The acceptable values are capitalized, e.g. INFORMATION_SERVICES, TECHNOLOGY., type ``String``
		``args['vulnerability']``: Vulnerability filter, type ``String``
		``args['issue_type']``: Issue type filter. TODO, need to list all possible values, can be found in active findings API., type ``String``
		``args['had_breach_within_last_days']``: Domains with breaches in the last X days. Possible values are numbers, e.g. 1000., type ``Number``
		
	:return:
		A ``CommandResults`` object that is passed to ``return_results``
	:rtype: ``CommandResults``
	"""

    # TODO need to check how/if need to handle mandatory aruments not being supplied
    # if not args.has_key('portfolio_id'):
    # ...

    demisto.debug("securityscorecard_portfolio_get_companies_command called with args: {0}".format(args))

    portfolio_id = args.get('portfolio_id')

    # Validate grade argument
    if 'grade' in args:
        grade = verify_grade(args.get('grade'))
    else:
        grade = None

    # Validate and transform industry
    # We need to capitalize the industry to conform to API
    if 'industry' in args:
        industry = str.upper(args.get('industry'))
    else:
        industry = None

    vulnerability = args.get('vulnerability')
    
    issue_type = args.get('issue_type')

    had_breach_within_last_days = arg_to_number(
        arg=args.get('had_breach_within_last_days'), 
        arg_name='had_breach_within_last_days', 
        required=False
    )

    response = client.get_companies_in_portfolio(
        portfolio=portfolio_id,
        grade=grade,
        industry=industry,
        vulnerability=vulnerability,
        issue_type=issue_type,
        had_breach_within_last_days=had_breach_within_last_days
    )

    # Check if the portfolio has more than 1 company
    # Throw warning to UI if there are no companies

    total_portfolios = int(response.get('total'))

    if not total_portfolios > 0:
        return_warning("No companies found in Portfolio {0}. Please add a company to it and retry.".format(portfolio_id))

    companies = response.get('entries')

    markdown = "**{0}** companies found in Portfolio {1}\n".format(total_portfolios, portfolio_id)
    markdown += tableToMarkdown("Companies in Portfolio {0}".format(portfolio_id), companies, headers=['domain', 'name', 'score', 'last30days_score_change', 'industry', 'size'])

    results = CommandResults(
        "SecurityScorecard.Company",
        readable_output=markdown,
        outputs=companies
    )

    return_results(results)

def securityscorecard_company_score_get_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    """securityscorecard_company_score_get_command: Retrieve company overall score.

    See 
	
	:type ``client``: ``Client``
	:type `` args``: ``Dict[str, Any]``
		``args['domain']``: Company domain, e.g. google.com, type ``String``
		
	:return:
		A ``CommandResults`` object that is passed to ``return_results``
	:rtype: ``CommandResults``
	"""

    domain = args.get('domain')

    score = client.get_company_score(domain=domain)

    # Render the grade image
    # TODO change resolution of image render size
    # https://stackoverflow.com/questions/14675913/changing-image-size-in-markdown
    score['grade_url'] = "![{0}]({0})".format(score.get('grade_url'))

    markdown = tableToMarkdown("Domain {0} Scorecard".format(domain), score)

    results = CommandResults(
        readable_output=markdown,
        outputs_prefix="SecurityScorecard.Company.Score",
        outputs=score
    )

    return_results(results)
    
def securityscorecard_company_factor_score_get_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    
    """securityscorecard_company_factor_score_get_command: Retrieve company factor score.
	
	:type ``client``: ``Client``
	:type `` args``: ``Dict[str, Any]``
		``args['domain']``: Company domain., type ``String``
		``args['severity_in']``: Issue severity filter. Optional values can be positive, info, low, medium, high. Can be comma-separated list, e.g. 'medium,high,positive', type ``array``
		
	:return:
		A ``CommandResults`` object that is passed to ``return_results``
	:rtype: ``CommandResults``
	"""

    domain = args.get('domain')
    severity_in = args.get('severity_in')

    response = client.get_company_factor_score(domain, severity_in)
    
    demisto.debug("factor score response: {0}".format(response))
    factor_scores = response.get('entries')


    # Render the grade image
    # TODO change resolution of image render size
    # https://stackoverflow.com/questions/14675913/changing-image-size-in-markdown
    for score in factor_scores:
        score['grade_url'] = "![{0}]({0})".format(score.get('grade_url'))
        # Doesn't work
        # score["grade_url"] = "<img src=\"{0}\" width=\"50\">".format(score.get("grade_url"))

    # TODO Need to change the output as currently nested 'issue_summary' 
    markdown = tableToMarkdown("Domain {0} Scorecard".format(domain), factor_scores)

    results = CommandResults(
        readable_output=markdown,
        outputs_prefix="SecurityScorecard.Company.Factor",
        outputs=factor_scores
    )

    return_results(results)

def securityscorecard_company_history_score_get_command(client: Client, args: Dict[str, Any]) -> CommandResults:

    """securityscorecard_company_history_score_get_command: Retrieve company historical scores
	
    See https://securityscorecard.readme.io/reference#get_companies-scorecard-identifier-history-score

	:type ``client``: ``Client``
	:type `` args``: ``Dict[str, Any]``
		``args['domain']``: Company domain, e.g. google.com, type ``String``.
		``args['from']``: Initial date for historical data. Value should be in format `YYYY-MM-DD`, type ``Date``.
		``args['to']``: Initial date for historical data. Value should be in format `YYYY-MM-DD`, type ``Date``.
            By default, if `from` and `to` are not supplied, the API will return 1 year back.
		``args['timing']``: Timing granularity. Acceptable values are `weekly` or `daily`, type ``String``, Default: `daily`.
		
	:return:
		A ``CommandResults`` object that is passed to ``return_results``
	:rtype: ``CommandResults``
	"""
    # TODO implement domain validation
    domain = args.get('domain')
    # TODO implement date format validation
    _from = args.get('from')
    to = args.get('to')
    # TODO implement timing value validation
    timing = args.get('timing')

    demisto.debug("Arguments: {0}".format(args))
    response = client.get_company_historical_scores(domain=domain, _from=_from, to=to, timing=timing)
    
    demisto.debug("API response: {0}".format(response))

    entries = response.get('entries')

    markdown = tableToMarkdown("Historical Scores for Domain [`{0}`](https://{0})".format(domain), entries, headers=['date', 'score'])

    results = CommandResults(
        readable_output=markdown,
        outputs_prefix="SecurityScorecard.Company.History",
        outputs=entries
    )

    return_results(results)

def securityscorecard_company_history_factor_score_get_command(client: Client, args: Dict[str, Any]) -> CommandResults:

    """securityscorecard_company_history_factor_score_get_command: Retrieve company historical factor scores
	
    See https://securityscorecard.readme.io/reference#get_companies-scorecard-identifier-history-factors-score

	:type ``client``: ``Client``
	:type `` args``: ``Dict[str, Any]``
		``args['domain']``: Company domain, e.g. google.com, type ``String``.
		``args['from']``: Initial date for historical data. Value should be in format `YYYY-MM-DD`, type ``Date``.
		``args['to']``: Initial date for historical data. Value should be in format `YYYY-MM-DD`, type ``Date``.
            By default, if `from` and `to` are not supplied, the API will return 1 year back.
		``args['timing']``: Timing granularity. date granularity, it could be "daily" (default), "weekly" or "monthly", type ``String``, Default: `daily`.
		
	:return:
		A ``CommandResults`` object that is passed to ``return_results``
	:rtype: ``CommandResults``
	"""

    # TODO implement domain validation
    domain = args.get('domain')
    # TODO implement date format validation
    _from = args.get('from')
    to = args.get('to')
    # TODO implement timing value validation
    timing = args.get('timing')

    demisto.debug("Arguments: {0}".format(args))
    response = client.get_company_historical_factor_scores(domain=domain, _from=_from, to=to, timing=timing)
    
    demisto.debug("API response: {0}".format(response))

    entries = response.get('entries')

    # TODO output for each entry has a 'factors' list, need to check how best to display within a table
    factor_scores = []

    for entry in entries:
        factors = entry.get("factors")
        for factor in factors:
            factor_score = {}
            factor_score["score"] = factor["score"]
            factor_score["name"] = factor["name"]
            factor_score["date"] = entry.get("date")
            factor_scores.append(factor_score)

    markdown = tableToMarkdown("Historical Factor Scores for Domain [`{0}`](https://{0})".format(domain), factor_scores)

    results = CommandResults(
        readable_output=markdown,
        outputs_prefix="SecurityScorecard.Company.FactorHistory",
        outputs=entries
    )

    return_results(results)

def securityscorecard_alert_grade_change_create_command(client: Client, args: Dict[str, Any]) -> CommandResults:
	
    """securityscorecard_alert_grade_change_create_command: Create alert based on grade
	
    See https://securityscorecard.readme.io/reference#post_users-by-username-username-alerts-grade

	:type ``client``: ``Client``
	:type `` args``: ``Dict[str, Any]``
		``args['email']``: Email of alert recipient. The user must be registered in SecurityScorecard system., type ``String``
		``args['change_direction']``: Direction of change. Possible values are 'rises' or 'drops'., type ``String``
		``args['score_types']``: Types of risk factors to monitor. Possible values are 'overall', 'any_factor_score', 'network_security', 'dns_health', 'patching_cadence', 'endpoint_security', 'ip_reputation', 'application_security', 'cubit_score', 'hacker_chatter', 'leaked_information', 'social_engineering'. For multiple factors, ['leaked_information', 'social_engineering'], type ``array``
		``args['target']``: What do you want to monitor with this alert. It could be one of the following 'my_scorecard', 'any_followed_company' or an array of portfolio IDs, e.g. ['60c78cc2d63162001a68c2b8', '60c8c5f9139e40001908c6a4'] or ['60c78cc2d63162001a68c2b8', 'my_portfolio'], type ``array``
		
	:return:
		A ``CommandResults`` object that is passed to ``return_results``
	:rtype: ``CommandResults``
	"""
    
    # TODO add email address validation
    email = args.get('email')
    change_direction = args.get('change_direction')
    # TODO change to argToList
    score_types = args.get('score_types').split(',')
    # TODO change to argToList
    target = args.get('target').split(',')

    demisto.debug("Attempting to create alert with body {0}".format(args))
    response = client.create_grade_change_alert(email=email, change_direction=change_direction, score_types=score_types, target=target)
    demisto.debug("Response received: {0}".format(response))
    alert_id = response.get("id")

    markdown = "Alert **{0}** created".format(alert_id)

    results = CommandResults(readable_output=markdown, outputs_prefix="SecurityScorecard.GradeChangeAlert.id", outputs=alert_id)

    return_results(results)

def securityscorecard_alert_score_threshold_create_command(client: Client, args: Dict[str, Any]) -> CommandResults:

    """securityscorecard_alert_score_threshold_create_command: Create alert based threshold met
	
	:type ``client``: ``Client``
	:type `` args``: ``Dict[str, Any]``
		``args['email']``: Email of alert recipient. The user must be registered in SecurityScorecard system., type ``String``
		``args['change_direction']``: Direction of change. Possible values are 'rises_above' or 'drops_below'., type ``String``
		``args['threshold']``: The numeric score used as the threshold to trigger the alert, type ``Number``
		``args['score_types']``: Types of risk factors to monitor. Possible values are 'overall', 'any_factor_score', 'network_security', 'dns_health', 'patching_cadence', 'endpoint_security', 'ip_reputation', 'application_security', 'cubit_score', 'hacker_chatter', 'leaked_information', 'social_engineering'. For multiple factors, ['leaked_information', 'social_engineering'], type ``array``
		``args['target']``: What do you want to monitor with this alert. It could be one of the following 'my_scorecard', 'any_followed_company' or an array of portfolio IDs, e.g. ['60c78cc2d63162001a68c2b8', '60c8c5f9139e40001908c6a4'] or ['60c78cc2d63162001a68c2b8', 'my_portfolio'], type ``array``
		
	:return:
		A ``CommandResults`` object that is passed to ``return_results``
	:rtype: ``CommandResults``
	"""

     # TODO add email address validation
    email = args.get('email')
    change_direction = args.get('change_direction')
    threshold = args.get('threshold')
    score_types = args.get('score_types').split(',')
    target = args.get('target').split(',')

    demisto.debug("Attempting to create alert with body {0}".format(args))
    response = client.create_score_threshold_alert(email=email, change_direction=change_direction, threshold=threshold, score_types=score_types, target=target)
    demisto.debug("Response received: {0}".format(response))
    alert_id = response.get("id")

    markdown = "Alert **{0}** created".format(alert_id)

    results = CommandResults(readable_output=markdown, outputs_prefix="SecurityScorecard.ScoreThresholdAlert.id", outputs=alert_id)

    return_results(results)

def securityscorecard_alert_delete_command(client: Client, args: Dict[str, Any]) -> CommandResults:
	
    """`securityscorecard_alert_delete_command`: Delete an alert
    See https://securityscorecard.readme.io/reference#delete_users-by-username-username-alerts-grade-alert
    See https://securityscorecard.readme.io/reference#delete_users-by-username-username-alerts-score-alert

	:type ``client``: ``Client``
	:type `` args``: ``Dict[str, Any]``
		``args['email']``: Email of alert recipient, type ``String``
		``args['alert_id']``: Alert ID, type ``String``
        ``args['alert_type']``: Alert type. Can be either `score` or `grade`, type ``String``
		
	:return:
		A ``CommandResults`` object that is passed to ``return_results``
	:rtype: ``CommandResults``
	"""

    email = args.get("email")
    alert_id = args.get("alert_id")
    alert_type = args.get("alert_type")
    client.delete_alert(email=email, alert_id=alert_id, alert_type=alert_type)

    markdown = "{} alert **{}** deleted".format(alert_type, str.capitalize(alert_id))
    
    # TODO Remove alert from context
    # context = get_integration_context()
    # alert_context = context.get("SecurityScorecard")
    # demisto.setContext()
    # demisto.getIntegrationContext()
    # demisto.debug("Alert context: {}".format(alert_context))
    
    results = CommandResults(readable_output=markdown)

    return_results(results)

def securityscorecard_alert_get_last_week_command(client: Client, args: Dict[str, Any]) -> CommandResults:
	
    """securityscorecard_alert_get_last_week_command: Retrieve alerts triggered in the last week

    See https://securityscorecard.readme.io/reference#get_users-by-username-username-notifications-recent
	
	:type ``client``: ``Client``
	:type `` args``: ``Dict[str, Any]``
		``args['email']``: Email of alert recipient., type ``String``
		``args['portfolio_id']``: Portfolio ID. Can be retrieved using ``!securityscorecard-portfolios-get```, type ``String``
		
	:return:
		A ``CommandResults`` object that is passed to ``return_results``
	:rtype: ``CommandResults``
	"""

    email = args.get('email')
    portfolio_id = args.get('portfolio_id')

    demisto.debug("Sending request to retrieve alerts with arguments {0}".format(args))

    response = client.get_alerts_last_week(email=email, portfolio_id=portfolio_id)

    entries = response.get("entries")

    # Retrieve the alert metadata (direction, score, factor, grade_letter, score_impact)
    alerts = []

    for entry in entries:
        # change_data is a list that includes all alert metadata that triggered the event
        changes = entry.get("change_data")
        for change in changes:
            alert = {}
            alert["id"] = entry.get("id")
            alert["change_type"] = entry.get("change_type")
            alert["domain"] = entry.get("domain")
            alert["company"] = entry.get("company_name")
            alert["created"] = entry.get("created_at")
            alert["direction"] = change.get("direction")
            alert["score"] = change.get("score")
            alert["factor"] = change.get("factor")
            alert["grade_letter"] = change.get("grade_letter")
            alert["score_impact"] = change.get("score_impact")
            alerts.append(alert)

    markdown = tableToMarkdown("Latest Alerts for user {0}".format(email), alerts)

    results = CommandResults(
        outputs_prefix="SecurityScorecard.Alert",
        outputs_key_field="id",
        readable_output=markdown,
        outputs=alerts
    )

    return_results(results)

def securityscorecard_company_services_get_command(client: Client, args: Dict[str, Any]) -> CommandResults:
	
    """securityscorecard_company_services_get_command: Retrieve the service providers of a domain
	
    See https://securityscorecard.readme.io/reference#get_companies-domain-services

	:type ``client``: ``Client``
	:type `` args``: ``Dict[str, Any]``
		``args['domain']``: Company domain, type ``String``
		
	:return:
		A ``CommandResults`` object that is passed to ``return_results``
	:rtype: ``CommandResults``
	"""

    domain = args.get("domain")

    response = client.get_domain_services(domain=domain)

    entries = response.get("entries")

    services = []

    for entry in entries:
        categories = entry.get("categories")
        for category in categories:
            service = {}
            service["vendor_domain"] = entry.get("vendor_domain")
            service["category"] = category
            services.append(service)

    markdown = tableToMarkdown("Services for domain [{0}](https://{0})".format(domain), services)

    results = CommandResults(
        outputs_prefix="SecurityScorecard.Company.Service",
        outputs=entries,
        readable_output=markdown
    )

    return_results(results)

def fetch_alerts(client: Client, params: Dict):

    """
    Fetch incidents/alerts from SecurityScorecard API

    See https://securityscorecard.readme.io/reference#get_users-by-username-username-notifications-recent

    The API is updated on a daily basis therefore `incidentFetchInterval` is set to 1440 (minutes per day)
    The API returns all alerts received in the last week.

    Every alert has a `"created_at"` parameter to notify when the alert was triggered. 
    This method will create incidents only for alerts that occurred on the day the alert was created.

    :type ``client``: ``Client``
	:type `` args``: ``Dict[str, Any]``
		``args['domain']``: Company domain, type ``String``

    :return: 
        ``None``
    :rtype: ``None``
    """    
    # Set the query size
    # API has query param page_size=100
    if not params.get("maxIncidents"):
        max_incidents = 100
    else:
        max_incidents = params.get("maxIncidents")

    # User/email to fetch alerts for
    username = params.get("username")

    results = client.fetch_alerts(page_size=max_incidents, username=username)

    alerts = results.get("entries")

    demisto.debug("API returned {0} alerts".format(str(len(alerts))))

    # Check if the API returned any alerts
    if len(alerts) > 0:
        incidents = incidents_to_import(alerts=alerts)

        # Check if any incidents should be imported according to last run time timestamp
        if len(incidents) > 0:
            demisto.debug("{0} Incidents will be imported".format(str(len(incidents))))
            demisto.debug("Incidents: {0}".format(incidents))
            demisto.incidents(incidents)
        else:
            demisto.debug("No incidents will be imported.")
            demisto.incidents([])
    # Return no incidents if API returned no alerts
    else:
        demisto.debug("API returned no alerts. Returning empty incident list")
        demisto.incidents([])



""" MAIN FUNCTION """

def main() -> None:
    """main function, parses params and runs command functions

    :return:
    :rtype:
    """

    demisto.debug("Script started with parameters '{0}'".format(demisto.params()))

    api_key = demisto.params().get('apikey')

    # SecurityScorecard API URL
    base_url = "https://api.securityscorecard.io/"

    # Default configuration
    verify_certificate = not demisto.params().get('insecure', False)
    proxy = demisto.params().get('proxy', False)

    demisto.debug(f'Command being called is {demisto.command()}')
    try:

        headers: Dict = {"Authorization": "Token {0}".format(api_key)}

        client = Client(
            base_url=base_url,
            verify=verify_certificate,
            headers=headers,
            proxy=proxy)

        if demisto.command() == 'test-module':
            # This is the call made when pressing the integration Test button.
            result = test_module(client)
            return_results(result)
        elif demisto.command() == "fetch-incidents":
            fetch_alerts(client, demisto.params())
        elif demisto.command() == 'securityscorecard-portfolios-get':
            return_results(securityscorecard_portfolios_get_command(client))
        elif demisto.command() == 'securityscorecard-portfolio-get-companies':
            return_results(securityscorecard_portfolio_get_companies_command(client, demisto.args()))
        elif demisto.command() == 'securityscorecard-company-score-get':
            return_results(securityscorecard_company_score_get_command(client, demisto.args()))
        elif demisto.command() == 'securityscorecard-company-factor-score-get':
            return_results(securityscorecard_company_factor_score_get_command(client, demisto.args()))
        elif demisto.command() == 'securityscorecard-company-history-score-get':
            return_results(securityscorecard_company_history_score_get_command(client, demisto.args()))
        elif demisto.command() == 'securityscorecard-company-history-factor-score-get':
            return_results(securityscorecard_company_history_factor_score_get_command(client, demisto.args()))
        elif demisto.command() == 'securityscorecard-alert-grade-change-create':
            return_results(securityscorecard_alert_grade_change_create_command(client, demisto.args()))
        elif demisto.command() == 'securityscorecard-alert-score-threshold-create':
            return_results(securityscorecard_alert_score_threshold_create_command(client, demisto.args()))
        elif demisto.command() == 'securityscorecard-alert-delete':
            return_results(securityscorecard_alert_delete_command(client, demisto.args()))
        elif demisto.command() == 'securityscorecard-alert-get-last-week':
            return_results(securityscorecard_alert_get_last_week_command(client, demisto.args()))
        elif demisto.command() == 'securityscorecard-company-services-get':
            return_results(securityscorecard_company_services_get_command(client, demisto.args()))
        # TODO create fetch_incidents
        
    # Log exceptions and return errors
    except Exception as e:
        demisto.error(traceback.format_exc())  # print the traceback
        return_error(f'Failed to execute {demisto.command()} command.\nError:\n{str(e)}')


""" ENTRY POINT """

if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
