
angular.module('cloudscalers.AccountServices', ['ng','cloudscalers.SessionServices'])

	.config(['$httpProvider',function($httpProvider) {
        $httpProvider.interceptors.push('authenticationInterceptor');
	}])
    .factory('Account',function ($http, $q) {
    	return {
            list: function() {
                return $http.get(cloudspaceconfig.apibaseurl + '/accounts/list').then(
                		function(result) {
                            return result.data;
                            var cloudspaces = promises[1].data;
                    });
            }
        };
    });