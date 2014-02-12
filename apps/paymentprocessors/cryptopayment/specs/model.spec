
[rootmodel:ConversionRate]
	"""
	The value of a cryptocurrency in USD at a specific time
	"""
	prop:time int,, time from which this rate is valid
	prop:currency str,,
	prop:value float,, the value in USD
	
[rootmodel:PaymentAddress]
	"""
	Addresses for making payments
	"""
	prop:address str,, the address (generated by a wallet somewhere else!)
	prop:coin str,, the currency this address is valid for
	prop:accountId int,, the account this address is assigned to