# Spec-Driven Development (course: BDD / Gherkin, Day 5).
# These scenarios are simultaneously the acceptance tests and the eval set.
# The deterministic ones are enforced by tests/unit/test_windows.py; the end-to-end
# agent behaviour is validated by `agents-cli eval` (tests/eval/).

Feature: Return-window watchdog

  Scenario: Surface a closing return window in time
    Given a ledger entry "blender" purchased 84 days ago at "Target"
    And Target's return policy is 90 days
    And the item is marked returnable and unused
    When the daily watchdog sweep runs
    Then an action event "return-window-closing" is raised
    And the user is notified "You can still return the blender for 6 more days"
    And a return-request draft is prepared but NOT sent

  Scenario: Do not nag on items past their window
    Given a ledger entry purchased 120 days ago at "Target" (90-day policy)
    When the daily watchdog sweep runs
    Then no return action event is raised
