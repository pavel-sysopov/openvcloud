from JumpScale import j
from cloudbrokerlib import authenticator
import requests
from requests.auth import HTTPBasicAuth
import ujson, time

class cloudapi_paypal(j.code.classGetBase()):
    """
    API consumption Actor, this actor is the final api a enduser uses to get consumption details

    """
    def __init__(self):

        self.paypal_user = j.application.config.get('mothership1.cloudbroker.paypal.apiuser')
        self.paypal_secret = j.application.config.get('mothership1.cloudbroker.paypal.apisecret')

        self.paypal_url = 'https://api.sandbox.paypal.com'
        usesandbox = j.application.config.get('mothership1.cloudbroker.paypal.sandbox')
        if usesandbox is not '1':
            self.paypal_url = 'https://api.paypal.com'
        else:
            self.paypal_url = 'https://api.sandbox.paypal.com'


        osiscl = j.core.osis.getClient(user='root')

        class Class():
            pass

        self.models = Class()
        for ns in osiscl.listNamespaceCategories('cloudbroker'):
            self.models.__dict__[ns] = (j.core.osis.getClientForCategory(osiscl, 'cloudbroker', ns))
            self.models.__dict__[ns].find = self.models.__dict__[ns].search

        self._te={}
        self.actorname="paypal"
        self.appname="cloudapi"
        #cloudapi_consumption_osis.__init__(self)
        pass


    def _get_access_token(self):

        tokenurl = '%s/v1/oauth2/token' % self.paypal_url
        headers = {'Accept': 'application/json'}
        payload = {'grant_type':'client_credentials'}
        paypalresponse = requests.post(tokenurl,headers=headers,data=payload,auth=HTTPBasicAuth(self.paypal_user, self.paypal_secret))
        if paypalresponse.status_code is not 200:
            #TODO raise error
            pass
        paypalresponsedata = paypalresponse.json()
        access_token = paypalresponsedata['access_token']
        #TODO: cache the token
        return access_token


    def confirmauthorization(self, id, token, PayerID, **kwargs):
        """
        Paypal callback url
        param:id
        param:token
        param:PayerID
        result string
        """
        ctx = kwargs['ctx']
        creditTransaction = self.models.credittransaction.get(id)
        paymentreference = creditTransaction.reference
        access_token = self._get_access_token()
        paymenturl = "%s/v1/payments/payment/%s/execute/" % (self.paypal_url,paymentreference)
        headers = {"Content-Type":"application/json",
                   "Authorization": "Bearer %s" % access_token}
        payload = { "payer_id" : PayerID }
        paypalresponse = requests.post(paymenturl, headers=headers,data=ujson.dumps(payload))
        if paypalresponse.status_code is not 200:
            ctx.start_response('302 Found',[('location','/wiki_gcb/AccountSettings')])
            return "There was an error executing the payment at paypal"
            #TODO raise erro

        paypalresponsedata = paypalresponse.json()

        creditTransaction.status = 'PROCESSED'
        self.models.credittransaction.set(creditTransaction)
        ctx.start_response('302 Found', [('location','/wiki_gcb/PaypalConfirmation')])
        return ""

    @authenticator.auth(acl='R')
    def initiatepayment(self, accountId, amount, currency, **kwargs):
        """
        Starts a paypal payment flow.
        param:accountId id of the account
        param:amount amount of credit to add
        param:currency currency the code of the currency you want to make a payment with (USD currently supported)
        result dict
        """
        ctx = kwargs['ctx']
        import urlparse
        urlparts = urlparse.urlsplit(ctx.env['HTTP_REFERER'])
        portalurl = '%s://%s' % (urlparts.scheme, urlparts.hostname)
        access_token = self._get_access_token()
        credittransaction = self.models.credittransaction.new()
        credittransaction.time = int(time.time())
        credittransaction.amount = amount
        credittransaction.credit = amount
        credittransaction.currency = 'USD'
        credittransaction.status = 'UNCONFIRMED'
        credittransaction.accountId = accountId
        credittransaction.id = self.models.credittransaction.set(credittransaction)[0]
        paymenturl = '%s/v1/payments/payment' % self.paypal_url
        payload = {
                   "intent":"sale",
                   "redirect_urls":{
                                    "return_url":"%s/restmachine/cloudapi/paypal/confirmauthorization?id=%s&authkey=%s" % (portalurl,credittransaction.id,kwargs['authkey']),
                                    "cancel_url":"%s/wiki_gcb/AccountSettings" % portalurl
                                   },
                   "payer":{
                            "payment_method":"paypal"
                           },
                   "transactions":[
                                   {
                                    "amount":{
                                              "total":amount,
                                              "currency":"USD"
                                             }
                                   }
                                  ]
                  }

        headers = {'content-type': 'application/json', 'Authorization': 'Bearer %s' % access_token}
        paypalresponse = requests.post(paymenturl, headers=headers,data=ujson.dumps(payload))
        if paypalresponse.status_code is not 201:
             #TODO raise error
             pass
        paypalresponsedata = paypalresponse.json()

        credittransaction.reference = paypalresponsedata['id']
        self.models.credittransaction.set(credittransaction)

        approval_url = next((link['href'] for link in paypalresponsedata['links'] if link['rel'] == 'approval_url'), None)
        return {'paypalurl':approval_url}
