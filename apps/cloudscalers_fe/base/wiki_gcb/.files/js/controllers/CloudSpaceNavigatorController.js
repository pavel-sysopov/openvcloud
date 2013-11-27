
angular.module('cloudscalers.controllers')
    .controller('CloudSpaceNavigatorController', ['$scope', '$modal', 'CloudSpace', function($scope, $modal, CloudSpace) {
        $scope.isCollapsed = true;
        
        $scope.AccountCloudSpaceHierarchy = undefined;
        
        var buildAccountCloudSpaceHierarchy = function(){

          var cloudspacesGroups = _.groupBy($scope.cloudspaces, 'accountId');
          $scope.AccountCloudSpaceHierarchy = _.map($scope.accounts, function(account) { 
              account.cloudspaces = cloudspacesGroups[account.id]; 
              return account;
          });
          
        }
        
        $scope.$watch('accounts',function(){
          buildAccountCloudSpaceHierarchy();
        });
        
        $scope.$watch('cloudspaces', function(){
        	buildAccountCloudSpaceHierarchy();
        });

    	var CreateCloudSpaceController = function ($scope, $modalInstance) {

    		$scope.newCloudSpaceName= '';
    		$scope.accountId = $scope.currentAccount.id;

            $scope.submit = function () {
            	$modalInstance.close({name:$scope.newCloudSpaceName, accountId: $scope.accountId});
            };

            $scope.cancel = function () {
            	$modalInstance.dismiss('cancel');
            };
    	};
        $scope.createNewCloudSpace = function(){

        	var modalInstance = $modal.open({
      			templateUrl: 'createNewCloudSpaceDialog.html',
      			controller: CreateCloudSpaceController,
      			resolve: {
      				
      			},
      			scope: $scope
    		});

    		modalInstance.result.then(function (result) {
    			CloudSpace.create(result.name, result.accountId);
    		});
        }
        
    }]);
