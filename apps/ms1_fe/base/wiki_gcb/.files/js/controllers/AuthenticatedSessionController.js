angular.module('cloudscalers.controllers')
    .controller('AuthenticatedSessionController', ['$scope', 'User', 'Account', 'CloudSpace', 'LoadingDialog', '$route', '$window','$timeout', '$location', function($scope, User, Account, CloudSpace, LoadingDialog, $route, $window, $timeout, $location) {
        $scope.currentUser = User.current();
        $scope.currentSpace = CloudSpace.current();
        $scope.currentAccount = $scope.currentSpace ? {id:$scope.currentSpace.accountId, name:$scope.currentSpace.accountName, userRightsOnAccount: $scope.currentSpace.acl, userRightsOnAccountBilling: $scope.currentSpace.userRightsOnAccountBilling} : {id:''};

        $scope.setCurrentCloudspace = function(space) {
        	if (space == null)
        	{
        		return;
        	}

            CloudSpace.setCurrent(space);
            $scope.currentSpace = space;
            $scope.setCurrentAccount();
        };

        $scope.setCurrentAccount = function(){
            if ($scope.currentSpace){
                $scope.currentAccount = {id: $scope.currentSpace.accountId, name: $scope.currentSpace.accountName, userRightsOnAccount: $scope.currentSpace.acl, userRightsOnAccountBilling: $scope.currentSpace.userRightsOnAccountBilling};
            }
        };

        $scope.loadSpaces = function() {
            return CloudSpace.list().then(function(cloudspaces){
                $scope.cloudspaces = cloudspaces;
                return cloudspaces;
            });
        };

        $scope.loadSpaces();

        $scope.$watch('cloudspaces', function(){
            if (!$scope.cloudspaces)
                return;

            var currentCloudSpaceFromList;
            if ($scope.currentSpace){
                currentCloudSpaceFromList = _.find($scope.cloudspaces, function(cloudspace){ return cloudspace.id == $scope.currentSpace.id; });
            }
            if (currentCloudSpaceFromList == null){
                currentCloudSpaceFromList = _.first($scope.cloudspaces);
            }
            $scope.setCurrentCloudspace(currentCloudSpaceFromList);

        }, true);

	    $scope.$watch('currentAccount',  function(){
              if($scope.currentAccount){
                    $scope.userRightsOnAccountBilling = $scope.currentAccount.userRightsOnAccountBilling;
	          }
            }, true);

        $scope.logout = function() {
            User.logout();

			var uri = new URI($window.location);
			uri.filename('');
			uri.fragment('');
			$window.location = uri.toString();
        };

    }]);