


angular.module('cloudscalers.SessionServices', ['ng'])

	.factory('authenticationInterceptor',['$q','$log', 'SessionData', function($q, $log, SessionData){
        return {
            'request': function(config) {
                if (config) {
                    url = config.url;

                    if(! /(partials)|(template)\//i.test(url)){

                    	var currentUser = SessionData.getUser();
                    	if (currentUser){
                    		uri = new URI(url);
                       		uri.addSearch('authkey', currentUser.api_key);
                       		config.url = uri.toString();
    					}
                    }
                }
                return config || $q.when(config);
    	    },
    	    'response': function(response) {
                $log.log("Response intercepted");
                return response || $q.when(response);
            }
        };
	}])
    .factory('SessionData', function($window) {
        return {
        	getUser : function(){
        			var userdata = $window.sessionStorage.getItem('gcb:currentUser');
        			if (userdata){
        				return JSON.parse(userdata);
        			}
        		},
        	setUser : function(userdata){
        			if (userdata){
        				$window.sessionStorage.setItem('gcb:currentUser', JSON.stringify(userdata));
        			}
        			else{
        				$window.sessionStorage.removeItem('gcb:currentUser');
        			}
        		}
        }
    })
    .factory('User', function ($http, SessionData, $q) {
        var user = {};
        
        user.current = function() {
            return SessionData.getUser();
        };
        
        user.login = function (username, password) {
            return $http({
                method: 'POST',
                data: {
                    username: username,
                    password: password
                },
                url: cloudspaceconfig.apibaseurl + '/users/authenticate'
            }).then(
            		function (result) {
            			SessionData.setUser({username: username, api_key: JSON.parse(result.data)});
            			return result.data;
            		},
            		function (reason) {
            			SessionData.setUser(undefined);
                        return $q.reject(reason); }
            );
        };

        user.logout = function() {
        	SessionData.setUser(undefined);
        };

        user.signUp = function(username, email, password) {
            var signUpResult = {};
            $http({
                method: 'POST',
                data: {
                    username: username,
                    email: email,
                    password: password
                },
                url: cloudspaceconfig.apibaseurl + '/users/signup'
            })
            .success(function(data, status, headers, config) {
                signUpResult.success = true;
            })
            .error(function(data, status, headers, config) {
                signUpResult.error = data;
            });
            return signUpResult;
        }
        
        return user;
        
    });