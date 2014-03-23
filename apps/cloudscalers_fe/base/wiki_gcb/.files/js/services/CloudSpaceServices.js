
angular.module('cloudscalers.services')
	 .factory('CloudSpace',function ($http, $q, SessionData) {
    	return {
            list: function() {
            	 return $http.get(cloudspaceconfig.apibaseurl + '/cloudspaces/list').then(
            			 function(result){
            				 return result.data;
            			 });
            },
            current: function() {
                return SessionData.getSpace();
            },
            setCurrent: function(space) {
                SessionData.setSpace(space);
            },
            create: function(name, accountId, userId) {
            	return $http.get(cloudspaceconfig.apibaseurl + '/cloudspaces/create?name=' + encodeURIComponent(name)+'&accountId=' + accountId + '&access=' + encodeURI(userId)).then(
            			function(result){
            				return JSON.parse(result.data);
            			},
            			function(reason){
            				return $q.defer(reason);
            			}
            		);
            },
            get: function(cloudSpaceId) {
                return $http.get(cloudspaceconfig.apibaseurl + '/cloudspaces/get?cloudspaceId=' + cloudSpaceId).then(
                        function(result){
                            return result.data;
                        },
                        function(reason){
                            return $q.defer(reason);
                        }
                    );
            },
            addUser: function(space, user, accessType) {
                var accessString = '';
                for (var x in accessType) {
                    if (accessType[x])
                        accessString += x;
                }

                return $http.get(cloudspaceconfig.apibaseurl + '/cloudspaces/addUser?cloudspaceId=' + space.id +
                          '&accesstype=' + accessString + '&userId=' + user)
                    .then(
                            function(result){ return result.data;},
                            function(reason) { return $q.reject(reason);});
            },
            deleteUser: function(space, userId) {
                return $http.get(cloudspaceconfig.apibaseurl + '/cloudspaces/deleteUser?cloudspaceId=' + space.id + 
                                 '&userId=' + userId)
                    .then(function(result) { return result.data; },
                          function(reason) { return $q.reject(reason); });
            },
            delete: function(cloudspace, userId) {
                return $http.get(cloudspaceconfig.apibaseurl + '/cloudspaces/delete?cloudspaceId=' + cloudspace.id + 
                                 '&userId=' + userId)
                    .then(function(result) { return result.data; },
                          function(reason) { return $q.reject(reason); });
            }
        };
    });