describe("SessionController tests", function(){
    var $scope, ctrl, $controller, User, $q, $window = {};
    
    beforeEach(module('cloudscalers'));
    
    beforeEach(inject(function($rootScope, _$controller_, _$q_) {
        $scope = $rootScope.$new();
        User = {login : jasmine.createSpy('login')};
        $controller = _$controller_;
        $q = _$q_;
    }));

    it("handles failure", function() {
    	var defer = $q.defer();
        User.login.andReturn(defer.promise);
        ctrl = $controller('SessionController', {$scope : $scope, User : User, $window : $window});

        $scope.username = 'error';
        $scope.password = 'pa$$w0rd';
        $scope.login();

        defer.reject(403);
        $scope.$digest();
        
        expect(User.login).toHaveBeenCalledWith('error', 'pa$$w0rd');
        expect($scope.login_error).toBe(403);
    });

    it('handles success', function() {
    	var defer = $q.defer();
        User.login.andReturn(defer.promise);
        ctrl = $controller('SessionController', {$scope : $scope, User : User, $window: $window});

        $scope.username = 'user1';
        $scope.password = 'pa$$w0rd';
        $scope.login();

        defer.resolve('myapikey');
        $scope.$digest();
        
        expect(User.login).toHaveBeenCalledWith('user1', 'pa$$w0rd');
        expect($scope.login_error).toBeUndefined();
    });
});

