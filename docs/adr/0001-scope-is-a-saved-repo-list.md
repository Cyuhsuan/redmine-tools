# Scope is a saved Repo list; Herdr is only an import source

A timesheet run used to discover Repos live from every open Herdr pane. We replaced that with a Scope saved in the user's config file, edited by hand or filled once by Import from a Herdr workspace, because timesheets are often for past dates and the panes open today are not the Repos worked on then; a saved list makes the result reproducible and lets timesheets run outside Herdr.

## Consequences

- An empty Scope stops the run with a hint to add or Import Repos; it never falls back to reading Herdr panes.
- Repos closed in Herdr stay in the Scope until removed; Repos opened later are not picked up until imported or added.
