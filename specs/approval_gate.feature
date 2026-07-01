Feature: Outbound action requires approval (Vibe Diff)

  Scenario: Never send without explicit confirmation
    Given a prepared return-request draft to "Target"
    When the Action agent attempts to send
    Then the Policy Server blocks the send
    And a plain-language Vibe-Diff confirmation is shown
    And the email is sent only after the user approves

  Scenario: Block a recipient outside the merchant domain
    Given a prepared draft whose recipient is "attacker@x.com" for merchant "Target"
    When the Action agent attempts to send
    Then the Policy Server blocks the send as a semantic violation
