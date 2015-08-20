package users

import (
	"errors"
	"log"
	"net/http"

	"github.com/RangelReale/osin"
	"github.com/gin-gonic/gin"
)

//UserDetails is the profile information
type UserDetails struct {
	Login  string
	Name   string
	Email  []string
	Scopes []string
}

var (
	UserNotFoundError        = errors.New("User not found")
	InvalidPasswordError     = errors.New("Invalid password")
	InvalidSecurityCodeError = errors.New("Invalid security code")
)

//UserStore defines the interface for user information
type UserStore interface {
	//Get user details
	Get(username string) (*UserDetails, error)

	//Validate checks if a given password is correct for a username and returns the available scopes
	//
	// If the user credientials could not be validated, it returns one of the
	// following errors: UserNotFoundError, InvalidPasswordError,
	// InvalidSecurityCodeError or a custom error
	Validate(username, password, securityCode string) (scopes []string, err error)

	//Close frees resources like connectionpools for example
	Close()
}

func RequiresUser(c *gin.Context, osinServer *osin.Server, u UserStore) *UserDetails {
	var code string
	if token := osin.CheckBearerAuth(c.Request); token != nil {
		code = token.Code
	} else {
		code = c.Request.FormValue("access_token")
	}

	if code == "" {
		log.Println("No access token in request")
		c.JSON(http.StatusUnauthorized, gin.H{})
		return nil
	}

	accesstoken, err := osinServer.Storage.LoadAccess(code)
	if err != nil {
		log.Println("Invalid access token")
		c.JSON(http.StatusUnauthorized, gin.H{})
		return nil
	}

	user, err := u.Get(accesstoken.UserData.(string))
	if err != nil {
		log.Println("Unable to get user details:", err)
		c.JSON(http.StatusInternalServerError, gin.H{})
		return nil
	}

	return user
}
