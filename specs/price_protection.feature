Feature: Price-protection claim

  Scenario: Detect a qualifying price drop
    Given a returnable monitor purchased 11 days ago for 299.00
    And the merchant offers a 30-day price-protection window
    When the price feed reports the same monitor at 259.00
    Then an action event "price-drop" is raised with delta 40.00
    And a price-adjustment draft is prepared for human approval
