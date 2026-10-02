# Timesheet tools

A toolkit that turns the user's own git commits into reviewed time entries on a work-tracking platform. Redmine is one platform among possibly several.

## Language

### Scope and sources

**Repo**:
A local git repository (identified by its root path) whose commits count as the user's work.
_Avoid_: 專案, project, workspace (for a local repo)

**Scope** (檢查範圍):
The user's saved list of Repos that a timesheet run collects commits from.
_Avoid_: 範圍, project list, watch list

**Import** (匯入):
Adding the Repos currently open in a Herdr workspace to the Scope, once; later Herdr changes do not alter the Scope.
_Avoid_: sync, 抓取 (as a live source)

### Platform

**Platform** (平台):
The work-tracking system that receives time entries, e.g. Redmine.
_Avoid_: backend, provider, tracker

**Project** (專案):
A container of work items on the Platform side. Never a local Repo.
_Avoid_: repo

**Time entry** (工時紀錄):
One record of hours logged on the Platform against a work item on a date.
_Avoid_: log, worklog row

**Activity** (活動):
The Platform's category for a Time entry (development, code review, discussion), chosen per row.
_Avoid_: type, category

### Timesheet

**Daily target** (每日目標):
The hours each day with commits should total after Top-up; 8 by default.
_Avoid_: quota, 8h rule

**Session**:
A run of one Repo branch's commits on the same day with no gap over the session gap.
_Avoid_: work block, span

**Timesheet** (工時表):
The review table of proposed Time entries for a date range, shown before anything is submitted.
_Avoid_: draft, report

**Top-up** (補分配):
Hours added to a day's rows so the day reaches the target, split by changed lines rather than measured time.
_Avoid_: padding, fill

**Unmapped** (未對應):
A row whose commits match no single work item; it is never submitted and gets no Top-up.
_Avoid_: orphan, unknown
