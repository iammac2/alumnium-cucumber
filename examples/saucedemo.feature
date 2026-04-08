Feature: SauceDemo login

  Scenario: Standard user can log in and see inventory
    Given navigate to "https://www.saucedemo.com"
    When type "standard_user" into the username field
    And type "secret_sauce" into the password field
    And click the login button
    Then the page shows an inventory of products

  Scenario Outline: Multiple user types can log in and see inventory
    Given navigate to "https://www.saucedemo.com"
    When type "problem_user" into the username field
    And type "secret_sauce" into the password field
    And click the login button
    Then the page shows some products even if images are broken

  Scenario Outline: Multiple user types can log in and see inventory
    Given navigate to "https://www.saucedemo.com"
    When type "<username>" into the username field
    And type "secret_sauce" into the password field
    And click the login button
    And the page finishes loading
    Then the page shows an inventory of products

    Examples: valid users
      | username                |
      | standard_user           |
      | performance_glitch_user |
