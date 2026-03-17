---
name: spec-writing
description: "Guidance for writing a project specification — requirements and scope definition phase."
---

# Writing a Project Specification

## Purpose

A spec defines **what needs to be done and why** — not how to do it. It is the requirements and scope agreement between stakeholders before any implementation planning begins.

Technical references are allowed only to the extent they help scope the work (e.g., "this requires integration with the AWS S3 API" sets a boundary; "we'll use a presigned URL pattern" does not belong here).

## What a Spec Should Contain

- **Goals** — what business or product outcome this project achieves
- **Requirements** — what the system must do (functional) and must not do (constraints)
- **Scope** — explicit list of what is in scope and what is out of scope
- **Success criteria** — how we know the project is done
- **Stakeholders / users** — who this affects
- **Technical boundaries** *(optional, scope only)* — external systems, APIs, or platforms this must interact with, named only to bound the work

## What a Spec Should NOT Contain

- Architecture decisions or design patterns
- Implementation approach or technology choices
- Data models, schemas, or API contracts
- Code-level detail of any kind

## Gathering Requirements

Ask questions **one at a time**. Start with the broadest open-ended question, then drill into specifics:

1. **Goal** — What outcome does this project deliver?
2. **Users / stakeholders** — Who is affected and how?
3. **Requirements** — What must the system do? Any hard constraints?
4. **Scope boundaries** — What is explicitly out of scope?
5. **Success criteria** — How do we know when this is done?
6. **Technical boundaries** *(if relevant)* — Are there specific external systems or platforms this must work with?

Only ask about technical boundaries if they are necessary to define scope — e.g., "Does this need to integrate with an existing system?" not "What technology should we use?"

## Key Principles

- **One question at a time** — don't overwhelm the user
- **YAGNI ruthlessly** — challenge scope creep, keep it focused
- **No solution bias** — avoid suggesting how things will be built
- **Explicit over implicit** — if something is out of scope, state it clearly
- **Short is better** — a tight, clear spec is more useful than a long vague one
