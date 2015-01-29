angular.module('cloudscalers.controllers')
    .controller('SessionController', ['$scope', 'User', '$window', '$timeout','$location', 'SessionData', function($scope, User, $window, $timeout,$location, SessionData) {
        $scope.user = {username : '', password:'', company: '', vat: ''};
        
        $scope.login_error = undefined;

        $scope.login = function() {
            $scope.$broadcast("autofill:update");
        	var usertologin = $scope.user.username;
            User.login(usertologin, $scope.user.password).
            then(
            		function(result) {
            			$scope.login_error = undefined;
            			var target = 'Decks';
                    	if (result.status == 409){
                    		target = 'AccountValidation';
                    	}
            			User.updateUserDetails(usertologin).then(
                                function(result) {
                                	var uri = new URI($window.location);
                        			uri.filename(target);
                        			$window.location = uri.toString();
                                },
                                function(reason){
                                	$scope.login_error = reason.status
                                });
            		},
            		function(reason) {
            			$scope.login_error = reason.status;
            		}
            );
        };

        if($location.search().username && $location.search().apiKey){
            SessionData.setUser({ username: $location.search().username, api_key: $location.search().apiKey });
            var target = 'Decks';
            var uri = new URI($window.location);
            uri.filename(target);
            uri.query('');
            $window.location = uri.toString();
        }
        $timeout(function() {
            // Read the value set by browser autofill
            $scope.user.username = angular.element('[ng-model="user.username"]').val();
            $scope.user.password =angular.element('[ng-model="user.password"]').val();
        }, 0);
    }]).directive("autofill", function () {
    return {
        require: "ngModel",
        link: function (scope, element, attrs, ngModel) {
            scope.$on("autofill:update", function() {
                ngModel.$setViewValue(element.val());
            });
        }
    }
});