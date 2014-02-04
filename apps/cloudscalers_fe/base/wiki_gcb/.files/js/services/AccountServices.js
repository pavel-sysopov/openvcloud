
angular.module('cloudscalers.services')

	.factory('Account', function ($http, $q, SessionData) {
    	return {
            list: function() {
                return $http.get(cloudspaceconfig.apibaseurl + '/accounts/list').then(
                		function(result) {
                            return result.data;
                    });
            },
            listUsers: function() {
                return $http.get(cloudspaceconfig.apibaseurl + '/accounts/listUsers').then(
                        function(result) {
                            return result.data;
                    });
            },
            current: function() {
                return SessionData.getAccount();
            },
            setCurrent: function(account) {
                SessionData.setAccount(account);
            },

            get: function(id) {
                return $http.get(cloudspaceconfig.apibaseurl + '/accounts/get?accountId=' + id).then(
                        function(result){
                            return result.data;
                        },
                        function(reason){
                            return $q.reject(reason);
                        }
                    );
            },
            addUser: function(account, user, accessType) {
                var accessString = '';
                for (var x in accessType) {
                    if (accessType[x])
                        accessString += x;
                }

                return $http.get(cloudspaceconfig.apibaseurl + '/accounts/addUser?accountId=' + account.id +
                          '&accesstype=' + accessString + '&userId=' + user)
                    .then(function(reason) { 
                        return reason.data; 
                    });
            },
            deleteUser: function(account, userId) {
                return $http.get(cloudspaceconfig.apibaseurl + '/accounts/deleteUser?accountId=' + account.id + 
                                 '&userId=' + userId)
                    .then(function(result) { return result.data; },
                          function(reason) { return reason.data; });
            },
            getCreditBalance: function(account) {
                return $http.get(cloudspaceconfig.apibaseurl + '/accounts/getCreditBalance?accountId=' + account.id).
                    then(function(result){return result.data;},
                        function(reason){return $q.reject(reason);}
                    );
            },
            getCreditHistory: function(account) {
                return $http.get(cloudspaceconfig.apibaseurl + '/accounts/getCreditHistory?accountId=' + account.id).
                    then(function(result){return result.data;},
                        function(reason){return $q.reject(reason);}
                    );
            }
        };
    });